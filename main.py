# main.py
import sys, asyncio, os
from types import SimpleNamespace

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from core.templates import templates  # อินสแตนซ์ Jinja2Templates กลาง
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse, HTMLResponse as StarletteHTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text

from database.base import Base
from database.connection import create_all_tables, SessionLocal, engine

# ---- RBAC helpers ----
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

def _need_perm_for(path: str, method: str):
    # Security
    if path.startswith("/security"):
        if path.startswith("/security/password"):
            return "security.password.change"
        return "security.manage"

    # Payroll
    if path.startswith("/payroll") or path.startswith("/api/v1/payroll"):
        # รายงานเงินเดือน (เฉพาะอ่าน)
        if "/payroll-entries" in path and method == "GET":
            return "payroll.report.view"
        return "payroll.edit" if method in WRITE_METHODS else "payroll.view"

    # Time Tracking (แยกคำขอเป็นสิทธิ์เฉพาะ)
    if path.startswith("/time-tracking") or path.startswith("/api/v1/time-tracking"):
        if "/leave-requests" in path:
            return "time.leave.request" if method == "GET" else "time.edit"
        if "/ot-requests" in path:
            return "time.ot.request" if method == "GET" else "time.edit"
        return "time.edit" if method in WRITE_METHODS else "time.view"

    # Meeting (แยกห้องประชุมต้อง manage)
    if path.startswith("/meeting") or path.startswith("/api/v1/meeting"):
        if "/rooms" in path:
            return "meeting.manage"
        # dashboard & bookings -> view ก็พอ
        return "meeting.manage" if method in WRITE_METHODS else "meeting.view"

    # Recruitment
    if path.startswith("/recruitment") or path.startswith("/api/v1/recruitment"):
        return "recruitment.manage" if method in WRITE_METHODS else "recruitment.view"

    # Data Management
    if path.startswith("/data-management") or path.startswith("/api/v1/data-management"):
        if "/employees" in path:
            # เข้าหน้า employees ได้ถ้ามี view/edit อย่างใดอย่างหนึ่ง
            return "employees.edit" if method in WRITE_METHODS else "employees.view"
        if "/departments" in path:
            return "departments.manage"
        if "/positions" in path:
            return "positions.manage"

    return None

# ----- Windows event loop policy -----
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# ----- App instance -----
app = FastAPI(title="HRM System API", version="1.0.0")

# ----- Small helpers -----
def _sess(request: Request):
    return request.session if "session" in request.scope else {}

def _get_uid(sess: dict | None):
    if not sess: return None
    return sess.get("emp_id") or sess.get("employee_id") or sess.get("user_id")

def _is_logged_in(request: Request) -> bool:
    return "session" in request.scope and bool(_get_uid(request.session))

# ----- Middlewares -----
class DevStubMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from modules.security.perms import compute_user_perms
        sess = _sess(request)
        if os.environ.get("HRM_DEV_ADMIN") == "1" and sess is not None:
            if not _get_uid(sess):
                sess["emp_id"] = 1
                sess["role"] = "ADMIN"
                sess["email"] = "admin@hrm.local"
                sess["name"] = "Dev Admin"
            if not hasattr(request.state, "current_user"):
                request.state.current_user = SimpleNamespace(id=1, role="ADMIN")
            if not sess.get("perms"):
                try:
                    with SessionLocal() as db:
                        sess["perms"] = sorted(list(
                            compute_user_perms(db, sess["emp_id"], sess.get("role") or "USER")
                        ))
                except Exception:
                    sess["perms"] = []
        return await call_next(request)

class AuthWallMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allow_paths=None, allow_prefixes=None):
        super().__init__(app)
        self.allow_paths = set(allow_paths or set())
        self.allow_prefixes = tuple(allow_prefixes or ())

    async def dispatch(self, request: Request, call_next):
        from modules.security.perms import has_perm_session, compute_user_perms

        path = request.url.path

        # public paths
        if path in self.allow_paths or any(path.startswith(p) for p in self.allow_prefixes):
            return await call_next(request)

        sess = _sess(request)
        uid = _get_uid(sess)
        if not uid:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return RedirectResponse("/auth/login", status_code=302)

        # เติม perms เข้าซีชันถ้ายังไม่มี (กันพลาด)
        if not sess.get("perms"):
            try:
                with SessionLocal() as db:
                    sess["perms"] = sorted(list(
                        compute_user_perms(db, uid, sess.get("role") or "USER")
                    ))
            except Exception:
                sess.setdefault("perms", [])

        # RBAC check
        required = _need_perm_for(path, request.method)
        if required and not has_perm_session(sess, required):
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Forbidden"}, status_code=403)
            return StarletteHTMLResponse("Forbidden", status_code=403)

        return await call_next(request)

