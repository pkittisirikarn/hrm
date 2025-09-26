from __future__ import annotations

from datetime import datetime, date, time, timedelta
from typing import List, Optional
from os import getenv

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .models import AttendanceDaily, AttendanceStatus, DayOfWeek
from modules.data_management.models import Employee

# -------------------- Time entries (report/import) --------------------
def get_time_entries_report(db: Session, employee_id_number: Optional[str] = None,
                            entry_date: Optional[date] = None, skip: int = 0, limit: int = 100):
    q = db.query(models.TimeEntry).options(joinedload(models.TimeEntry.employee))
    if employee_id_number:
        q = (q.join(Employee, models.TimeEntry.employee_id == Employee.id)
               .filter(Employee.employee_id_number.ilike(f"%{employee_id_number}%")))
    if entry_date:
        q = q.filter(func.date(models.TimeEntry.check_in_time) == entry_date)
    return q.order_by(models.TimeEntry.check_in_time.desc()).offset(skip).limit(limit).all()

def import_time_entries_from_csv_or_excel(db: Session, df: pd.DataFrame) -> int:
    created = updated = 0
    df.columns = df.columns.str.strip()
    req = ['Employee ID', 'Time']
    if not all(c in df.columns for c in req):
        missing = [c for c in req if c not in df.columns]
        raise KeyError(f"Missing required columns: {', '.join(missing)}")
    df['Time'] = pd.to_datetime(df['Time'], errors='coerce'); df.dropna(subset=['Time'], inplace=True)
    grouped = df.groupby([df['Employee ID'], df['Time'].dt.date])

    for (emp_code, d), day_df in grouped:
        emp = db.query(Employee).filter(Employee.employee_id_number == str(emp_code)).first()
        if not emp: continue
        ci = day_df['Time'].min(); co = day_df['Time'].max(); 
        if len(day_df) < 2: co = None

        exist = db.query(models.TimeEntry).filter(
            models.TimeEntry.employee_id == emp.id,
            func.date(models.TimeEntry.check_in_time) == d
        ).first()
        if exist:
            exist.check_in_time = ci; exist.check_out_time = co; db.add(exist); updated += 1
        else:
            db.add(models.TimeEntry(employee_id=emp.id, check_in_time=ci, check_out_time=co,
                                    status=models.TimeEntryStatus.APPROVED)); created += 1
    db.commit(); return created + updated

# -------------------- Leave overlap check --------------------
def check_for_overlapping_leave(db: Session, employee_id: int, start_date: datetime,
                                end_date: datetime, existing_request_id: Optional[int] = None):
    q = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status.in_([models.LeaveStatus.PENDING, models.LeaveStatus.APPROVED]),
        models.LeaveRequest.start_date < end_date,
        models.LeaveRequest.end_date > start_date
    )
    if existing_request_id:
        q = q.filter(models.LeaveRequest.id != existing_request_id)
    overlap = q.first()
    if overlap:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"An overlapping leave request (ID: {overlap.id}) already exists for this period.")

