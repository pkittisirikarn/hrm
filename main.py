# main.py
import sys, asyncio, os
from types import SimpleNamespace

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text

from database.base import Base
from database.connection import create_all_tables, SessionLocal, engine

# ----- Windows event loop policy -----
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# ----- App instance -----
app = FastAPI(title="HRM System API", version="1.0.0")

# ----- Helpers -----
def _sess(request: Request):
    return request.session if "session" in request.scope else {}

def _is_logged_in(request: Request) -> bool:
    return "session" in request.scope and bool(request.session.get("emp_id"))

# ----- Middlewares -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DevStubMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        sess = _sess(request)
        if os.environ.get("HRM_DEV_ADMIN") == "1" and sess is not None:
            if not sess.get("emp_id"):
                sess["emp_id"] = 1
                sess["role"] = "ADMIN"
                sess["email"] = "admin@hrm.local"
                sess["name"] = "Dev Admin"
            if not hasattr(request.state, "current_user"):
                request.state.current_user = SimpleNamespace(id=1, role="ADMIN")
        return await call_next(request)

class AuthWallMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, allow_paths=None, allow_prefixes=None):
        super().__init__(app)
        self.allow_paths = set(allow_paths or set())
        self.allow_prefixes = tuple(allow_prefixes or ())

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if path in self.allow_paths or any(path.startswith(p) for p in self.allow_prefixes):
            return await call_next(request)

        sess = _sess(request)
        if not sess or not sess.get("emp_id"):
            if path.startswith("/api/"):
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return RedirectResponse("/auth/login", status_code=302)

        return await call_next(request)

app.add_middleware(DevStubMiddleware)
app.add_middleware(
    AuthWallMiddleware,
    allow_paths={"/", "/login"},
    allow_prefixes=("/auth/", "/static/", "/favicon", "/docs", "/openapi.json"),
)

# IMPORTANT: ใส่ SessionMiddleware “เป็นตัวสุดท้าย” ที่ add -> ทำให้มันเป็น outermost และมี session ก่อนตัวอื่น
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret"),
    session_cookie="hrm_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=False,
)

# ----- Static & Templates -----
os.makedirs("static/uploads/rooms", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# ----- Routers -----
from modules.data_management import routes as data_management_routes
from modules.payroll import routes as payroll_routes
from modules.time_tracking import routes as time_tracking_routes

from modules.meeting.routes import api as meeting_api, pages as meeting_pages
from modules.recruitment.routes import api as recruitment_api, pages as recruitment_pages

from modules.security.routes import api as security_api, pages as security_pages
from modules.security.backup_routes import api_backup, pages as backup_pages

# password routes (export เป็น api_pw เสมอจากไฟล์ที่เราแก้ให้)
from modules.security.password_routes import api_pw, pages as pw_pages, ensure_password_hash_column

from modules.security.auth_routes import router as auth_router
from modules.security.bootstrap import ensure_default_admin
from modules.security.permissions_service import (
    ensure_security_tables,
    seed_default_roles_permissions,
)
from modules.security.perms import (
    ensure_permissions_schema,
    seed_admin_all,
)
from modules.security.deps import has_perm

templates.env.globals["has_perm"] = has_perm

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
    # 1) สร้างตารางจาก SQLAlchemy models ทั้งหมด
    Base.metadata.create_all(bind=engine)

    # 2) migrations เฉพาะโมดูล meeting (ถ้ามี)
    run_startup_migrations(engine)

    print("Creating all database tables...")
    create_all_tables()
    print("Database tables created successfully.")

    # 3) เตรียม schema/ตาราง security “ก่อน” ใช้งาน
    #    - สร้าง column password_hash
    #    - สร้างตาราง roles/permissions
    ensure_password_hash_column()
    ensure_security_tables(engine)
    ensure_permissions_schema(engine)
    with SessionLocal() as db:
        seed_default_roles_permissions(db)
    seed_admin_all(engine)

    # 5) สร้าง admin เริ่มต้น (หลังคอลัมน์ password_hash มีแล้ว)
    ensure_default_admin()

    # 6) migrations อื่น ๆ
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

    # 7) normalize สถานะจองห้อง verg หลังมีตารางแน่ ๆ
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
    # ถ้าไม่มีไฟล์จะ 404 — แนะนำใส่ static/favicon.ico เพื่อให้ 200
    return RedirectResponse("/static/favicon.ico")

# ----- Entrypoint -----
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
