"""Server-side authorization, CSRF and explicit demo/private workspace selection."""
import secrets

import anyio
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from .demo_sessions import COOKIE_NAME
from .identity import AUTH_COOKIE, MODE_COOKIE

PUBLIC_AUTH = {"/api/auth/login", "/api/auth/register", "/api/auth/recover", "/api/auth/reset-password"}
CONTROL = {"/api/health", "/api/config", "/api/demo/start", "/api/welcome", *PUBLIC_AUTH}


async def protect_hosted(request, call_next):
    settings = request.app.state.hosted_settings
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    try:
        origin = request.headers.get("origin")
        callback = path == "/api/gmail/callback"
        write = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        if not callback and ((origin and origin != settings.origin) or request.headers.get("sec-fetch-site") == "cross-site" or (write and not origin)):
            raise HTTPException(403, "Use the same-origin Moniq application.")
        service = request.app.state.identity_store
        token = request.cookies.get(AUTH_COOKIE)
        identity = await anyio.to_thread.run_sync(service.authenticate, token) if service else None
        if identity:
            request.state.identity = identity
            request.state.auth_token = token
            if path not in {"/api/health", "/api/config"}:
                await anyio.to_thread.run_sync(service.rate_limit, "private-api", identity.user_id, 240, 60)
            if path == "/api/gmail/sync":
                await anyio.to_thread.run_sync(service.rate_limit, "gmail-sync", identity.user_id, 6, 60)
        mode = request.cookies.get(MODE_COOKIE)
        request.state.workspace = "personal" if identity and mode != "demo" else "demo" if mode == "demo" else "welcome"
        if identity and write and path not in PUBLIC_AUTH:
            if not secrets.compare_digest(request.headers.get("x-moniq-csrf", ""), service.csrf(token)):
                raise HTTPException(403, "Refresh Moniq and retry with the current session's security token.")
        if request.method in {"POST", "PUT", "PATCH"} or (write and request.headers.get("content-length") is not None):
            length = request.headers.get("content-length")
            maximum = 3_000_000 if request.state.workspace == "personal" else 8192
            if length is None:
                raise HTTPException(411, "A bounded request body is required.")
            if not length.isdigit() or int(length) > maximum:
                raise HTTPException(413, "Request is too large for this workspace.")
        if path in CONTROL or path == "/api/auth/logout":
            return await call_next(request)
        if path == "/api/workspace":
            if not identity:
                raise HTTPException(401, "Log in to choose a private workspace.")
            return await call_next(request)
        if request.state.workspace == "personal":
            if path.startswith("/api/upgrade-demo/") or path in {"/api/demo/reset", "/api/demo/import-statement"}:
                raise HTTPException(403, "Synthetic reset and sample imports cannot modify a private workspace.")
            request.state.private_engine = await anyio.to_thread.run_sync(service.workspace, identity.user_id)
            return await call_next(request)
        if path.startswith("/api/gmail/"):
            raise HTTPException(403, "Real Gmail is available only in an authenticated private workspace.")
        if path.startswith("/api/auth/") or request.state.workspace != "demo":
            raise HTTPException(401, "Log in or explicitly start your isolated synthetic demo.")
        if token and not identity:
            # An expired private login never silently becomes a financial workspace.
            raise HTTPException(401, "Session expired. Log in again or start a new demo.")
        if path.startswith("/api/imports/"):
            raise HTTPException(403, "Personal uploads are disabled in synthetic demo sessions.")
        with request.app.state.demo_store.lease(request.cookies.get(COOKIE_NAME)) as session:
            await anyio.to_thread.run_sync(session.lock.acquire)
            try:
                request.state.demo_engine = session.engine
                return await call_next(request)
            finally:
                session.lock.release()
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
