"""No open signup: invitations verify email; recovery revokes all sessions."""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr

from .identity import AUTH_COOKIE, MODE_COOKIE, SESSION_SECONDS, normalize_email

router = APIRouter(prefix="/api/auth")


def store(request):
    value = getattr(request.app.state, "identity_store", None)
    if not getattr(request.app.state, "hosted_app", False) or value is None:
        raise HTTPException(503, "Private test accounts are not enabled. You can try the synthetic demo.")
    return value


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=128)


class RegisterIn(LoginIn):
    invitation: SecretStr = Field(min_length=20, max_length=100)


class RecoverIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)


class ResetIn(BaseModel):
    token: SecretStr = Field(min_length=20, max_length=100)
    password: SecretStr = Field(min_length=15, max_length=128)


def attempt_limits(request, action, email):
    service = store(request)
    email = normalize_email(email)
    # Do not trust arbitrary X-Forwarded-For values as a rate-limit identity.
    address = request.client.host if request.client else "unknown"
    service.rate_limit(action + "-address", address, limit=30)
    service.rate_limit(action + "-email", email, limit=8)
    return service


@router.post("/register", status_code=201)
def register(payload: RegisterIn, request: Request):
    service = attempt_limits(request, "register", payload.email)
    return service.register(payload.email, payload.password.get_secret_value(), payload.invitation.get_secret_value())


@router.post("/login")
def login(payload: LoginIn, request: Request, response: Response):
    service = attempt_limits(request, "login", payload.email)
    token = service.login(payload.email, payload.password.get_secret_value())
    old = request.cookies.get(AUTH_COOKIE)
    if old:
        service.logout(old)
    response.set_cookie(AUTH_COOKIE, token, secure=True, httponly=True, samesite="lax", path="/", max_age=SESSION_SECONDS)
    response.set_cookie(MODE_COOKIE, "personal", secure=True, httponly=True, samesite="lax", path="/", max_age=SESSION_SECONDS)
    return {"authenticated": True, "csrf_token": service.csrf(token)}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    service = store(request)
    if request.cookies.get(AUTH_COOKIE):
        service.logout(request.cookies[AUTH_COOKIE])
    for cookie in (AUTH_COOKIE, MODE_COOKIE):
        response.delete_cookie(cookie, path="/", secure=True, httponly=True, samesite="lax")


@router.post("/recover", status_code=202)
def recover(payload: RecoverIn, request: Request, background: BackgroundTasks):
    service = attempt_limits(request, "recover", payload.email)
    def deliver():
        try:
            service.send_grant(payload.email, "reset")
        except HTTPException:
            pass  # Generic response for every address, including provider failures.
    background.add_task(deliver)
    return {"message": "If an eligible account exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetIn, request: Request):
    service = store(request)
    service.rate_limit("reset-address", request.client.host if request.client else "unknown", limit=10)
    service.reset_password(payload.token.get_secret_value(), payload.password.get_secret_value())
    return {"message": "Password changed. Log in again; previous sessions are signed out."}
