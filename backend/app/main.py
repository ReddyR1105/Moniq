import csv
import io
import json
from contextlib import asynccontextmanager

import anyio
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StaticHTTPException

from .circles import guard_transaction, router as circles_router
from .assistant import answer_question
from .config import COOKIE_SECURE, CORS_ORIGINS, MAX_DEMO_SESSIONS, PUBLIC_DEMO, PUBLIC_MODEL_DIR, PUBLIC_ORIGIN, ROOT, RUNTIME, SERVE_FRONTEND, SESSION_TTL_SECONDS
from .database import engine, get_db
from .demo_policy import SCHEDULE_MERCHANTS, check_profile, check_question, check_transaction, descriptions, require_sample, sample_messages
from .demo_sessions import COOKIE_NAME, DemoSessionStore
from .finance import budgets, dashboard, deal_recommendations, detect_subscriptions, forecast, insights, money
from .gmail_routes import require_local, router as gmail_router, validate_personal_transaction
from .integrations import integration_status
from .ml import Classifier
from .models import Account, AccountDetails, Base, Budget, Correction, Deal, GmailItem, Goal, Notification, Profile, RecurringPayment, Transaction
from .notifications import parse_message
from .schemas import BudgetIn, Category, ClassifyIn, GoalIn, MessageIn, ProfileIn, ScenarioIn, ScheduleIn, SubscriptionIn, TransactionIn, cents
from .seed import seed_demo
from .transactions import MAX_CSV_BYTES, add_transaction, csv_payloads, prepare_transaction, read_csv, serialize_transaction
from .workspace import workspace_classifier
from .smartapprove import router as smart_router
from .upgrade_scenario import approvals_router, router as upgrade_router
from .account_tools import router as account_router
from .goals import goal_rows, router as goal_router

classifier = None


@asynccontextmanager
async def lifespan(app):
    global classifier
    app.state.public_demo = PUBLIC_DEMO
    app.state.gmail = None
    app.state.personal_engine = None
    app.state.scenario_engine = None
    app.state.personal_classifier = None
    if PUBLIC_DEMO:
        classifier = Classifier(model_dir=PUBLIC_MODEL_DIR)
        classifier.train()  # Public inference uses a separate immutable synthetic baseline.
        app.state.demo_store = DemoSessionStore(RUNTIME / "public-sessions", SESSION_TTL_SECONDS, MAX_DEMO_SESSIONS)
    else:
        Base.metadata.create_all(engine)
        classifier = Classifier()
        with Session(engine) as db:
            # A deliberately deleted demo is never silently recreated on restart.
            if not db.scalar(select(Account.id)):
                seed_demo(db)
    try:
        app.state.classifier = classifier
        yield
    finally:
        if PUBLIC_DEMO:
            app.state.demo_store.close()
        else:
            if app.state.personal_engine is not None:
                app.state.personal_engine.dispose()
            if app.state.scenario_engine is not None:
                app.state.scenario_engine.dispose()


app = FastAPI(title="Moniq", version="0.2.0", lifespan=lifespan, description="Student finance MVP with local persistence and isolated public synthetic sessions.",
              docs_url=None if PUBLIC_DEMO else "/docs", redoc_url=None if PUBLIC_DEMO else "/redoc", openapi_url=None if PUBLIC_DEMO else "/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"], allow_credentials=False)
Db = Depends(get_db)