# -------------------- Working Schedule CRUD --------------------
def create_working_schedule(db: Session, schedule: schemas.WorkingScheduleCreate):
    obj = models.WorkingSchedule(**schedule.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_working_schedule(db: Session, schedule_id: int):
    return db.query(models.WorkingSchedule).filter(models.WorkingSchedule.id == schedule_id).first()
def get_working_schedules(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.WorkingSchedule).offset(skip).limit(limit).all()
def update_working_schedule(db: Session, schedule_id: int, schedule_update: schemas.WorkingScheduleUpdate):
    obj = get_working_schedule(db, schedule_id); 
    if not obj: return None
    for k,v in schedule_update.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_working_schedule(db: Session, schedule_id: int):
    obj = get_working_schedule(db, schedule_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return {"message": "ตารางเวลาทำงานถูกลบแล้ว"}

# -------------------- Time Entry CRUD --------------------
def create_time_entry(db: Session, time_entry: schemas.TimeEntryCreate):
    obj = models.TimeEntry(**time_entry.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_time_entry(db: Session, entry_id: int):
    return (db.query(models.TimeEntry).options(joinedload(models.TimeEntry.employee))
            .filter(models.TimeEntry.id == entry_id).first())
def get_time_entries(db: Session, skip: int = 0, limit: int = 100):
    return (db.query(models.TimeEntry).options(joinedload(models.TimeEntry.employee))
            .offset(skip).limit(limit).all())
def update_time_entry(db: Session, entry_id: int, time_entry_update: schemas.TimeEntryUpdate):
    obj = get_time_entry(db, entry_id); 
    if not obj: return None
    for k,v in time_entry_update.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_time_entry(db: Session, entry_id: int):
    obj = get_time_entry(db, entry_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return {"message": "บันทึกเวลาถูกลบแล้ว"}

# -------------------- Leave Types CRUD --------------------
def create_leave_type(db: Session, leave_type: schemas.LeaveTypeCreate):
    obj = models.LeaveType(**leave_type.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_leave_type(db: Session, leave_type_id: int):
    return db.query(models.LeaveType).filter(models.LeaveType.id == leave_type_id).first()
def get_leave_types(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.LeaveType).offset(skip).limit(limit).all()
def update_leave_type(db: Session, leave_type_id: int, leave_type_update: schemas.LeaveTypeUpdate):
    obj = get_leave_type(db, leave_type_id); 
    if not obj: return None
    for k,v in leave_type_update.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_leave_type(db: Session, leave_type_id: int):
    obj = get_leave_type(db, leave_type_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return {"message": "ประเภทการลาถูกลบแล้ว"}

# -------------------- Leave Requests CRUD --------------------
def create_leave_request(db: Session, leave_request: schemas.LeaveRequestCreate):
    check_for_overlapping_leave(db, leave_request.employee_id, leave_request.start_date, leave_request.end_date)
    obj = models.LeaveRequest(**leave_request.model_dump(), request_date=datetime.utcnow())
    db.add(obj); db.commit(); db.refresh(obj); return obj

def get_leave_request(db: Session, request_id: int):
    obj = (db.query(models.LeaveRequest)
             .options(joinedload(models.LeaveRequest.employee), joinedload(models.LeaveRequest.leave_type))
             .filter(models.LeaveRequest.id == request_id).first())
    if obj:
        delta = obj.end_date - obj.start_date
        obj.num_days = delta.total_seconds() / (8 * 3600)
    return obj

def get_leave_requests(db: Session, skip: int = 0, limit: int = 100):
    rows = (db.query(models.LeaveRequest)
              .options(joinedload(models.LeaveRequest.employee), joinedload(models.LeaveRequest.leave_type))
              .offset(skip).limit(limit).all())
    for r in rows:
        delta = r.end_date - r.start_date
        r.num_days = delta.total_seconds() / (8 * 3600)
    return rows

def update_leave_request(db: Session, request_id: int, leave_request_update: schemas.LeaveRequestUpdate):
    obj = db.query(models.LeaveRequest).filter(models.LeaveRequest.id == request_id).first()
    if not obj: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")
    data = leave_request_update.model_dump(exclude_unset=True)
    check_for_overlapping_leave(db, data.get("employee_id", obj.employee_id),
                                data.get("start_date", obj.start_date), data.get("end_date", obj.end_date),
                                existing_request_id=request_id)
    for k,v in data.items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj)
    delta = obj.end_date - obj.start_date
    obj.num_days = delta.total_seconds() / (8 * 3600)
    return obj

def delete_leave_request(db: Session, request_id: int):
    obj = get_leave_request(db, request_id)
    if not obj: return None
    db.delete(obj); db.commit(); return {"message": "คำขอลาถูกลบแล้ว"}

# -------------------- Holidays CRUD --------------------
def create_holiday(db: Session, holiday: schemas.HolidayCreate):
    obj = models.Holiday(**holiday.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_holiday(db: Session, holiday_id: int):
    return db.query(models.Holiday).filter(models.Holiday.id == holiday_id).first()
def get_holidays(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Holiday).offset(skip).limit(limit).all()
def update_holiday(db: Session, holiday_id: int, holiday_update: schemas.HolidayUpdate):
    obj = get_holiday(db, holiday_id); 
    if not obj: return None
    for k,v in holiday_update.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_holiday(db: Session, holiday_id: int):
    obj = get_holiday(db, holiday_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return {"message": "วันหยุดถูกลบแล้ว"}

# -------------------- OT Types CRUD --------------------
def create_ot_type(db: Session, ot_type: schemas.OvertimeTypeCreate):
    obj = models.OvertimeType(**ot_type.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_ot_type(db: Session, ot_type_id: int):
    return db.query(models.OvertimeType).filter(models.OvertimeType.id == ot_type_id).first()
def get_ot_types(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.OvertimeType).offset(skip).limit(limit).all()
def update_ot_type(db: Session, ot_type_id: int, ot_type_update: schemas.OvertimeTypeUpdate):
    obj = get_ot_type(db, ot_type_id); 
    if not obj: return None
    for k,v in ot_type_update.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_ot_type(db: Session, ot_type_id: int):
    obj = get_ot_type(db, ot_type_id); 
    if not obj: return None
    if getattr(obj, "ot_requests", None):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Cannot delete Overtime Type because it is currently in use by OT requests.")
    db.delete(obj); db.commit(); return {"message": "Overtime Type deleted successfully."}

# -------------------- OT Requests CRUD --------------------
def check_for_overlapping_ot(
    db: Session,
    employee_id: int,
    start_time: datetime,
    end_time: datetime,
    existing_request_id: Optional[int] = None
):
    """
    กันการซ้อนทับช่วงเวลา OT เฉพาะรายการที่สถานะ 'รอดำเนินการ/อนุมัติ'
    รองรับทั้งกรณี status เป็น Enum (OvertimeStatus/LeaveStatus) หรือเป็นข้อความ
    """
    # เตรียมค่าที่ถือว่า "ใช้งานอยู่" สำหรับการกันซ้อน
    active_statuses = []

    # ถ้ามี Enum OvertimeStatus ใช้ก่อน
    if hasattr(models, "OvertimeStatus"):
        active_statuses += [models.OvertimeStatus.PENDING, models.OvertimeStatus.APPROVED]
    # บางโปรเจกต์ใช้ LeaveStatus กับตาราง OT
    if hasattr(models, "LeaveStatus"):
        active_statuses += [models.LeaveStatus.PENDING, models.LeaveStatus.APPROVED]

    # เติมสำรองเป็นสตริง (กรณีคอลัมน์เป็น String)
    active_statuses += ["PENDING", "APPROVED", "Pending", "Approved", "รอ", "อนุมัติ"]

    q = db.query(models.OvertimeRequest).filter(
        models.OvertimeRequest.employee_id == employee_id,
        models.OvertimeRequest.status.in_(active_statuses),
        models.OvertimeRequest.start_time < end_time,
        models.OvertimeRequest.end_time > start_time,
    )
    if existing_request_id:
        q = q.filter(models.OvertimeRequest.id != existing_request_id)

    overlap = q.first()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An overlapping OT request (ID: {overlap.id}) already exists for this period."
        )

def create_ot_request(db: Session, ot_request: schemas.OvertimeRequestCreate):
    check_for_overlapping_ot(db, ot_request.employee_id, ot_request.start_time, ot_request.end_time)
    obj = models.OvertimeRequest(**ot_request.model_dump(), request_date=datetime.utcnow())
    db.add(obj); db.commit(); db.refresh(obj); return obj

def get_ot_request(db: Session, request_id: int):
    return (db.query(models.OvertimeRequest)
              .options(joinedload(models.OvertimeRequest.employee), joinedload(models.OvertimeRequest.ot_type))
              .filter(models.OvertimeRequest.id == request_id).first())

def get_ot_requests(db: Session, skip: int = 0, limit: int = 100):
    return (db.query(models.OvertimeRequest)
              .options(joinedload(models.OvertimeRequest.employee), joinedload(models.OvertimeRequest.ot_type))
              .order_by(models.OvertimeRequest.request_date.desc())
              .offset(skip).limit(limit).all())

def update_ot_request(db: Session, request_id: int, ot_request_update: schemas.OvertimeRequestUpdate):
    obj = get_ot_request(db, request_id)
    if not obj: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OT request not found")
    data = ot_request_update.model_dump(exclude_unset=True)
    check_for_overlapping_ot(db, data.get("employee_id", obj.employee_id),
                             data.get("start_time", obj.start_time), data.get("end_time", obj.end_time),
                             existing_request_id=request_id)
    for k,v in data.items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

def delete_ot_request(db: Session, request_id: int):
    obj = get_ot_request(db, request_id)
    if not obj: return None
    db.delete(obj); db.commit(); return {"message": "OT request deleted successfully."}

# -------------------- Attendance Daily (policy/compute) --------------------
def _minutes_between(a: Optional[datetime], b: Optional[datetime]) -> int:
    if not a or not b: return 0
    return max(0, int((b - a).total_seconds() // 60))

def _calc_break_minutes(ws) -> int:
    if getattr(ws, "break_minutes_override", None) is not None:
        return int(ws.break_minutes_override or 0)
    bst = getattr(ws, "break_start_time", None); bet = getattr(ws, "break_end_time", None)
    if bst and bet:
        dummy = datetime(2000, 1, 1)
        return _minutes_between(datetime.combine(dummy, bst), datetime.combine(dummy, bet))
    return 0

def _env_int(name: str, default: int) -> int:
    try:
        v = int(getenv(name, str(default)).strip())
        return max(0, v)
    except Exception:
        return default

def _env_time(name: str, default_hhmm: str) -> time:
    raw = (getenv(name) or "").strip()
    try:
        if raw: return datetime.strptime(raw, "%H:%M").time()
    except Exception:
        pass
    return datetime.strptime(default_hhmm, "%H:%M").time()

DEF_LATE_GRACE_MIN        = _env_int("ATT_DEFAULT_LATE_GRACE_MIN", 5)
DEF_EARLY_LEAVE_GRACE_MIN = _env_int("ATT_DEFAULT_EARLY_LEAVE_GRACE_MIN", 0)
DEF_ABSENCE_AFTER_MIN     = _env_int("ATT_DEFAULT_ABSENCE_AFTER_MIN", 240)
DEF_STD_DAILY_MINUTES     = _env_int("ATT_DEFAULT_STANDARD_DAILY_MINUTES", 480)
DEF_START_TIME            = _env_time("ATT_DEFAULT_START_TIME", "08:30")
DEF_END_TIME              = _env_time("ATT_DEFAULT_END_TIME", "17:30")

def _get_schedule_for_day(db: Session, employee_id: int, day: date):
    wd_idx = day.weekday()
    idx_to_enum = {0: DayOfWeek.MONDAY, 1: DayOfWeek.TUESDAY, 2: DayOfWeek.WEDNESDAY,
                   3: DayOfWeek.THURSDAY, 4: DayOfWeek.FRIDAY, 5: DayOfWeek.SATURDAY, 6: DayOfWeek.SUNDAY}
    dow = idx_to_enum[wd_idx]

    base_q = (db.query(models.WorkingSchedule)
                .filter(models.WorkingSchedule.day_of_week == dow)
                .filter(models.WorkingSchedule.is_active == True))
    sch = (base_q.filter(models.WorkingSchedule.employee_id == employee_id)
                 .order_by(models.WorkingSchedule.is_default.desc(), models.WorkingSchedule.id.asc()).first())
    if sch: return sch
    return (base_q.filter(models.WorkingSchedule.employee_id.is_(None))
                 .order_by(models.WorkingSchedule.is_default.desc(), models.WorkingSchedule.id.asc()).first())

# def _break_minutes_for_any_day(db: Session, employee_id: int, day: date) -> int:
#     """
#     คืนค่านาทีพักจาก WorkingSchedule ของวันนั้น ๆ
#     - ใช้ break_minutes_override ถ้ามี
#     - ไม่สนใจว่าเป็นวันทำงานหรือไม่ (is_working_day=False ก็ยังอ่านได้)
#     - ถ้าไม่พบตารางเลย คืน 0
#     """
#     sch = _get_schedule_for_day(db, employee_id, day)
#     if not sch:
#         return 0
#     return _calc_break_minutes(sch)

def _policy_from_schedule(sch) -> dict:
    late_grace    = getattr(sch, "late_grace_min", None)
    early_grace   = getattr(sch, "early_leave_grace_min", None) or getattr(sch, "early_grace_min", None)
    absence_after = getattr(sch, "absence_after_min", None)
    std_minutes   = getattr(sch, "standard_daily_minutes", None)
    break_min     = _calc_break_minutes(sch)
    is_working    = getattr(sch, "is_working_day", True)
    start_t = getattr(sch, "start_time", None) or DEF_START_TIME
    end_t   = getattr(sch, "end_time",   None) or DEF_END_TIME
    return {
        "start_time": start_t,
        "end_time":   end_t,
        "late_grace_min":        late_grace if isinstance(late_grace, int) else DEF_LATE_GRACE_MIN,
        "early_leave_grace_min": early_grace if isinstance(early_grace, int) else DEF_EARLY_LEAVE_GRACE_MIN,
        "absence_after_min":     absence_after if isinstance(absence_after, int) else DEF_ABSENCE_AFTER_MIN,
        "standard_daily_minutes":std_minutes if isinstance(std_minutes, int) else DEF_STD_DAILY_MINUTES,
        "break_minutes":         break_min,
        "is_workday":            bool(is_working),
    }

# ---------- FIX 1: คำนวณ OT ก่อน return (และใส่ลง dict ที่ส่งคืน) ----------
def _classify_attendance_for_day(db: Session, employee_id: int, day: date) -> Optional[dict]:
    # Leave (อนุมัติ)
    lr = (
        db.query(models.LeaveRequest)
          .filter(models.LeaveRequest.employee_id == employee_id)
          .filter(models.LeaveRequest.status == models.LeaveStatus.APPROVED)
          .filter(models.LeaveRequest.start_date <= day)
          .filter(models.LeaveRequest.end_date >= day)
          .first()
    )
    if lr:
        is_paid = True
        try:
            lt = db.query(models.LeaveType).get(lr.leave_type_id)
            if hasattr(lt, "is_paid_leave"):
                is_paid = bool(lt.is_paid_leave)
            elif hasattr(lt, "is_paid"):
                is_paid = bool(lt.is_paid)
        except Exception:
            pass
        # วันลาไม่คิด OT
        return dict(
            status_code=AttendanceStatus.LEAVE.value,
            late_minutes=0,
            early_leave_minutes=0,
            work_minutes=0,
            is_paid_leave=is_paid,
            ot_weekday_minutes=0,
            ot_holiday_minutes=0,
        )

    sch = _get_schedule_for_day(db, employee_id, day)
    if not sch:
        # ไม่มีตาราง -> ข้ามไป (holiday OT จะถูกคิดผ่าน fallback ใน get_attendance_metrics())
        return None
    policy = _policy_from_schedule(sch)
    if not policy["is_workday"]:
        # วันหยุดตามตาราง -> ข้ามไป (ให้ metrics ใช้ fallback จาก OT requests)
        return None

    # time entry ของวันนั้น
    day_start = datetime.combine(day, time(0, 0, 0))
    day_end   = day_start + timedelta(days=1)
    te = (
        db.query(models.TimeEntry)
          .filter(models.TimeEntry.employee_id == employee_id)
          .filter(models.TimeEntry.check_in_time >= day_start)
          .filter(models.TimeEntry.check_in_time <  day_end)
          .first()
    )
    if not te:
        return dict(
            status_code=AttendanceStatus.ABSENCE.value,
            late_minutes=0,
            early_leave_minutes=0,
            work_minutes=0,
            is_paid_leave=False,
            ot_weekday_minutes=0,
            ot_holiday_minutes=0,
        )

    start_dt = datetime.combine(day, policy["start_time"])
    end_dt   = datetime.combine(day, policy["end_time"])
    ci = te.check_in_time or start_dt
    co = te.check_out_time or ci
    if co < ci:
        co = ci

    raw_late  = max(0, int((ci - start_dt).total_seconds() // 60))
    late_minutes = max(0, raw_late - policy["late_grace_min"])
    raw_early = max(0, int((end_dt - co).total_seconds() // 60))
    early_leave_minutes = max(0, raw_early - policy["early_leave_grace_min"])
    work_minutes = max(0, int((co - ci).total_seconds() // 60) - policy["break_minutes"])

    if work_minutes < policy["absence_after_min"]:
        return dict(
            status_code=AttendanceStatus.ABSENCE.value,
            late_minutes=0,
            early_leave_minutes=0,
            work_minutes=work_minutes,
            is_paid_leave=False,
            ot_weekday_minutes=0,
            ot_holiday_minutes=0,
        )

    # --- คำนวณ OT สำหรับ "วันทำงาน" ---
    ot_weekday_minutes = 0
    if te and co and co > end_dt:
        ot_weekday_minutes = max(0, int((co - end_dt).total_seconds() // 60))

    status_code = AttendanceStatus.LATE.value if late_minutes > 0 else AttendanceStatus.PRESENT.value
    return dict(
        status_code=status_code,
        late_minutes=late_minutes,
        early_leave_minutes=early_leave_minutes,
        work_minutes=work_minutes,
        is_paid_leave=True,
        ot_weekday_minutes=ot_weekday_minutes,
        ot_holiday_minutes=0,   # วันทำงานไม่คิด holiday OT ตรงนี้
    )

def rebuild_attendance_range(
    db: Session,
    start: date,
    end: date,
    employee_id: Optional[int] = None,
    debug: bool = True,
):
    # เลือกพนักงาน
    q_emp = db.query(Employee)
    if employee_id:
        q_emp = q_emp.filter(Employee.id == employee_id)
    employees = q_emp.all()

    # ลบข้อมูลเดิมในช่วงนี้
    q_del = db.query(AttendanceDaily).filter(
        AttendanceDaily.day >= start,
        AttendanceDaily.day <= end,
    )
    if employee_id:
        q_del = q_del.filter(AttendanceDaily.employee_id == employee_id)
    q_del.delete(synchronize_session=False)

    # วนทุกวันในช่วง
    cur = start
    while cur <= end:
        for emp in employees:
            res = _classify_attendance_for_day(db, emp.id, cur)

            # debug log
            if debug:
                if res:
                    print(
                        f"[ATT] emp={emp.id} day={cur} "
                        f"status={res.get('status_code')} "
                        f"work={res.get('work_minutes', 0)} "
                        f"late={res.get('late_minutes', 0)} "
                        f"early={res.get('early_leave_minutes', 0)}"
                    )
                else:
                    print(f"[ATT] emp={emp.id} day={cur} status=SKIP (no schedule / non-working day)")

            if not res:
                continue

            # เตรียมค่า
            status_code = res.get("status_code", AttendanceStatus.PRESENT.value)
            work_minutes = int(res.get("work_minutes", 0) or 0)
            late_minutes = int(res.get("late_minutes", 0) or 0)
            early_leave_minutes = int(res.get("early_leave_minutes", 0) or 0)
            is_paid_leave = bool(res.get("is_paid_leave", True))
            ot_wd = int(res.get("ot_weekday_minutes", 0) or 0)
            ot_hol = int(res.get("ot_holiday_minutes", 0) or 0)

            if status_code == AttendanceStatus.ABSENCE.value:
                # ถ้าเป็นขาดงาน ไม่คิด late/early และไม่บันทึก OT
                late_minutes = 0
                early_leave_minutes = 0
                ot_wd = 0
                ot_hol = 0

            # ใส่เฉพาะคอลัมน์ที่มีจริงในตาราง
            payload = {
                "employee_id": emp.id,
                "day": cur,
                "status_code": status_code,
                "work_minutes": work_minutes,
                "late_minutes": late_minutes,
                "early_leave_minutes": early_leave_minutes,
                "is_paid_leave": is_paid_leave,
            }
            if "ot_weekday_minutes" in AttendanceDaily.__table__.c:
                payload["ot_weekday_minutes"] = ot_wd
            if "ot_holiday_minutes" in AttendanceDaily.__table__.c:
                payload["ot_holiday_minutes"] = ot_hol

            db.add(AttendanceDaily(**payload))

        cur += timedelta(days=1)

    db.commit()

def _break_minutes_for_any_day(db: Session, employee_id: int, day: date) -> int:
    """
    คืนค่านาทีพักจาก WorkingSchedule ของวันนั้น ๆ
    - ใช้ break_minutes_override ถ้ามี ไม่งั้นคำนวณจาก break_start_time/break_end_time
    - ไม่สนใจว่าเป็นวันทำงานหรือไม่ (ใช้เพื่อหักเวลาพักของ OT วันหยุดได้)
    """
    sch = _get_schedule_for_day(db, employee_id, day)
    if not sch:
        return 0
    return _calc_break_minutes(sch)

# -------------------- Break override helper -------------------
def _get_break_override_minutes(db: Session, employee_id: int, weekday: int) -> int:
    """
    คืนค่านาทีพักจาก WorkingSchedule ของวันในสัปดาห์ที่ระบุ (0=Mon .. 6=Sun)
    เลือกของพนักงานก่อน ถ้าไม่มีค่อยใช้ template (employee_id is NULL)
    รองรับหลายชื่อฟิลด์ เช่น break_override_minutes, break_override (int)
    """
    try:
        from modules.time_tracking import models as tm
        WS = getattr(tm, "WorkingSchedule")
    except Exception:
        return 0

    q = (
        db.query(WS)
          .filter(WS.is_active == True, WS.day_of_week == weekday)
          .filter(or_(WS.employee_id == employee_id, WS.employee_id == None))
          .order_by(WS.employee_id.desc())           # ของพนักงานมี priority สูงกว่า
    )
    ws = q.first()
    if not ws:
        return 0

    for fld in ("break_override_minutes", "break_override", "break_minutes_override"):
        if hasattr(ws, fld):
            try:
                val = int(getattr(ws, fld) or 0)
                return max(0, val)
            except Exception:
                pass
    return 0


# -------------------- Attendance metrics (with OT fallback & break) --------------------
def get_attendance_metrics(db: Session, employee_id: int, start: date, end: date) -> dict:
    rows = (
        db.query(AttendanceDaily)
          .filter(
              AttendanceDaily.employee_id == employee_id,
              AttendanceDaily.day >= start,
              AttendanceDaily.day <= end
          ).all()
    )

    # ===== metrics หลักจาก AttendanceDaily =====
    late_minutes = sum((getattr(r, "late_minutes", 0) or 0) for r in rows)
    early_leave_minutes = (
        sum((getattr(r, "early_leave_minutes", 0) or 0) for r in rows)
        if "early_leave_minutes" in AttendanceDaily.__table__.c else 0
    )
    absent_days = sum(1 for r in rows if r.status_code == AttendanceStatus.ABSENCE.value)
    unpaid_leave_days = sum(
        1 for r in rows
        if (r.status_code == AttendanceStatus.LEAVE.value and not bool(getattr(r, "is_paid_leave", False)))
    )
    work_minutes = (
        sum((getattr(r, "work_minutes", 0) or 0) for r in rows)
        if "work_minutes" in AttendanceDaily.__table__.c else 0
    )

    has_ot_wd  = "ot_weekday_minutes" in AttendanceDaily.__table__.c
    has_ot_hol = "ot_holiday_minutes" in AttendanceDaily.__table__.c
    ot_weekday_minutes = sum((getattr(r, "ot_weekday_minutes", 0) or 0) for r in rows) if has_ot_wd else 0
    ot_holiday_minutes = sum((getattr(r, "ot_holiday_minutes", 0) or 0) for r in rows) if has_ot_hol else 0

    print(f"[OTDBG] emp={employee_id} period={start}..{end} "
          f"att_rows={len(rows)} att_ot_wd={ot_weekday_minutes} att_ot_hol={ot_holiday_minutes} "
          f"(has_cols wd={has_ot_wd} hol={has_ot_hol})")

    # ===== Fallback: ใช้ OT Requests ที่ "อนุมัติ" และหักพัก (override) =====
    # จะทำงานเมื่อไม่มีคอลัมน์ OT ใน Attendance หรือมีแต่รวมแล้วยังเป็น 0
    wd1_min = 0   # 1x
    wd15_min = 0  # 1.5x
    hol3_min = 0  # 3x

    if (not has_ot_wd and not has_ot_hol) or (ot_weekday_minutes + ot_holiday_minutes) == 0:
        # หาโมเดลแบบปลอดภัย
        OTRequest = None
        OTType = None
        try:
            if hasattr(models, "OvertimeRequest"):
                OTRequest = getattr(models, "OvertimeRequest")
            elif hasattr(models, "OTRequest"):
                OTRequest = getattr(models, "OTRequest")

            if hasattr(models, "OvertimeType"):
                OTType = getattr(models, "OvertimeType")
            elif hasattr(models, "OTType"):
                OTType = getattr(models, "OTType")
        except Exception as e:
            print(f"[OTDBG] !! model lookup failed: {e}")
            OTRequest = OTType = None

        def _is_approved(val) -> bool:
            try:
                name = getattr(val, "name", None)
                if name:
                    return name.upper() == "APPROVED"
            except Exception:
                pass
            s = str(val or "").strip()
            return s.upper() == "APPROVED" or s == "อนุมัติ"

        def _is_holiday_type(ot_type_obj) -> bool:
            # true ถ้ามีธง is_holiday หรือ multiplier >= 2.5 หรือชื่อสื่อว่า holiday/3x
            if hasattr(ot_type_obj, "is_holiday"):
                try:
                    if bool(getattr(ot_type_obj, "is_holiday")):
                        return True
                except Exception:
                    pass
            mult = getattr(ot_type_obj, "multiplier", None)
            try:
                if mult is not None and float(mult) >= 2.5:
                    return True
            except Exception:
                pass
            name = (getattr(ot_type_obj, "name", "") or "").lower()
            return ("holiday" in name) or ("x3" in name) or (" 3" in name) or name.strip().endswith("3")

        def _extract_multiplier(ot_type_obj) -> float:
            """
            พยายามอ่านตัวคูณจากหลายชื่อฟิลด์; ถ้าไม่ได้ ให้เดาจากชื่อประเภท
            """
            for fld in ("multiplier", "ot_multiplier", "rate", "factor"):
                if hasattr(ot_type_obj, fld):
                    try:
                        v = getattr(ot_type_obj, fld)
                        if v is not None:
                            fv = float(v)
                            if fv > 0:
                                return fv
                    except Exception:
                        pass
            name = (getattr(ot_type_obj, "name", "") or "").strip().lower()
            if "1.5" in name or "normal" in name:
                return 1.5
            if "holiday" in name or "x3" in name or name.endswith("3"):
                return 3.0
            if "weekend" in name or "x1" in name or name.endswith("1"):
                return 1.0
            return 1.0

        if OTRequest and OTType:
            p_start_dt = datetime.combine(start, time.min)
            p_end_dt   = datetime.combine(end,   time.max)

            q = (
                db.query(OTRequest, OTType)
                  .join(OTType, OTType.id == OTRequest.ot_type_id)
                  .filter(
                      OTRequest.employee_id == employee_id,
                      OTRequest.start_time <= p_end_dt,
                      OTRequest.end_time   >= p_start_dt,
                  )
            )
            rows_q = q.all()
            print(f"[OTDBG] fallback query rows={len(rows_q)} window={p_start_dt}..{p_end_dt}")

            for req, t in rows_q:
                raw_status = getattr(req, "status", None)
                if not _is_approved(raw_status):
                    continue

                # ตัดช่วงให้อยู่ในรอบ
                s = max(req.start_time, p_start_dt)
                e = min(req.end_time,   p_end_dt)
                if e <= s:
                    continue

                mins = int((e - s).total_seconds() // 60)

                # หักพักจาก WorkingSchedule (override) ตามวันของช่วง OT
                brk = _get_break_override_minutes(db, employee_id, s.weekday())
                eff_mins = max(0, mins - brk)

                mult = _extract_multiplier(t)

                print(f"[OTDBG]  + OT#{getattr(req,'id',None)} OK cut=[{s}..{e}] "
                      f"mins={mins} break={brk} eff={eff_mins} "
                      f"type='{getattr(t,'name',None)}' mult={mult}")

                # จัด bucket
                if _is_holiday_type(t):
                    hol3_min += eff_mins              # 3x
                elif mult >= 1.4:
                    wd15_min += eff_mins             # 1.5x
                else:
                    wd1_min  += eff_mins             # 1x

            print(f"[OTDBG] fallback totals -> 1x={wd1_min} 1.5x={wd15_min} 3x={hol3_min}")

            # map ให้กับคีย์เดิมเพื่อความเข้ากันได้กับสูตรเดิม
            ot_weekday_minutes = wd15_min          # ใช้แทน 1.5x
            ot_holiday_minutes = hol3_min          # ใช้แทน 3x
        else:
            print("[OTDBG] fallback skipped: missing OvertimeRequest/OvertimeType models")

    ot_total_minutes = (wd1_min + wd15_min + hol3_min) if (wd1_min or wd15_min or hol3_min) \
                       else (ot_weekday_minutes + ot_holiday_minutes)

    print(f"[OTDBG] FINAL ot_weekday(1.5x)={ot_weekday_minutes} "
          f"ot_holiday(3x)={ot_holiday_minutes} "
          f"ot1x={wd1_min} total={ot_total_minutes}")

    # คืนทั้งคีย์ใหม่และคีย์เดิม
    return {
        "late_minutes": late_minutes,
        "early_leave_minutes": early_leave_minutes,
        "absent_days": absent_days,
        "unpaid_leave_days": unpaid_leave_days,
        "work_minutes": work_minutes,

        # คีย์เดิม (เพื่อความเข้ากันได้กับสูตรที่มีอยู่)
        "ot_weekday_minutes": ot_weekday_minutes,   # 1.5x
        "ot_holiday_minutes": ot_holiday_minutes,   # 3x

        # คีย์ใหม่
        "ot1x_minutes": wd1_min,
        "ot15x_minutes": wd15_min,
        "ot3x_minutes": hol3_min,

        "ot_total_minutes": ot_total_minutes,
    }

# -------------------- debug helper --------------------
def debug_att_day(db: Session, employee_id: int, day: date):
    sch = _get_schedule_for_day(db, employee_id, day)
    print("=== DEBUG ATT ===")
    print("emp:", employee_id, "day:", day)
    if not sch:
        print("No schedule"); return
    policy = _policy_from_schedule(sch); print("policy:", policy)

    start_of_day = datetime.combine(day, time.min); end_of_day = start_of_day + timedelta(days=1)
    te = (db.query(models.TimeEntry)
            .filter(models.TimeEntry.employee_id == employee_id)
            .filter(models.TimeEntry.check_in_time >= start_of_day)
            .filter(models.TimeEntry.check_in_time <  end_of_day)
            .order_by(models.TimeEntry.check_in_time.asc()).first())
    print("time entry:", getattr(te, "check_in_time", None), getattr(te, "check_out_time", None))
    if not te:
        print("=> ABSENCE (no TE)"); return

    start_dt = datetime.combine(day, policy["start_time"]); end_dt = datetime.combine(day, policy["end_time"])
    ci = te.check_in_time or start_dt; co = te.check_out_time or ci
    raw_late = max(0, int((ci - start_dt).total_seconds() // 60)); late_m = max(0, raw_late - policy["late_grace_min"])
    raw_early = max(0, int((end_dt - co).total_seconds() // 60));  early_m = max(0, raw_early - policy["early_leave_grace_min"])
    work_m = max(0, int((co - ci).total_seconds() // 60) - int(policy["break_minutes"]))
    print(f"calc: start={start_dt.time()} end={end_dt.time()} ci={ci.time()} co={co.time()} work={work_m} late={late_m} early={early_m}")
    if work_m < int(policy["absence_after_min"]):
        print("=> ABSENCE (work_minutes below threshold)")
    else:
        print("=>", "LATE" if late_m > 0 else "PRESENT", "(early_leave:", early_m, ")")