# เปิดใช้ AuthWall (DevStub เปิดเมื่ออยากทดสอบ)
# app.add_middleware(DevStubMiddleware)
app.add_middleware(
    AuthWallMiddleware,
    allow_paths={"/", "/login"},
    allow_prefixes=("/auth/", "/static/", "/favicon", "/docs", "/openapi.json"),
)

# ----- Session & Middlewares -----
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret"),
    session_cookie="hrm_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 24 * 7,
)

# ----- Static & Templates -----
os.makedirs("static/uploads/rooms", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.state.templates = templates

# ให้เทมเพลตเรียก has_perm จาก session ได้ (แสดง/ซ่อนเมนู)
from modules.security.perms import has_perm as has_perm_for_template
templates.env.globals["has_perm"] = has_perm_for_template

# ----- Routers -----
from modules.data_management import routes as data_management_routes
from modules.payroll import routes as payroll_routes
from modules.time_tracking import routes as time_tracking_routes

from modules.meeting.routes import api as meeting_api, pages as meeting_pages
from modules.recruitment.routes import api as recruitment_api, pages as recruitment_pages

from modules.security.routes import api as security_api, pages as security_pages
from modules.security.backup_routes import api_backup, pages as backup_pages

from modules.security.password_routes import api_pw, pages as pw_pages, ensure_password_hash_column

from modules.security.auth_routes import router as auth_router
from modules.security.bootstrap import ensure_default_admin
from modules.security.permissions_service import (
    ensure_security_tables,
    seed_default_roles_permissions,
    seed_full_permissions,
)
from modules.security.perms import (
    ensure_permissions_schema,
    seed_admin_all,
)

# include routers
app.include_router(meeting_api)
app.include_router(meeting_pages)

app.include_router(recruitment_api)
app.include_router(recruitment_pages)

app.include_router(security_api)
app.include_router(security_pages)
app.include_router(backup_pages, include_in_schema=False)
app.include_router(api_backup)
app.include_router(pw_pages, include_in_schema=False)
app.include_router(api_pw)

app.include_router(
    data_management_routes.api_router,
    prefix="/api/v1/data-management",
    tags=["Data Management API"],
)
app.include_router(payroll_routes.api_router, prefix="/api/v1/payroll", tags=["Payroll API"])
app.include_router(time_tracking_routes.api_router)

app.include_router(data_management_routes.ui_router, prefix="/data-management", include_in_schema=False)
app.include_router(payroll_routes.ui_router, prefix="/payroll", include_in_schema=False)
app.include_router(time_tracking_routes.ui_router, prefix="/time-tracking", include_in_schema=False)

app.include_router(auth_router, include_in_schema=False)

# ----- Startup -----
from modules.data_management.migrations import migrate_employees_contact_columns
from modules.meeting.migrations import migrate_meeting_rooms_columns, run_startup_migrations

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    run_startup_migrations(engine)

    print("Creating all database tables...")
    create_all_tables()
    print("Database tables created successfully.")

    ensure_password_hash_column()
    ensure_security_tables(engine)
    ensure_permissions_schema(engine)
    with SessionLocal() as db:
        seed_default_roles_permissions(db)
        seed_full_permissions(db)
    seed_admin_all(engine)

    ensure_default_admin()

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

    try:
        with SessionLocal() as db:
            db.execute(text("UPDATE meeting_bookings SET status='APPROVED' WHERE status='BOOKED'"))
            db.commit()
    except Exception as e:
        print(f"⚠️ Normalize meeting bookings warning: {e}")

# ----- UI routes -----
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
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return RedirectResponse("/static/favicon.ico")

# ----- Entrypoint -----
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