@app.middleware("http")
async def private_response_headers(request: Request, call_next):
    if PUBLIC_DEMO and (request.url.path.startswith("/api/gmail/") or request.url.path == "/api/workspace"):
        return JSONResponse({"detail": "Gmail and personal workspaces are unavailable in public demo sessions."}, status_code=403)
    if not PUBLIC_DEMO and request.cookies.get("moniq_workspace") in {"personal", "scenario"}:
        try:
            require_local(request)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    origin = request.headers.get("origin")
    expected_origin = PUBLIC_ORIGIN or str(request.base_url).rstrip("/")
    if PUBLIC_DEMO and request.url.path.startswith("/api/") and (request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != expected_origin)):
        return JSONResponse({"detail": "Use the same-origin Moniq demo."}, status_code=403)
    if not PUBLIC_DEMO and request.method in {"POST", "PUT", "DELETE"} and origin and origin not in CORS_ORIGINS:
        return Response(content='{"detail":"Origin is not permitted for this local demo."}', status_code=403, media_type="application/json")
    if PUBLIC_DEMO and request.url.path.startswith("/api/imports/"):
        return JSONResponse({"detail": "Personal statement uploads are disabled. Import the built-in synthetic statement instead."}, status_code=403)
    if PUBLIC_DEMO and request.method in {"POST", "PUT"}:
        length = request.headers.get("content-length")
        if length is None:
            return JSONResponse({"detail": "A bounded request body is required."}, status_code=411)
        if not length.isdigit() or int(length) > 8192:
            return JSONResponse({"detail": "Demo requests must be smaller than 8 KB."}, status_code=413)
    try:
        if PUBLIC_DEMO and request.url.path == "/api/config":
            token = await anyio.to_thread.run_sync(app.state.demo_store.bootstrap, request.cookies.get(COOKIE_NAME))
            response = await call_next(request)
            response.set_cookie(COOKIE_NAME, token, httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=SESSION_TTL_SECONDS)
        elif PUBLIC_DEMO and request.url.path.startswith("/api/") and request.url.path != "/api/health":
            with app.state.demo_store.lease(request.cookies.get(COOKIE_NAME)) as session:
                await anyio.to_thread.run_sync(session.lock.acquire)
                try:
                    request.state.demo_engine = session.engine
                    response = await call_next(request)
                finally:
                    session.lock.release()
        else:
            response = await call_next(request)
    except HTTPException as exc:
        response = JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/api/health")
def health():
    if not PUBLIC_DEMO:
        with Session(engine) as db:
            db.execute(select(Account.id).limit(1))
    return {"status": "ok", "prototype": True, "mode": "isolated synthetic sessions" if PUBLIC_DEMO else "synthetic single-user demo", "model_loaded": classifier is not None, "integrations": integration_status()}


@app.get("/api/config")
def runtime_config(request: Request):
    return {"public_demo": PUBLIC_DEMO, "session_ttl_minutes": SESSION_TTL_SECONDS // 60,
            "upload_enabled": not PUBLIC_DEMO, "retrain_enabled": not PUBLIC_DEMO,
            "workspace": request.cookies.get("moniq_workspace", "demo") if not PUBLIC_DEMO and request.cookies.get("moniq_workspace") in {"personal", "scenario"} else "demo"}


@app.get("/api/dashboard")
def get_dashboard(db: Session = Db):
    return dashboard(db)


@app.get("/api/transactions")
def get_transactions(q: str = Query(default="", max_length=200), category: Category | None = None,
                     kind: str | None = Query(default=None, pattern="^(expense|income|refund|reimbursement|settlement)$"),
                     start: str | None = None, end: str | None = None,
                     offset: int = Query(default=0, ge=0), limit: int = Query(default=500, ge=1, le=1000), db: Session = Db):
    query = select(Transaction)
    if q:
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Transaction.description.ilike(f"%{escaped}%", escape="\\") | Transaction.merchant.ilike(f"%{escaped}%", escape="\\"))
    if category:
        query = query.where(Transaction.category == category.value)
    if kind:
        query = query.where(Transaction.kind == kind)
    from datetime import date
    try:
        if start:
            query = query.where(Transaction.date >= date.fromisoformat(start))
        if end:
            query = query.where(Transaction.date <= date.fromisoformat(end))
        if start and end and start > end:
            raise ValueError()
    except ValueError as exc:
        raise HTTPException(422, "Use valid ISO dates, with the start before the end.") from exc
    return [serialize_transaction(t) for t in db.scalars(query.order_by(Transaction.date.desc(), Transaction.id.desc()).offset(offset).limit(limit))]


