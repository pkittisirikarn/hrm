# main.py
import sys, asyncio, os
import uvicorn
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse

from database.base import Base
from database.connection import create_all_tables, SessionLocal, engine
from sqlalchemy import text

# --- app modules/routers ---
from modules.data_management import routes as data_management_routes
from modules.payroll import routes as payroll_routes
from modules.time_tracking import routes as time_tracking_routes
from modules.meeting.routes import api as meeting_api, pages as meeting_pages
from modules.recruitment.routes import api as recruitment_api, pages as recruitment_pages
from modules.security.routes import api as security_api, pages as security_pages
from modules.security.backup_routes import api_backup
from modules.security.password_routes import api_pw, pages as pw_pages
from modules.security.bootstrap import ensure_default_admin
from modules.security.auth_routes import router as auth_router

from modules.data_management.migrations import migrate_employees_contact_columns
from modules.meeting.migrations import migrate_meeting_rooms_columns, run_startup_migrations

# ---------- Windows loop ----------
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

app = FastAPI(title="HRM System API", version="1.0.0")

# 2) CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _is_logged_in(request: Request) -> bool:
    """อ่านสถานะล็อกอินแบบปลอดภัย (มี session ค่อยอ่านค่า)"""
    if "session" not in request.scope:
        return False
    return bool(request.session.get("emp_id"))

# 3) DEV stub (ไม่แตะ session ถ้ายังไม่มี)
class DevStubMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.environ.get("HRM_DEV_ADMIN") == "1":
            if not request.session.get("emp_id"):
                request.session["emp_id"] = 1
                request.session["role"] = "ADMIN"
                request.session["email"] = "admin@hrm.local"
                request.session["name"] = "Dev Admin"
            if not hasattr(request.state, "current_user"):
                request.state.current_user = SimpleNamespace(id=1, role="ADMIN")
        return await call_next(request)

# 4) Auth wall (กันเข้าหน้าอื่นถ้ายังไม่ล็อกอิน) — อนุญาตบาง path
class AuthWallMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allow_paths=None, allow_prefixes=None):
        super().__init__(app)
        self.allow_paths = set(allow_paths or set())
        self.allow_prefixes = tuple(allow_prefixes or ())

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.allow_paths or any(path.startswith(p) for p in self.allow_prefixes):
            return await call_next(request)

        if not request.session.get("emp_id"):
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return RedirectResponse("/auth/login", status_code=302)

        return await call_next(request)

# ใส่สองตัวนี้ “หลัง” SessionMiddleware
app.add_middleware(DevStubMiddleware)
app.add_middleware(
    AuthWallMiddleware,
    allow_paths={"/", "/login"},
    allow_prefixes=("/auth/", "/static/", "/favicon", "/docs", "/openapi.json"),
)

from starlette.middleware.sessions import SessionMiddleware
# ---------- Middlewares ----------
# 1) SessionMiddleware ต้องมาก่อนและจะเป็นตัวเติม request.scope["session"]
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret"),
    session_cookie="hrm_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=False,
)

# ---------- Static & Templates ----------
os.makedirs("static/uploads/rooms", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# ---------- Routers ----------
app.include_router(meeting_api)
app.include_router(meeting_pages)

app.include_router(recruitment_api)
app.include_router(recruitment_pages)

app.include_router(security_api)
app.include_router(security_pages)
app.include_router(api_backup)
app.include_router(pw_pages, include_in_schema=False)
app.include_router(api_pw)

app.include_router(data_management_routes.api_router, prefix="/api/v1/data-management", tags=["Data Management API"])
app.include_router(payroll_routes.api_router,          prefix="/api/v1/payroll",         tags=["Payroll API"])
app.include_router(time_tracking_routes.api_router)

app.include_router(data_management_routes.ui_router, prefix="/data-management", include_in_schema=False)
app.include_router(payroll_routes.ui_router,         prefix="/payroll",         include_in_schema=False)
app.include_router(time_tracking_routes.ui_router,   prefix="/time-tracking",   include_in_schema=False)

# Auth (รวมเป็น router เดียว)
app.include_router(auth_router, include_in_schema=False)

# ---------- Startup ----------
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    run_startup_migrations(engine)

    ensure_default_admin()
    print("Creating all database tables...")
    create_all_tables()
    print("Database tables created successfully.")

    try:
        migrate_employees_contact_columns(engine)
        print("✓ Migrated employees: added email/phone_number if missing.")
    except Exception as e:
        print(f"⚠️ Migrate warning (employees contact columns): {e}")

    try:
        migrate_meeting_rooms_columns(engine)
        print("✓ Migrated meeting_rooms: ensured notes (and is_active) columns.")
    except Exception as e:
        print(f"⚠️ Migrate warning (meeting_rooms): {e}")

# ---------- UI routes ----------
@app.get("/", include_in_schema=False)
async def root(request: Request):
    if _is_logged_in(request):
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/auth/login", status_code=302)

@app.get("/login", include_in_schema=False)
def _go_login():
    return RedirectResponse("/auth/login", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    # ใช้ไฟล์ templates/dashboard.html (มีอยู่แล้ว)
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # ถ้าไม่มีไฟล์ จะ 404 จาก /static/favicon.ico (ไม่ใช่ 500)
    return RedirectResponse("/static/favicon.ico")

# ---------- Entrypoint ----------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)

# (utility) — ทำความสะอาดสถานะ booking เก่า ๆ
def _normalize_meeting_booking_statuses():
    with SessionLocal() as db:
        db.execute(text("UPDATE meeting_bookings SET status='APPROVED' WHERE status='BOOKED'"))
        db.commit()

_normalize_meeting_booking_statuses()
