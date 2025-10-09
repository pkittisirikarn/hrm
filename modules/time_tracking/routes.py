# modules/time_tracking/routes.py
from fastapi import (
    APIRouter, Depends, HTTPException, status, Request,
    UploadFile, File, Query
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import date, datetime, time
import pandas as pd
import io

from database.connection import get_db
from modules.data_management.models import Employee
from modules.time_tracking.models import TimeEntry
from . import schemas, services

# --------------------------------------
# Routers
# --------------------------------------
ui_router  = APIRouter()                                 # เส้นทางหน้าจอ (HTML)
api_router = APIRouter(prefix="/api/v1/time-tracking",   # เส้นทาง API
                       tags=["Time Tracking API"])

# --------------------------------------
# Helpers (UI templating)
# --------------------------------------
def _tpl(request: Request, path: str, ctx: dict | None = None):
    """Render template using templates stored in app.state (set in main.py)."""
    templates = request.app.state.templates
    return templates.TemplateResponse(path, {"request": request, **(ctx or {})})

# =========================
# UI ROUTES
# =========================
@ui_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def ui_index(request: Request):
    return _tpl(request, "time_tracking/index.html")

@ui_router.get("/working-schedules", response_class=HTMLResponse, include_in_schema=False)
async def ui_working_schedules(request: Request):
    return _tpl(request, "time_tracking/working_schedules.html")

@ui_router.get("/time-entries", response_class=HTMLResponse, include_in_schema=False)
async def ui_time_entries(request: Request):
    return _tpl(request, "time_tracking/time_entries.html")

@ui_router.get("/leave-requests", response_class=HTMLResponse, include_in_schema=False)
async def ui_leave_requests(request: Request):
    return _tpl(request, "time_tracking/leave_requests.html")

@ui_router.get("/leave-types", response_class=HTMLResponse, include_in_schema=False)
async def ui_leave_types(request: Request):
    return _tpl(request, "time_tracking/leave_types.html")

@ui_router.get("/leave-balances", response_class=HTMLResponse, include_in_schema=False)
async def ui_leave_balances(request: Request):
    return _tpl(request, "time_tracking/leave_balances.html")

@ui_router.get("/holidays", response_class=HTMLResponse, include_in_schema=False)
async def ui_holidays(request: Request):
    return _tpl(request, "time_tracking/holidays.html")

@ui_router.get("/report", response_class=HTMLResponse, include_in_schema=False)
async def ui_report(request: Request):
    return _tpl(request, "time_tracking/report.html")

@ui_router.get("/ot-types", response_class=HTMLResponse, include_in_schema=False)
async def ui_ot_types(request: Request):
    return _tpl(request, "time_tracking/ot_types.html")

@ui_router.get("/ot-requests", response_class=HTMLResponse, include_in_schema=False)
async def ui_ot_requests(request: Request):
    return _tpl(request, "time_tracking/ot_requests.html", {"title": "จัดการคำขอ OT"})

@ui_router.get("/ot-requests/{ot_request_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def ui_ot_request_edit(ot_request_id: int, request: Request):
    return _tpl(
        request,
        "time_tracking/ot_request_edit.html",
        {"title": "แก้ไขคำขอ OT", "ot_request_id": ot_request_id},
    )

# =========================
# API ROUTES
# =========================

# -------- Logs / Time entries report (แบบ range/รายวัน) --------
@api_router.get("/logs/")
def list_logs(
    db: Session = Depends(get_db),
    employee_code: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = 200,
    offset: int = 0,
):
    q = (
        db.query(TimeEntry)
        .join(Employee, Employee.id == TimeEntry.employee_id)
        .order_by(TimeEntry.check_in_time.asc())
    )

    if employee_code:
        q = q.filter(Employee.employee_id_number.ilike(f"%{employee_code}%"))

    if date_from and date_to:
        start_dt = datetime.combine(date_from, time.min)
        end_dt   = datetime.combine(date_to,   time.max)
        q = q.filter(
            or_(
                TimeEntry.check_in_time.between(start_dt, end_dt),
                TimeEntry.check_out_time.between(start_dt, end_dt),
                (TimeEntry.check_in_time <= end_dt)
                & (func.coalesce(TimeEntry.check_out_time, TimeEntry.check_in_time) >= start_dt),
            )
        )
    elif date_from:
        q = q.filter(func.date(TimeEntry.check_in_time) >= date_from)
    elif date_to:
        q = q.filter(func.date(TimeEntry.check_in_time) <= date_to)

    items = q.offset(offset).limit(limit).all()
    return {"count": q.count(), "items": items}

# -------- Leave Balances --------
@api_router.get("/leave-balances/{employee_id}/{year}",
               response_model=List[schemas.LeaveBalanceInDB])
def api_get_leave_balances(employee_id: int, year: int, db: Session = Depends(get_db)):
    rows = services.get_leave_balances(db=db, employee_id=employee_id, year=year)
    return rows

@api_router.get("/leave-balances/")
def list_leave_balances_api(
    employee_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    y = year or datetime.utcnow().year
    return services.list_leave_balances(db=db, employee_id=employee_id, year=y)

@api_router.put("/leave-balances/{balance_id}")
def update_leave_balance_api(
    balance_id: int,
    opening_quota: Optional[float] = Query(None),  # legacy
    accrued: Optional[float] = Query(None),
    used: Optional[float] = Query(None),
    adjusted: Optional[float] = Query(None),
    carry_in: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    # map query params -> LeaveBalanceUpdate
    data = {}
    if opening_quota is not None:
        data["opening"] = opening_quota   # ← map legacy ชื่อเก่าไป field ใหม่
    if accrued is not None:
        data["accrued"] = accrued
    if used is not None:
        data["used"] = used
    if adjusted is not None:
        data["adjusted"] = adjusted
    if carry_in is not None:
        data["carry_in"] = carry_in

    patch = schemas.LeaveBalanceUpdate(**data)
    obj = services.update_leave_balance(db=db, balance_id=balance_id, patch=patch)
    if not obj:
        raise HTTPException(status_code=404, detail="Leave balance not found")
    return obj

@api_router.post("/leave-balances/seed")
def seed_leave_balances_api(
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    return services.seed_leave_balances(db=db, year=year)

@api_router.patch("/leave-balances/{balance_id}")
def patch_leave_balance_api(
    balance_id: int,
    patch: schemas.LeaveBalanceUpdate,   # body JSON: {opening, accrued, used, adjusted, carry_in}
    db: Session = Depends(get_db),
):
    obj = services.update_leave_balance(db=db, balance_id=balance_id, patch=patch)
    if not obj:
        raise HTTPException(status_code=404, detail="Leave balance not found")
    return obj

@api_router.post("/leave-balances/{employee_id}/{year}/{leave_type_id}/adjust",
                 response_model=schemas.LeaveBalanceInDB)
def api_adjust_leave_balance(
    employee_id: int, year: int, leave_type_id: int,
    payload: schemas.LeaveBalanceAdjust, db: Session = Depends(get_db)
):
    lb = services.adjust_leave_balance(
        db=db, employee_id=employee_id,
        leave_type_id=leave_type_id, year=year,
        delta=payload.adjusted_delta
    )
    return lb

# -------- Leave approve / reject --------
@api_router.post("/leave-requests/{request_id}/approve",
                 response_model=schemas.LeaveRequestInDB)
def api_approve_leave(request_id: int, db: Session = Depends(get_db)):
    return services.approve_leave_request(db=db, request_id=request_id)

@api_router.post("/leave-requests/{request_id}/reject",
                 response_model=schemas.LeaveRequestInDB)
def api_reject_leave(request_id: int, reason: Optional[str] = Query(None), db: Session = Depends(get_db)):
    return services.reject_leave_request(db=db, request_id=request_id, reason=reason)

@api_router.get("/leave-requests/balance")
def api_leave_balance(
    employee_id: int = Query(...),
    leave_type_id: int = Query(...),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    return services.get_leave_balance_year(
        db=db, employee_id=employee_id,
        leave_type_id=leave_type_id, year=year
    )
    
# ---------- Leave Requests (CRUD) ----------
@api_router.post("/leave-requests/", response_model=schemas.LeaveRequestInDB, status_code=status.HTTP_201_CREATED)
def create_leave_request_api(payload: schemas.LeaveRequestCreate, db: Session = Depends(get_db)):
    return services.create_leave_request(db=db, leave_request=payload)

@api_router.get("/leave-requests/", response_model=List[schemas.LeaveRequestInDB])
def list_leave_requests_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_leave_requests(db=db, skip=skip, limit=limit)

@api_router.get("/leave-requests/{request_id}", response_model=schemas.LeaveRequestInDB)
def get_leave_request_api(request_id: int, db: Session = Depends(get_db)):
    obj = services.get_leave_request(db=db, request_id=request_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return obj

@api_router.put("/leave-requests/{request_id}", response_model=schemas.LeaveRequestInDB)
def update_leave_request_api(request_id: int, payload: schemas.LeaveRequestUpdate, db: Session = Depends(get_db)):
    return services.update_leave_request(db=db, request_id=request_id, leave_request_update=payload)

@api_router.delete("/leave-requests/{request_id}", status_code=status.HTTP_200_OK)
def delete_leave_request_api(request_id: int, db: Session = Depends(get_db)):
    deleted = services.delete_leave_request(db=db, request_id=request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return {"message": "คำขอลาถูกลบแล้ว"}

# -------- Attendance: rebuild daily snapshot --------
@api_router.post("/attendance/rebuild")
def rebuild_attendance_api(
    start: date = Query(..., description="YYYY-MM-DD"),
    end: date = Query(..., description="YYYY-MM-DD"),
    employee_id: Optional[str] = Query(
        None,
        description="ใช้ employee.id (int) หรือรหัสพนักงาน employee_id_number (str)",
    ),
    db: Session = Depends(get_db),
):
    emp_db_id: Optional[int] = None
    if employee_id:
        try:
            emp_db_id = int(employee_id)
        except ValueError:
            emp = db.query(Employee).filter(Employee.employee_id_number == employee_id).first()
            if not emp:
                raise HTTPException(status_code=404, detail=f"ไม่พบพนักงานรหัส {employee_id}")
            emp_db_id = emp.id

    services.rebuild_attendance_range(db=db, start=start, end=end, employee_id=emp_db_id)
    return {"ok": True, "start": str(start), "end": str(end), "employee_id": emp_db_id}

# -------- Report data (ใช้ในหน้า /time-tracking/report) --------
@api_router.get("/report/data")
def get_time_entries_report_api(
    employee_id_number: Optional[str] = Query(None),
    entry_date: Optional[date] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    include_leaves: bool = Query(True),
    include_ot: bool = Query(True),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    if date_from or date_to:
        _from = date_from or date_to
        _to   = date_to or date_from
        # รายงานแบบรวม (Time + Leave + OT)
        return services.build_daily_report(
            db=db,
            date_from=_from,
            date_to=_to,
            employee_id_number=employee_id_number,
            include_leaves=include_leaves,
            include_ot=include_ot,
        )
    # กรณีดึงวันเดียวแบบเก่า
    return services.get_time_entries_report(
        db=db,
        employee_id_number=employee_id_number,
        entry_date=entry_date,
        skip=skip,
        limit=limit,
    )

# ---------- Working Schedules ----------
@api_router.post("/working-schedules/", response_model=schemas.WorkingScheduleInDB, status_code=status.HTTP_201_CREATED)
def create_working_schedule(schedule: schemas.WorkingScheduleCreate, db: Session = Depends(get_db)):
    return services.create_working_schedule(db=db, schedule=schedule)

@api_router.get("/working-schedules/", response_model=List[schemas.WorkingScheduleInDB])
def list_working_schedules(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_working_schedules(db=db, skip=skip, limit=limit)

@api_router.get("/working-schedules/{schedule_id}", response_model=schemas.WorkingScheduleInDB)
def get_working_schedule(schedule_id: int, db: Session = Depends(get_db)):
    obj = services.get_working_schedule(db=db, schedule_id=schedule_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Working schedule not found")
    return obj

@api_router.put("/working-schedules/{schedule_id}", response_model=schemas.WorkingScheduleInDB)
def update_working_schedule(schedule_id: int, schedule_update: schemas.WorkingScheduleUpdate, db: Session = Depends(get_db)):
    obj = services.update_working_schedule(db=db, schedule_id=schedule_id, schedule_update=schedule_update)
    if not obj:
        raise HTTPException(status_code=404, detail="Working schedule not found")
    return obj

@api_router.delete("/working-schedules/{schedule_id}", status_code=status.HTTP_200_OK)
def delete_working_schedule(schedule_id: int, db: Session = Depends(get_db)):
    deleted = services.delete_working_schedule(db=db, schedule_id=schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Working schedule not found")
    return {"message": "ตารางเวลาทำงานถูกลบแล้ว"}

# ---------- Time Entries ----------
@api_router.post("/time-entries/", response_model=schemas.TimeEntryInDB, status_code=status.HTTP_201_CREATED)
def create_time_entry(time_entry: schemas.TimeEntryCreate, db: Session = Depends(get_db)):
    return services.create_time_entry(db=db, time_entry=time_entry)

@api_router.get("/time-entries/", response_model=List[schemas.TimeEntryInDB])
def list_time_entries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_time_entries(db=db, skip=skip, limit=limit)

@api_router.get("/time-entries/{entry_id}", response_model=schemas.TimeEntryInDB)
def get_time_entry(entry_id: int, db: Session = Depends(get_db)):
    obj = services.get_time_entry(db=db, entry_id=entry_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกเวลา")
    return obj

@api_router.put("/time-entries/{entry_id}", response_model=schemas.TimeEntryInDB)
def update_time_entry(entry_id: int, time_entry_update: schemas.TimeEntryUpdate, db: Session = Depends(get_db)):
    obj = services.update_time_entry(db=db, entry_id=entry_id, time_entry_update=time_entry_update)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกเวลา")
    return obj

@api_router.delete("/time-entries/{entry_id}", status_code=status.HTTP_200_OK)
def delete_time_entry(entry_id: int, db: Session = Depends(get_db)):
    deleted = services.delete_time_entry(db=db, entry_id=entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกเวลา")
    return {"message": "บันทึกเวลาถูกลบแล้ว"}

@api_router.post("/time-entries/import", status_code=status.HTTP_200_OK)
async def import_time_entries(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not (file.filename.endswith(".csv") or file.filename.endswith(".xlsx")):
        raise HTTPException(status_code=400, detail="ไฟล์ต้องเป็น CSV หรือ Excel (.xlsx)")
    try:
        content = await file.read()
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.StringIO(content.decode("utf-8")))
        else:
            df = pd.read_excel(io.BytesIO(content))
        count = services.import_time_entries_from_csv_or_excel(db, df)
        return {"message": f"นำเข้าข้อมูลสำเร็จ {count} รายการ", "imported_count": count}
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="ไฟล์ข้อมูลว่างเปล่า")
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"ไฟล์ต้องมีคอลัมน์ที่จำเป็น: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการนำเข้า: {e}")

# ---------- Leave Types ----------
@api_router.post("/leave-types/", response_model=schemas.LeaveTypeInDB, status_code=status.HTTP_201_CREATED)
def create_leave_type(leave_type: schemas.LeaveTypeCreate, db: Session = Depends(get_db)):
    return services.create_leave_type(db=db, leave_type=leave_type)

@api_router.get("/leave-types/", response_model=List[schemas.LeaveTypeInDB])
def list_leave_types(skip: int = 0, limit: int = 100,
                     affects_balance: bool | None = Query(None),
                     db: Session = Depends(get_db)):
    return services.get_leave_types(db=db, skip=skip, limit=limit, affects_balance=affects_balance)

@api_router.get("/leave-types/{leave_type_id}", response_model=schemas.LeaveTypeInDB)
def get_leave_type(leave_type_id: int, db: Session = Depends(get_db)):
    obj = services.get_leave_type(db=db, leave_type_id=leave_type_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบประเภทการลา")
    return obj

@api_router.put("/leave-types/{leave_type_id}", response_model=schemas.LeaveTypeInDB)
def update_leave_type(leave_type_id: int, leave_type_update: schemas.LeaveTypeUpdate, db: Session = Depends(get_db)):
    obj = services.update_leave_type(db=db, leave_type_id=leave_type_id, leave_type_update=leave_type_update)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบประเภทการลา")
    return obj

@api_router.delete("/leave-types/{leave_type_id}", status_code=status.HTTP_200_OK)
def delete_leave_type(leave_type_id: int, db: Session = Depends(get_db)):
    deleted = services.delete_leave_type(db=db, leave_type_id=leave_type_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ไม่พบประเภทการลา")
    return {"message": "ประเภทการลาถูกลบแล้ว"}

# ---------- Overtime Types ----------
@api_router.post("/ot-types/", response_model=schemas.OvertimeTypeInDB, status_code=status.HTTP_201_CREATED)
async def create_ot_type(request: Request, db: Session = Depends(get_db)):
    ctype = (request.headers.get("content-type") or "").lower()
    if ctype.startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
        data["is_active"] = str(form.get("is_active", "true")).lower() in ("true", "1", "on", "yes")
        raw_rate = str(form.get("rate_multiplier", "")).replace(",", ".")
        data["rate_multiplier"] = float(raw_rate) if raw_rate else None

    try:
        payload = schemas.OvertimeTypeCreate(**data)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"ข้อมูลไม่ถูกต้อง: {e}")
    return services.create_ot_type(db=db, ot_type=payload)

@api_router.get("/ot-types/", response_model=List[schemas.OvertimeTypeInDB])
def list_ot_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_ot_types(db=db, skip=skip, limit=limit)

@api_router.put("/ot-types/{ot_type_id}", response_model=schemas.OvertimeTypeInDB)
def update_ot_type(ot_type_id: int, ot_type_update: schemas.OvertimeTypeUpdate, db: Session = Depends(get_db)):
    obj = services.update_ot_type(db=db, ot_type_id=ot_type_id, ot_type_update=ot_type_update)
    if not obj:
        raise HTTPException(status_code=404, detail="Overtime Type not found")
    return obj

@api_router.delete("/ot-types/{ot_type_id}", status_code=status.HTTP_200_OK)
def delete_ot_type(ot_type_id: int, db: Session = Depends(get_db)):
    return services.delete_ot_type(db=db, ot_type_id=ot_type_id)

# ---------- Overtime Requests ----------
@api_router.post("/ot-requests/", response_model=schemas.OvertimeRequestInDB, status_code=status.HTTP_201_CREATED)
def create_ot_request(ot_request: schemas.OvertimeRequestCreate, db: Session = Depends(get_db)):
    return services.create_ot_request(db=db, ot_request=ot_request)

@api_router.get("/ot-requests/", response_model=List[schemas.OvertimeRequestInDB])
def list_ot_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_ot_requests(db=db, skip=skip, limit=limit)

@api_router.get("/ot-requests/{request_id}", response_model=schemas.OvertimeRequestInDB)
def get_ot_request(request_id: int, db: Session = Depends(get_db)):
    obj = services.get_ot_request(db=db, request_id=request_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Overtime Request not found")
    return obj

@api_router.put("/ot-requests/{request_id}", response_model=schemas.OvertimeRequestInDB)
def update_ot_request(request_id: int, ot_request_update: schemas.OvertimeRequestUpdate, db: Session = Depends(get_db)):
    obj = services.update_ot_request(db=db, request_id=request_id, ot_request_update=ot_request_update)
    if not obj:
        raise HTTPException(status_code=404, detail="Overtime Request not found")
    return obj

@api_router.delete("/ot-requests/{request_id}", status_code=status.HTTP_200_OK)
def delete_ot_request(request_id: int, db: Session = Depends(get_db)):
    deleted = services.delete_ot_request(db=db, request_id=request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Overtime Request not found")
    return {"message": "OT request deleted successfully."}

# ---------- Holidays ----------
@api_router.post("/holidays/", response_model=schemas.HolidayInDB, status_code=status.HTTP_201_CREATED)
def create_holiday(holiday: schemas.HolidayCreate, db: Session = Depends(get_db)):
    return services.create_holiday(db=db, holiday=holiday)

@api_router.get("/holidays/", response_model=List[schemas.HolidayInDB])
def list_holidays(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_holidays(db=db, skip=skip, limit=limit)

@api_router.get("/holidays/{holiday_id}", response_model=schemas.HolidayInDB)
def get_holiday(holiday_id: int, db: Session = Depends(get_db)):
    obj = services.get_holiday(db=db, holiday_id=holiday_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบวันหยุด")
    return obj

@api_router.put("/holidays/{holiday_id}", response_model=schemas.HolidayInDB)
def update_holiday(holiday_id: int, holiday_update: schemas.HolidayUpdate, db: Session = Depends(get_db)):
    obj = services.update_holiday(db=db, holiday_id=holiday_id, holiday_update=holiday_update)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบวันหยุด")
    return obj

@api_router.delete("/holidays/{holiday_id}", status_code=status.HTTP_200_OK)
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    deleted = services.delete_holiday(db=db, holiday_id=holiday_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="ไม่พบวันหยุด")
    return {"message": "วันหยุดถูกลบแล้ว"}