@app.post("/api/transactions", status_code=201)
def create_transaction(payload: TransactionIn, request: Request, db: Session = Db):
    validate_personal_transaction(request, payload, db)
    if PUBLIC_DEMO:
        check_transaction(payload)
    try:
        row = add_transaction(db, payload, workspace_classifier(request), "notification" if payload.notification_text else "manual")
        if row is None:
            raise HTTPException(409, "Duplicate transaction: same date, merchant, and signed amount.")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Duplicate transaction.") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
    return serialize_transaction(row)


@app.put("/api/transactions/{transaction_id}")
def update_transaction(transaction_id: int, payload: TransactionIn, request: Request, db: Session = Db):
    validate_personal_transaction(request, payload, db)
    if PUBLIC_DEMO:
        check_transaction(payload)
    row = db.get(Transaction, transaction_id)
    if not row:
        raise HTTPException(404, "Transaction not found.")
    if not db.get(Account, payload.account_id):
        raise HTTPException(422, "Choose an existing account.")
    guard_transaction(db, transaction_id)
    from .models import ApprovalAudit
    if row.source == "smartapprove-adjustment" or db.scalar(select(ApprovalAudit.id).where(ApprovalAudit.transaction_id == row.id, ApprovalAudit.action == "reversed")):
        raise HTTPException(409, "Reversed approvals and their adjustments remain immutable audit records.")
    before = {"amount_cents": row.amount_cents, "kind": row.kind, "category": row.category, "account_id": row.account_id, "date": row.date.isoformat()}
    from .smartapprove import record_correction
    values = prepare_transaction(payload, workspace_classifier(request), row.source)
    duplicate = db.scalar(select(Transaction.id).where(Transaction.fingerprint == values["fingerprint"], Transaction.id != transaction_id))
    if duplicate:
        raise HTTPException(409, "This edit would create a duplicate transaction.")
    if row.category != values["category"]:
        db.add(Correction(description=payload.description, previous_category=row.category, corrected_category=values["category"]))
    for key, value in values.items():
        setattr(row, key, value)
    record_correction(db, row, before)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Duplicate transaction.") from exc
    return serialize_transaction(row)


@app.delete("/api/transactions/{transaction_id}", status_code=204)
def remove_transaction(transaction_id: int, db: Session = Db):
    row = db.get(Transaction, transaction_id)
    if not row:
        raise HTTPException(404, "Transaction not found.")
    guard_transaction(db, transaction_id)
    from .smartapprove import auto_record
    if auto_record(db, transaction_id) or row.source == "smartapprove-adjustment":
        raise HTTPException(409, "Use the auditable SmartApprove reversal instead of deleting approval history.")
    db.execute(delete(Notification).where(Notification.transaction_id == transaction_id))
    for email in db.scalars(select(GmailItem).where(GmailItem.transaction_id == transaction_id)):
        email.transaction_id = None  # Preserve reviewed message IDs so a deleted import is not resynced.
    db.delete(row)
    db.commit()
    return Response(status_code=204)


async def uploaded_csv(file):
    content = await file.read(MAX_CSV_BYTES + 1)
    await file.close()
    try:
        return read_csv(content, file.filename or "")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/imports/preview")
async def preview_csv(file: UploadFile = File(...)):
    frame = await uploaded_csv(file)
    return {"columns": frame.columns.tolist(), "sample": frame.head(5).to_dict(orient="records"), "rows": len(frame)}


@app.post("/api/imports/csv")
async def import_csv(request: Request, file: UploadFile = File(...), mapping: str = Form(...), convention: str = Form("negative_expense"),
                     day_first: bool = Form(False), account_id: int = Form(1), db: Session = Db):
    frame = await uploaded_csv(file)
    try:
        parsed = json.loads(mapping)
        payloads = csv_payloads(frame, parsed, convention, day_first)
        for payload in payloads:
            payload.account_id = account_id
            validate_personal_transaction(request, payload, db)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    imported = duplicates = 0
    try:
        for payload in payloads:
            row = add_transaction(db, payload, workspace_classifier(request), "csv")
            if row:
                imported += 1
            else:
                duplicates += 1
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Concurrent import conflict; no rows saved. Try again.") from exc
    return {"imported": imported, "duplicates": duplicates, "total_rows": len(payloads),
            "note": "Duplicate heuristic: same date, normalized merchant and signed amount. Two identical same-day purchases may need distinct merchant labels."}


