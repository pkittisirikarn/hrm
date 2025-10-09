# main.py
import sys, asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

# DB
from database.connection import create_all_tables, SessionLocal, engine

# Routers
from modules.data_management import routes as data_management_routes
from modules.payroll import routes as payroll_routes
from modules.time_tracking import routes as time_tracking_routes
from modules.meeting.routes import api as meeting_api, pages as meeting_pages

# Migrations/seed helpers
from modules.data_management.migrations import migrate_employees_contact_columns
from modules.meeting.migrations import migrate_meeting_rooms_columns

# Windows event loop policy (dev on Windows)
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

app = FastAPI(
    title="HRM System API",
    description="API for the Human Resource Management System",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static & templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

# Meeting (API + Pages)
app.include_router(meeting_api)
app.include_router(meeting_pages)

@app.on_event("startup")
def on_startup():
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

    # --- Lightweight migrate: working_schedules add/ensure columns ---
    try:
        with engine.begin() as conn:
            insp = inspect(engine)
            cols = {c["name"] for c in insp.get_columns("working_schedules")}

            def add_col(sql: str):
                conn.execute(text(sql))

            if "employee_id" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN employee_id INTEGER")
                print("✓ Added working_schedules.employee_id")

            if "is_working_day" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN is_working_day BOOLEAN DEFAULT 1")
            if "late_grace_min" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN late_grace_min INTEGER")
            if "early_leave_grace_min" not in cols and "early_grace_min" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN early_leave_grace_min INTEGER")
            if "absence_after_min" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN absence_after_min INTEGER")
            if "standard_daily_minutes" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN standard_daily_minutes INTEGER")
            if "break_minutes_override" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN break_minutes_override INTEGER")
            if "break_start_time" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN break_start_time TIME")
            if "break_end_time" not in cols:
                add_col("ALTER TABLE working_schedules ADD COLUMN break_end_time TIME")

            print("✓ Migrated working_schedules columns if missing.")
    except Exception as e:
        print(f"⚠️ Migrate warning (working_schedules): {e}")

    # --- Lightweight migrate: payroll_runs add scheme_id / created_at if missing ---
    try:
        with engine.begin() as conn:
            insp = inspect(engine)
            cols = {c["name"] for c in insp.get_columns("payroll_runs")}
            if "scheme_id" not in cols:
                conn.execute(text("ALTER TABLE payroll_runs ADD COLUMN scheme_id INTEGER"))
                conn.execute(text("UPDATE payroll_runs SET scheme_id = 1 WHERE scheme_id IS NULL"))
                print("Backfilled payroll_runs.scheme_id -> 1")
            if "created_at" not in cols:
                conn.execute(text("ALTER TABLE payroll_runs ADD COLUMN created_at DATETIME"))
        print("✓ Migrated payroll_runs columns if missing.")
    except Exception as e:
        print(f"⚠️ Migrate warning (payroll_runs): {e}")

    # Ensure default payroll scheme & formulas
    from modules.payroll.services import ensure_default_scheme_and_formulas
    with SessionLocal() as db:
        ensure_default_scheme_and_formulas(db)
        print("Ensured default payroll scheme & formulas.")

    # --- Seed defaults for working_schedules ---
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE working_schedules
                SET late_grace_min = COALESCE(late_grace_min, 5),
                    early_leave_grace_min = COALESCE(early_leave_grace_min, 0),
                    absence_after_min = COALESCE(absence_after_min, 240),
                    standard_daily_minutes = COALESCE(standard_daily_minutes, 480)
            """))
        print("✓ Seeded defaults for working_schedules.")
    except Exception as e:
        print(f"⚠️ Seed warning: {e}")

    # --- Lightweight migrate: attendance_daily add early_leave_minutes if missing ---
    try:
        with engine.begin() as conn:
            insp = inspect(engine)
            cols = {c["name"] for c in insp.get_columns("attendance_daily")}
            if "early_leave_minutes" not in cols:
                conn.execute(text("ALTER TABLE attendance_daily ADD COLUMN early_leave_minutes INTEGER"))
                conn.execute(text("UPDATE attendance_daily SET early_leave_minutes = 0 WHERE early_leave_minutes IS NULL"))
                print("✓ Migrated attendance_daily.early_leave_minutes")
    except Exception as e:
        print(f"⚠️ Migrate warning (attendance_daily): {e}")

# ---------- UI routes ----------
@app.get("/", include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "HRM Home"})

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard/index.html", {"request": request})

@app.get("/payroll", include_in_schema=False)
async def redirect_to_payroll_allowance_types():
    return RedirectResponse(url="/payroll/allowance-types", status_code=302)

# ---------- Routers ----------
# NOTE: อย่าใส่ prefix ซ้ำกับที่ประกาศใน router แล้ว
# Data management API: (module นี้ประกาศ path ภายในเอง → ใส่ prefix ที่นี่)
app.include_router(data_management_routes.api_router, prefix="/api/v1/data-management", tags=["Data Management API"])
# Payroll API:
app.include_router(payroll_routes.api_router,          prefix="/api/v1/payroll",         tags=["Payroll API"])
# Time-tracking API: api_router มี prefix แล้ว → ไม่ต้องใส่ prefix ที่นี่ซ้ำ
app.include_router(time_tracking_routes.api_router)

# UI routers (prefix ที่นี่ตามเมนู)
app.include_router(data_management_routes.ui_router, prefix="/data-management", include_in_schema=False)
app.include_router(payroll_routes.ui_router,         prefix="/payroll",         include_in_schema=False)
app.include_router(time_tracking_routes.ui_router,   prefix="/time-tracking",   include_in_schema=False)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