@app.post("/api/classify")
def classify(payload: ClassifyIn, request: Request):
    if PUBLIC_DEMO:
        require_sample(payload.description in descriptions())
    return workspace_classifier(request).classify(payload.description)


@app.get("/api/ml/metrics")
def model_metrics(request: Request, db: Session = Db):
    return {**workspace_classifier(request).report, "stored_corrections": len(list(db.scalars(select(Correction.id))))}


@app.post("/api/ml/retrain")
def retrain(request: Request, db: Session = Db):
    if PUBLIC_DEMO:
        raise HTTPException(403, "Public predictions use an immutable baseline. Corrections stay in your session; retraining is available in local mode.")
    return workspace_classifier(request).train(list(db.scalars(select(Correction))))


@app.post("/api/notifications/parse")
def parse_notification(payload: MessageIn, request: Request):
    if PUBLIC_DEMO:
        require_sample(payload.text in sample_messages())
    try:
        return parse_message(payload.text, workspace_classifier(request))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/api/notifications/examples")
def message_examples():
    return {"examples": sample_messages()}


@app.post("/api/demo/import-sample")
def import_demo_statement(request: Request, db: Session = Db):
    if request.cookies.get("moniq_workspace") == "personal":
        raise HTTPException(409, "Sample statements are available in the synthetic demo workspace only.")
    frame = read_csv((ROOT / "data/sample_statement.csv").read_bytes(), "sample_statement.csv")
    payloads = csv_payloads(frame, {"date": "Date", "description": "Description", "amount": "Amount", "kind": "Kind", "category": "Category"}, "negative_expense")
    imported = sum(add_transaction(db, payload, classifier, "csv") is not None for payload in payloads)
    db.commit()
    return {"imported": imported, "duplicates": len(payloads) - imported}


@app.get("/api/budgets")
def list_budgets(db: Session = Db):
    return budgets(db)


@app.put("/api/budgets")
def save_budget(payload: BudgetIn, db: Session = Db):
    if payload.category == Category.income:
        raise HTTPException(422, "Income is not a spending budget category.")
    row = db.scalar(select(Budget).where(Budget.category == payload.category.value, Budget.period == payload.period))
    if row:
        row.limit_cents = cents(payload.limit)
    else:
        db.add(Budget(category=payload.category.value, period=payload.period, limit_cents=cents(payload.limit)))
    db.commit()
    return budgets(db)


@app.get("/api/forecast")
def get_forecast(db: Session = Db):
    return forecast(db)


@app.post("/api/scenarios")
def analyze_scenario(payload: ScenarioIn, db: Session = Db):
    base = forecast(db)
    changed = forecast(db, {"purchase_cents": cents(payload.purchase), "savings_cents": cents(payload.savings),
                            "extra_income_cents": cents(payload.extra_income), "delay_days": payload.delay_days})
    return {"baseline": base, "scenario": changed, "difference": round(changed["projected_balance"] - base["projected_balance"], 2)}


@app.get("/api/insights")
def get_insights(db: Session = Db):
    return insights(db)


@app.get("/api/schedules")
def get_schedules(db: Session = Db):
    return [{"id": r.id, "merchant": r.merchant, "amount": money(r.amount_cents), "category": r.category,
             "kind": r.kind, "next_due": r.next_due.isoformat(), "interval_days": r.interval_days,
             "status": r.status} for r in db.scalars(select(RecurringPayment).order_by(RecurringPayment.next_due))]


def schedule_values(payload):
    if PUBLIC_DEMO:
        require_sample(payload.merchant in SCHEDULE_MERCHANTS or payload.merchant in descriptions())
    from .config import today
    if payload.next_due <= today():
        raise HTTPException(422, "Choose a future due date. Record past payments as transactions.")
    return {"merchant": payload.merchant, "amount_cents": cents(payload.amount), "category": payload.category.value,
            "kind": payload.kind, "next_due": payload.next_due, "interval_days": payload.interval_days, "status": "confirmed"}


@app.post("/api/schedules", status_code=201)
def create_schedule(payload: ScheduleIn, db: Session = Db):
    values = schedule_values(payload)
    if db.scalar(select(RecurringPayment.id).where(RecurringPayment.merchant == payload.merchant)):
        raise HTTPException(409, "A schedule for this merchant already exists. Edit it instead.")
    db.add(RecurringPayment(**values))
    db.commit()
    return get_schedules(db)


@app.put("/api/schedules/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleIn, db: Session = Db):
    row = db.get(RecurringPayment, schedule_id)
    if not row:
        raise HTTPException(404, "Schedule not found.")
    values = schedule_values(payload)
    if db.scalar(select(RecurringPayment.id).where(RecurringPayment.merchant == payload.merchant, RecurringPayment.id != schedule_id)):
        raise HTTPException(409, "A schedule for this merchant already exists.")
    for key, value in values.items():
        setattr(row, key, value)
    db.commit()
    return get_schedules(db)


@app.delete("/api/schedules/{schedule_id}", status_code=204)
def remove_schedule(schedule_id: int, db: Session = Db):
    row = db.get(RecurringPayment, schedule_id)
    if not row:
        raise HTTPException(404, "Schedule not found.")
    if row.category == "subscriptions":
        row.status = "incorrect"
    else:
        db.delete(row)
    db.commit()
    return Response(status_code=204)


@app.get("/api/deals")
def get_deals(db: Session = Db):
    return deal_recommendations(db)


@app.get("/api/subscriptions")
def get_subscriptions(db: Session = Db):
    return detect_subscriptions(db)


@app.put("/api/subscriptions/{recurring_id}")
def confirm_subscription(recurring_id: int, payload: SubscriptionIn, db: Session = Db):
    row = db.get(RecurringPayment, recurring_id)
    if not row:
        raise HTTPException(404, "Recurring payment not found.")
    row.status = payload.status
    db.commit()
    return detect_subscriptions(db)


class AssistantIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@app.post("/api/assistant")
def assistant_question(payload: AssistantIn, db: Session = Db):
    if PUBLIC_DEMO:
        check_question(payload.question)
    return answer_question(db, payload.question)


def serialize_profile(row):
    if not row:
        return None
    return {"name": row.name, "university": row.university, "academic_year": row.academic_year,
            "allowance": money(row.allowance_cents), "income_preference": row.income_preference,
            "interests": row.interests, "student_verified": row.student_verified, "notifications": row.notifications}


@app.get("/api/profile")
def get_profile(db: Session = Db):
    return serialize_profile(db.get(Profile, 1))


@app.put("/api/profile")
def save_profile(payload: ProfileIn, db: Session = Db):
    if PUBLIC_DEMO:
        check_profile(payload)
    row = db.get(Profile, 1)
    if not row:
        row = Profile(id=1)
        db.add(row)
    for key, value in payload.model_dump(exclude={"allowance"}).items():
        setattr(row, key, value)
    row.allowance_cents = cents(payload.allowance)
    allowance = db.scalar(select(RecurringPayment).where(RecurringPayment.merchant == "Family allowance", RecurringPayment.kind == "income"))
    if allowance:
        allowance.amount_cents = row.allowance_cents
    db.commit()
    return serialize_profile(row)


@app.get("/api/goals")
def get_goals(db: Session = Db):
    return goal_rows(db)


@app.put("/api/goals/{goal_id}")
def save_goal(goal_id: int, payload: GoalIn, db: Session = Db):
    if PUBLIC_DEMO:
        require_sample(payload.name in {"Emergency fund", "Laptop fund", "Tuition fund", "Travel fund"})
    row = db.get(Goal, goal_id)
    if not row:
        row = Goal(id=goal_id)
        db.add(row)
    row.name, row.target_cents, row.saved_cents = payload.name, cents(payload.target), cents(payload.saved)
    db.commit()
    return get_goals(db)


@app.get("/api/export")
def export_data(request: Request, format: str = Query(default="json", pattern="^(json|csv)$"), db: Session = Db):
    transactions = [serialize_transaction(t) for t in db.scalars(select(Transaction).order_by(Transaction.date))]
    if format == "csv":
        output = io.StringIO(newline="")
        fields = ["date", "description", "merchant", "amount", "kind", "category"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in transactions:
            for key in ("description", "merchant", "category", "kind"):
                if row[key].lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                    row[key] = "'" + row[key]
            writer.writerow(row)
        return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="moniq-transactions.csv"'})
    def rows(model):
        return [{column.name: (value.isoformat() if hasattr(value, "isoformat") else value)
                 for column in model.__table__.columns for value in [getattr(row, column.name)]}
                for row in db.scalars(select(model))]
    payload = {"profile": serialize_profile(db.get(Profile, 1)), "accounts": rows(Account), "transactions": transactions,
               "budgets": rows(Budget), "goals": rows(Goal), "recurring_payments": rows(RecurringPayment),
               "deals": rows(Deal), "notifications": rows(Notification), "corrections": rows(Correction),
               "synthetic": PUBLIC_DEMO or request.cookies.get("moniq_workspace") != "personal",
               "registered_account_details": rows(AccountDetails), "gmail_review_items": rows(GmailItem)}
    from .models import Circle, CircleMember, CircleExpense, CircleShare, CircleSettlement, LedgerAudit, TrustedSender, ApprovalAudit, GmailEvidence, DebitCard, AccountTransfer, GoalPlan, GoalContribution
    for model in (Circle, CircleMember, CircleExpense, CircleShare, CircleSettlement, LedgerAudit, TrustedSender, ApprovalAudit, GmailEvidence, DebitCard, AccountTransfer, GoalPlan, GoalContribution):
        payload[model.__tablename__] = rows(model)
    return Response(json.dumps(payload, indent=2), media_type="application/json", headers={"Content-Disposition": 'attachment; filename="moniq-data.json"'})


@app.delete("/api/data", status_code=204)
def delete_data(request: Request, db: Session = Db):
    if request.cookies.get("moniq_workspace") == "personal" and not PUBLIC_DEMO:
        from .gmail_routes import manager
        manager(request).disconnect()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(delete(table))
    # Retain an empty account as the persistent deletion marker.
    db.add(Account(id=1, name="Empty local account", opening_balance_cents=0))
    db.commit()
    if not PUBLIC_DEMO:
        workspace_classifier(request).train()  # Reset only this workspace's correction-trained model.
    return Response(status_code=204)


@app.post("/api/demo/reset")
def reset_demo(request: Request, db: Session = Db):
    if request.cookies.get("moniq_workspace") == "personal" and not PUBLIC_DEMO:
        raise HTTPException(409, "Switch to the synthetic workspace before Reset Demo. Personal records are preserved.")
    seed_demo(db, reset=True)
    if not PUBLIC_DEMO:
        classifier.train()
    return {"status": "reset", "message": "Synthetic student demo restored. Personal changes and corrections removed."}


app.include_router(gmail_router)
app.include_router(circles_router)
app.include_router(smart_router)
app.include_router(upgrade_router)
app.include_router(approvals_router)
app.include_router(account_router)
app.include_router(goal_router)


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StaticHTTPException as exc:
            if exc.status_code == 404 and scope["path"].strip("/").split("/")[0] != "api" and "." not in path:
                return await super().get_response("index.html", scope)
            raise


if SERVE_FRONTEND:
    app.mount("/", FrontendFiles(directory=ROOT / "frontend/dist", html=True), name="frontend")
