# modules/time_tracking/services.py
from __future__ import annotations

from datetime import datetime as _dt
from datetime import date, time, timedelta, datetime
from typing import List, Optional
from os import getenv
from typing import List, Optional, Iterable, Dict, Tuple, DefaultDict
from collections import defaultdict

import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy import or_, func, and_, text
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .models import (
    AttendanceDaily,
    AttendanceStatus,
    DayOfWeek,
    LeaveBalance,
    LeaveType,
    LeaveRequest,
    LeaveStatus,
)
from modules.data_management.models import Employee

# =====================================================================
# Environment / Defaults
# =====================================================================

def _env_int(name: str, default: int) -> int:
    try:
        v = int(getenv(name, str(default)).strip())
        return max(0, v)
    except Exception:
        return default

def _env_time(name: str, default_hhmm: str) -> time:
    raw = (getenv(name) or "").strip()
    try:
        if raw:
            return datetime.strptime(raw, "%H:%M").time()
    except Exception:
        pass
    return datetime.strptime(default_hhmm, "%H:%M").time()

DEF_LATE_GRACE_MIN        = _env_int("ATT_DEFAULT_LATE_GRACE_MIN", 5)
DEF_EARLY_LEAVE_GRACE_MIN = _env_int("ATT_DEFAULT_EARLY_LEAVE_GRACE_MIN", 0)
DEF_ABSENCE_AFTER_MIN     = _env_int("ATT_DEFAULT_ABSENCE_AFTER_MIN", 240)
DEF_STD_DAILY_MINUTES     = _env_int("ATT_DEFAULT_STANDARD_DAILY_MINUTES", 480)
DEF_START_TIME            = _env_time("ATT_DEFAULT_START_TIME", "08:30")
DEF_END_TIME              = _env_time("ATT_DEFAULT_END_TIME", "17:30")

STD_DAY_MINUTES = DEF_STD_DAILY_MINUTES  # alias

# =====================================================================
# Leave Balance core
# =====================================================================

def _days_between_std(start_dt: datetime, end_dt: datetime) -> float:
    """คำนวณวันจากนาทีจริง ÷ STD_DAY_MINUTES (ถ้า 0 นาทีให้นับเป็น 1 วัน)."""
    mins = max(0, int((end_dt - start_dt).total_seconds() // 60))
    if mins == 0:
        mins = STD_DAY_MINUTES
    return round(mins / float(STD_DAY_MINUTES), 4)

def get_or_create_leave_balance(db: Session, employee_id: int, leave_type_id: int, year: int):
    """
    คืน (LeaveBalance, created: bool). ถ้าไม่มีให้สร้างใหม่และตั้งค่าตัวเลขเป็น 0.0
    """
    lb = (
        db.query(models.LeaveBalance)
        .filter(
            models.LeaveBalance.employee_id == employee_id,
            models.LeaveBalance.leave_type_id == leave_type_id,
            models.LeaveBalance.year == year,
        )
        .first()
    )
    created = False
    if not lb:
        lb = models.LeaveBalance(
            employee_id=employee_id,
            leave_type_id=leave_type_id,
            year=year,
        )
        # เฉพาะฟิลด์ที่มีจริงในตาราง
        for name in ("opening", "accrued", "used", "adjusted", "carry_in"):
            if hasattr(models.LeaveBalance, name):
                setattr(lb, name, 0.0)
        db.add(lb)
        db.flush()
        created = True
    return lb, created

# ---------- Accrual helpers (optional, ใช้เมื่อมีฟิลด์ใน leave_types) ----------
_ANNUAL_LEAVE_KEYWORDS = {"annual", "vacation", "ลาพักร้อน", "พักร้อน"}

def _is_annual_leave(leave_type) -> bool:
    name = (getattr(leave_type, "name", "") or "").strip().lower()
    return any(k in name for k in _ANNUAL_LEAVE_KEYWORDS)

def _full_years_completed(hire_dt: date | datetime | None, as_of: date) -> int:
    """จำนวน 'ปีเต็ม' นับจากวันเริ่มงานจนถึงวัน as_of (นับครบรอบ)."""
    if not hire_dt:
        return 0
    if isinstance(hire_dt, datetime):
        hire_dt = hire_dt.date()
    years = as_of.year - hire_dt.year
    anniv = hire_dt.replace(year=as_of.year)
    if as_of < anniv:
        years -= 1
    return max(0, years)

def calc_opening_quota_for_year(employee, leave_type, year: int) -> float:
    """
    opening = base(annual_quota) + years_completed * accrue_per_year, เพดานด้วย max_quota (ถ้ามี)
    - ใช้กับประเภทที่ affects_balance=True
    - โดยดีฟอลต์ใช้กับ 'ลาพักร้อน' เท่านั้น (ดูชื่อ). ถ้าต้องการใช้ทุกประเภท ให้ตัด _is_annual_leave ออก
    - ถ้าตาราง leave_types ยังไม่มีคอลัมน์ accrue_per_year/max_quota → fallback base อย่างเดียว
    """
    base = float(getattr(leave_type, "annual_quota", 0.0) or 0.0)

    # ไม่มีคอลัมน์ใหม่ -> คืน base
    if not hasattr(leave_type, "accrue_per_year") or not hasattr(leave_type, "max_quota"):
        return base

    if not _is_annual_leave(leave_type):
        return base

    inc = float(getattr(leave_type, "accrue_per_year", 0.0) or 0.0)
    cap = float(getattr(leave_type, "max_quota", 0.0) or 0.0)

    as_of = date(year, 1, 1)
    years_completed = _full_years_completed(getattr(employee, "hire_date", None), as_of)

    opening = base + years_completed * inc
    if cap and cap > 0:
        opening = min(opening, cap)
    return float(max(0.0, opening))

def _years_of_service(emp: Employee, year: int) -> int:
    """
    นับจำนวน 'ปีที่ครบแล้ว' ณ ต้นปีนั้น เช่น เข้างาน 2023-06-10
    - ปี 2023 => 0 (ยังไม่ครบปี)
    - ปี 2024 => 0 หรือ 1 แล้วแต่นโยบาย (ตรงนี้เอาแบบ conservative: ครบเมื่อถึงวันครบรอบ)
    - เพื่อความง่าย: ใช้ความต่างปีแบบ floor ตามวันครบรอบ
    """
    if not getattr(emp, "hire_date", None):
        return 0
    hd: date = emp.hire_date if isinstance(emp.hire_date, date) else emp.hire_date.date()
    asof = date(year, 1, 1)
    yrs = (asof.year - hd.year) - (1 if (asof.month, asof.day) < (hd.month, hd.day) else 0)
    return max(0, yrs)

def seed_leave_balances(db: Session, year: int):
    """
    opening = min( annual_quota + years_of_service * accrue_per_year , max_quota(if >0) )
    ใช้เฉพาะ leave type ที่ affects_balance = True
    """
    employees = db.query(Employee).all()
    leave_types = db.query(models.LeaveType).filter(models.LeaveType.affects_balance == True).all()

    created = 0
    for emp in employees:
        yrs = _years_of_service(emp, year)
        for lt in leave_types:
            lb, is_new = get_or_create_leave_balance(db, emp.id, lt.id, year)

            # base
            base = float(getattr(lt, "annual_quota", 0.0) or 0.0)
            accrue = float(getattr(lt, "accrue_per_year", 0.0) or 0.0)
            cap = float(getattr(lt, "max_quota", 0.0) or 0.0)

            opening_val = base + yrs * accrue
            if cap > 0:
                opening_val = min(opening_val, cap)

            # เข้ากับ schema เก่า/ใหม่
            if hasattr(models.LeaveBalance, "opening"):
                lb.opening = float(opening_val)
            elif hasattr(models.LeaveBalance, "opening_quota"):
                lb.opening_quota = float(opening_val)

            if is_new:
                # กัน None
                for name in ("accrued", "used", "adjusted", "carry_in"):
                    if hasattr(lb, name) and getattr(lb, name) is None:
                        setattr(lb, name, 0.0)
                created += 1

    db.commit()
    return {"ok": True, "year": year, "created": created}

def list_leave_balances(db: Session, employee_id: int, year: int):
    """
    คืนรายการ leave balance เป็น dict ที่ front ใช้งานง่าย
    - ใส่ leave_type_name
    - opening ถ้าไม่มีให้ fallback ไป opening_quota หรือ 0.0
    - คำนวณ available ให้เสร็จ
    """
    rows = (
        db.query(models.LeaveBalance, models.LeaveType)
          .join(models.LeaveType, models.LeaveType.id == models.LeaveBalance.leave_type_id)
          .filter(models.LeaveBalance.employee_id == employee_id,
                  models.LeaveBalance.year == year)
          .order_by(models.LeaveType.name.asc())
          .all()
    )

    result = []
    for lb, lt in rows:
        opening = getattr(lb, "opening", None)
        if opening is None and hasattr(lb, "opening_quota"):
            opening = getattr(lb, "opening_quota", 0.0)

        accrued  = float(getattr(lb, "accrued", 0.0)   or 0.0)
        used     = float(getattr(lb, "used", 0.0)      or 0.0)
        adjusted = float(getattr(lb, "adjusted", 0.0)  or 0.0)
        carry_in = float(getattr(lb, "carry_in", 0.0)  or 0.0)
        opening  = float(opening or 0.0)

        try:
            available = float(getattr(lb, "available"))
        except Exception:
            available = opening + accrued + carry_in + adjusted - used

        result.append({
            "id": lb.id,
            "employee_id": lb.employee_id,
            "leave_type_id": lb.leave_type_id,
            "leave_type_name": lt.name or "",
            "year": lb.year,
            "opening": opening,
            "accrued": accrued,
            "used": used,
            "adjusted": adjusted,
            "carry_in": carry_in,
            "available": float(available),
        })

    return result

def get_leave_balances(db: Session, employee_id: int, year: int) -> list[LeaveBalance]:
    return (
        db.query(LeaveBalance)
        .filter(LeaveBalance.employee_id == employee_id, LeaveBalance.year == year)
        .all()
    )

def update_leave_balance(db: Session, balance_id: int, patch: schemas.LeaveBalanceUpdate):
    """
    รองรับ opening และ opening_quota (legacy) โดย map ให้ถูกคอลัมน์
    """
    lb = db.query(models.LeaveBalance).filter(models.LeaveBalance.id == balance_id).first()
    if not lb:
        return None
    data = patch.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "opening_quota":
            if hasattr(models.LeaveBalance, "opening"):
                lb.opening = float(v or 0)
            elif hasattr(models.LeaveBalance, "opening_quota"):
                lb.opening_quota = float(v or 0)
        else:
            setattr(lb, k, float(v or 0))
    db.commit()
    db.refresh(lb)
    return lb

def adjust_leave_balance(
    db: Session, employee_id: int, leave_type_id: int, year: int, delta: float
) -> LeaveBalance:
    lb, _ = get_or_create_leave_balance(db, employee_id, leave_type_id, year)
    if hasattr(models.LeaveBalance, "adjusted"):
        lb.adjusted = float(getattr(lb, "adjusted", 0.0) or 0.0) + float(delta or 0.0)
        db.commit()
        db.refresh(lb)
    return lb

def _should_affect_balance(db: Session, leave_type_id: int) -> bool:
    lt = db.query(LeaveType).get(leave_type_id)
    return bool(getattr(lt, "affects_balance", True)) if lt else False

def _split_across_years(start_d: date, end_d: date, total_days: float) -> list[tuple[int, float]]:
    """ง่ายที่สุด: ใส่ยอดทั้งหมดในปีเริ่มต้น (ต้องการละเอียดค่อยแตกช่วง)."""
    return [(start_d.year, total_days)]

def approve_leave_request(db: Session, request_id: int) -> LeaveRequest:
    req = (
        db.query(LeaveRequest)
        .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
        .filter(LeaveRequest.id == request_id)
        .first()
    )
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")

    if str(getattr(req, "status", "")).upper() == "APPROVED":
        return req

    if not _should_affect_balance(db, req.leave_type_id):
        req.status = LeaveStatus.APPROVED
        db.commit()
        db.refresh(req)
        return req

    days = _days_between_std(req.start_date, req.end_date)
    chunks = _split_across_years(req.start_date.date(), req.end_date.date(), days)

    # ตรวจสิทธิ์
    for (yy, d) in chunks:
        lb, _ = get_or_create_leave_balance(db, req.employee_id, req.leave_type_id, yy)
        avail = lb.available if hasattr(lb, "available") else (
            float(getattr(lb, "opening", 0.0)) + float(getattr(lb, "accrued", 0.0))
            + float(getattr(lb, "carry_in", 0.0)) + float(getattr(lb, "adjusted", 0.0))
            - float(getattr(lb, "used", 0.0))
        )
        if avail < d:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient leave balance for year {yy}: need {d} days, available {avail:.2f}",
            )

    # หักยอด
    for (yy, d) in chunks:
        lb, _ = get_or_create_leave_balance(db, req.employee_id, req.leave_type_id, yy)
        lb.used = float(getattr(lb, "used", 0.0) or 0.0) + float(d)
        db.add(lb)

    req.status = LeaveStatus.APPROVED
    db.commit()
    db.refresh(req)
    return req

def reject_leave_request(db: Session, request_id: int, reason: Optional[str] = None) -> LeaveRequest:
    req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    req.status = LeaveStatus.REJECTED
    if hasattr(req, "note") and reason:
        req.note = reason
    db.commit()
    db.refresh(req)
    return req

def _ensure_enough_balance(
    db: Session, employee_id: int, leave_type_id: int, start_dt: datetime, end_dt: datetime
):
    """
    ใช้ตอนสร้าง/แก้ไขคำขอที่ตั้ง Approved ตั้งแต่แรก ให้เช็คสิทธิ์ก่อน
    """
    lt = db.query(models.LeaveType).get(leave_type_id)
    if not lt or not bool(getattr(lt, "affects_balance", True)):
        return

    quota = float(getattr(lt, "annual_quota", 0.0) or 0.0)
    if quota == 0.0:
        return  # ไม่จำกัดโควต้า

    y = start_dt.year
    lb, _ = get_or_create_leave_balance(db, employee_id, leave_type_id, y)
    need = _days_between_std(start_dt, end_dt)

    # ถ้ามี property available ใช้เลย, ไม่งั้นคำนวณคร่าวจาก quota-used
    avail = getattr(lb, "available", None)
    if avail is None:
        avail = quota - float(getattr(lb, "used", 0.0) or 0.0)

    if float(avail) < need:
        raise HTTPException(
            status_code=409, detail=f"สิทธิ์ไม่พอ ต้องใช้ {need:.2f} วัน เหลือ {float(avail):.2f} วัน"
        )

def _apply_usage(
    db: Session, employee_id: int, leave_type_id: int, start_dt: datetime, end_dt: datetime, sign: int
):
    """
    sign = +1 เมื่อตั้ง Approved → เพิ่ม used
    sign = -1 เมื่อเปลี่ยนจาก Approved → คืน used
    """
    lt = db.query(models.LeaveType).get(leave_type_id)
    if not lt or not bool(getattr(lt, "affects_balance", True)):
        return
    y = start_dt.year
    lb, _ = get_or_create_leave_balance(db, employee_id, leave_type_id, y)
    inc = _days_between_std(start_dt, end_dt) * (1 if sign >= 0 else -1)
    lb.used = max(0.0, float(getattr(lb, "used", 0.0) or 0.0) + inc)
    db.commit()
    db.refresh(lb)

def get_leave_balance_year(
    db: Session, employee_id: int, leave_type_id: int, year: int, include_pending: bool = True
) -> dict:
    """
    สรุป balance จาก LeaveRequest (Approved/Pending) ตามปี (อิง quota จาก LeaveType.annual_quota)
    """
    lt = db.query(LeaveType).filter(LeaveType.id == leave_type_id).first()
    if not lt:
        return {
            "quota": 0.0,
            "used_approved": 0.0,
            "used_pending": 0.0,
            "available": 0.0,
            "affects_balance": True,
        }

    quota = float(getattr(lt, "annual_quota", 0.0) or 0.0)
    affects = bool(getattr(lt, "affects_balance", True))

    y_start = datetime(year, 1, 1)
    y_end = datetime(year, 12, 31, 23, 59, 59)

    q = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.leave_type_id == leave_type_id,
        LeaveRequest.start_date <= y_end,
        LeaveRequest.end_date >= y_start,
    )
    rows = q.all()

    used_appr = 0.0
    used_pend = 0.0
    for r in rows:
        s = max(r.start_date, y_start)
        e = min(r.end_date, y_end)
        if e <= s:
            continue
        d = _days_between_std(s, e)
        st = str(getattr(r, "status", "")).upper()
        if st == "APPROVED":
            used_appr += d
        elif include_pending and st == "PENDING":
            used_pend += d

    available = quota - used_appr if quota > 0 else float("inf")
    return {
        "quota": quota,
        "used_approved": round(used_appr, 4),
        "used_pending": round(used_pend, 4),
        "available": round(available if available != float("inf") else 999999, 4),
        "affects_balance": affects,
    }

# =====================================================================
# Time entries (Report / Import)
# =====================================================================

def get_time_entries_report(
    db: Session,
    employee_id_number: Optional[str] = None,
    entry_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(models.TimeEntry).options(joinedload(models.TimeEntry.employee))
    if employee_id_number:
        q = (
            q.join(Employee, models.TimeEntry.employee_id == Employee.id)
            .filter(Employee.employee_id_number.ilike(f"%{employee_id_number}%"))
        )
    if entry_date:
        q = q.filter(func.date(models.TimeEntry.check_in_time) == entry_date)
    return q.order_by(models.TimeEntry.check_in_time.desc()).offset(skip).limit(limit).all()

def get_time_entries_report_range(
    db: Session,
    employee_id_number: Optional[str],
    date_from: date,
    date_to: date,
    skip: int = 0,
    limit: int = 100,
):
    q = db.query(models.TimeEntry).options(joinedload(models.TimeEntry.employee))
    if employee_id_number:
        q = (
            q.join(Employee, models.TimeEntry.employee_id == Employee.id)
            .filter(Employee.employee_id_number.ilike(f"%{employee_id_number}%"))
        )

    start_dt = datetime.combine(date_from, time.min)
    end_dt = datetime.combine(date_to, time.max)

    q = q.filter(
        or_(
            models.TimeEntry.check_in_time.between(start_dt, end_dt),
            models.TimeEntry.check_out_time.between(start_dt, end_dt),
            (models.TimeEntry.check_in_time <= end_dt)
            & (func.coalesce(models.TimeEntry.check_out_time, models.TimeEntry.check_in_time) >= start_dt),
        )
    )
    return q.order_by(models.TimeEntry.check_in_time.desc()).offset(skip).limit(limit).all()

def import_time_entries_from_csv_or_excel(db: Session, df: pd.DataFrame) -> int:
    created = updated = 0
    df.columns = df.columns.str.strip()
    req = ["Employee ID", "Time"]
    if not all(c in df.columns for c in req):
        missing = [c for c in req if c not in df.columns]
        raise KeyError(f"Missing required columns: {', '.join(missing)}")

    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df.dropna(subset=["Time"], inplace=True)
    grouped = df.groupby([df["Employee ID"], df["Time"].dt.date])

    for (emp_code, d), day_df in grouped:
        emp = db.query(Employee).filter(Employee.employee_id_number == str(emp_code)).first()
        if not emp:
            continue

        ci = day_df["Time"].min()
        co = day_df["Time"].max()
        if len(day_df) < 2:
            co = None

        exist = (
            db.query(models.TimeEntry)
            .filter(models.TimeEntry.employee_id == emp.id, func.date(models.TimeEntry.check_in_time) == d)
            .first()
        )
        if exist:
            exist.check_in_time = ci
            exist.check_out_time = co
            db.add(exist)
            updated += 1
        else:
            db.add(
                models.TimeEntry(
                    employee_id=emp.id,
                    check_in_time=ci,
                    check_out_time=co,
                    status=models.TimeEntryStatus.APPROVED,
                )
            )
            created += 1
    db.commit()
    return created + updated

# =====================================================================
# Holidays CRUD
# =====================================================================
def _holiday_date_col():
    for c in ("date", "holiday_date", "day", "start_date"):
        if hasattr(models.Holiday, c):
            return getattr(models.Holiday, c)
    return getattr(models.Holiday, "id")  # fallback

def _is_holiday(db: Session, day: date) -> bool:
    col = _holiday_date_col()
    # ถ้าเป็นคอลัมน์ datetime ให้เทียบเฉพาะวัน
    # ใช้ func.date เพื่อความกว้าง (บาง DB)
    try:
        return db.query(models.Holiday).filter(func.date(col) == day).first() is not None
    except Exception:
        # fallback เทียบตรง ๆ
        return db.query(models.Holiday).filter(col == day).first() is not None

# def _holiday_date_col():
#     """
#     คืนคอลัมน์วันที่ที่มีอยู่จริงใน models.Holiday หนึ่งตัว
#     รองรับหลายชื่อสคีมา: date, holiday_date, day, start_date
#     """
#     cand = ("date", "holiday_date", "day", "start_date")
#     for c in cand:
#         if hasattr(models.Holiday, c):
#             return getattr(models.Holiday, c)
#     # ถ้าไม่พบจริง ๆ ก็ย้อนกลับไปใช้ id เพื่อกัน error
#     return getattr(models.Holiday, "id")

def _classify_attendance_for_day(db: Session, employee_id: int, day: date) -> Optional[dict]:
    # 1) ถ้าเป็นวันลา (อนุมัติ) -> คืนสถานะลา (เหมือนเดิม)
    lr = (
        db.query(models.LeaveRequest)
        .filter(models.LeaveRequest.employee_id == employee_id)
        .filter(models.LeaveRequest.status == models.LeaveStatus.APPROVED)
        .filter(models.LeaveRequest.start_date <= day)
        .filter(models.LeaveRequest.end_date >= day)
        .first()
    )
    if lr:
        ...
        return dict(...)

    # 2) ถ้าเป็น "วันหยุด" -> ข้ามไม่สร้างแถว (แสดงว่างในหน้า)
    if _is_holiday(db, day):
        return None  # ไม่ถือเป็นขาดงาน/ลา

    # 3) ทำงานต่อด้วย schedule ตามปกติ
    sch = _get_schedule_for_day(db, employee_id, day)
    if not sch:
        return None
    policy = _policy_from_schedule(sch)
    if not policy["is_workday"]:
        return None

def create_holiday(db: Session, holiday: schemas.HolidayCreate):
    obj = models.Holiday(**holiday.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_holidays(db: Session, skip: int = 0, limit: int = 100):
    # เรียงตามคอลัมน์วันที่ที่หาได้ ถ้าไม่มีใช้ id
    date_col = _holiday_date_col()
    return (
        db.query(models.Holiday)
        .order_by(date_col.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_holiday(db: Session, holiday_id: int):
    return db.query(models.Holiday).filter(models.Holiday.id == holiday_id).first()

def update_holiday(db: Session, holiday_id: int, holiday_update: schemas.HolidayUpdate):
    obj = get_holiday(db, holiday_id)
    if not obj:
        return None
    for k, v in holiday_update.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_holiday(db: Session, holiday_id: int):
    obj = get_holiday(db, holiday_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return {"message": "วันหยุดถูกลบแล้ว"}

# =====================================================================
# Daily report (Time + Leaves + OT)
# =====================================================================

def _dr_daterange(d1: date, d2: date) -> Iterable[date]:
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)

def _dr_overlap_minutes(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> int:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    return max(0, int((end - start).total_seconds() // 60))

def _dr_day_segments(db: Session, emp_id: int, d: date) -> List[Tuple[time, time]]:
    """
    คืนช่วงเวลาทำงานของวันนั้นแบบยืดหยุ่น:
    - ถ้า WorkingSchedule มี break ให้แตกเป็น 2 ช่วง (ก่อนพัก/หลังพัก)
    - ถ้าเป็นวันหยุด/ไม่ใช่วันทำงาน => []
    """
    sch = _get_schedule_for_day(db, emp_id, d)
    if not sch:
        return []
    pol = _policy_from_schedule(sch)
    if not pol["is_workday"]:
        return []

    start_t: time = pol["start_time"]
    end_t: time = pol["end_time"]
    segs: List[Tuple[time, time]] = []

    # ถ้ามี break_start/break_end ใน schedule ให้แยกเป็น 2 ช่วง
    bst = getattr(sch, "break_start_time", None)
    bet = getattr(sch, "break_end_time", None)
    if bst and bet and bst < bet:
        if start_t < bst:
            segs.append((start_t, bst))
        if bet < end_t:
            segs.append((bet, end_t))
    else:
        segs.append((start_t, end_t))

    return segs

def _dr_work_minutes(segs: List[Tuple[time, time]]) -> int:
    tot = 0
    for s, e in segs:
        tot += int((datetime.combine(date(2000,1,1), e) - datetime.combine(date(2000,1,1), s)).total_seconds() // 60)
    return tot

def _dr_leave_fraction_on_day(leave_start: datetime, leave_end: datetime, d: date, segs: List[Tuple[time, time]]) -> Optional[float]:
    """ส่วนของวันลาในวัน d (0..1); ถ้าไม่ใช่วันทำงานให้คืน None"""
    if not segs:
        return None
    total = _dr_work_minutes(segs)
    if total <= 0:
        return None
    used = 0
    for s, e in segs:
        used += _dr_overlap_minutes(leave_start, leave_end, datetime.combine(d, s), datetime.combine(d, e))
    used = min(used, total)
    return round(used / total, 4)

def build_daily_report(
    db: Session,
    date_from: date,
    date_to: date,
    employee_id_number: Optional[str] = None,
    include_leaves: bool = True,
    include_ot: bool = True,
) -> List[dict]:
    # master
    lt_list = db.query(LeaveType).all()
    ot_list = db.query(models.OvertimeType).all() if hasattr(models, "OvertimeType") else []
    lt_id2name = {x.id: x.name for x in lt_list}
    ot_id2name = {x.id: x.name for x in ot_list}

    # employees
    emp_q = db.query(Employee)
    if employee_id_number:
        emp_q = emp_q.filter(Employee.employee_id_number == employee_id_number)
    emps = emp_q.all()
    emp_by_id = {e.id: e for e in emps}

    # time entries (ครอบคลุมช่วง)
    start_dt = datetime.combine(date_from, time.min)
    end_dt   = datetime.combine(date_to,   time.max)

    te_q = (
        db.query(models.TimeEntry)
        .filter(
            or_(
                models.TimeEntry.check_in_time.between(start_dt, end_dt),
                models.TimeEntry.check_out_time.between(start_dt, end_dt),
                (models.TimeEntry.check_in_time <= end_dt) &
                (func.coalesce(models.TimeEntry.check_out_time, models.TimeEntry.check_in_time) >= start_dt)
            )
        )
    )
    if employee_id_number:
        te_q = (
            te_q.join(Employee, models.TimeEntry.employee_id == Employee.id)
                .filter(Employee.employee_id_number == employee_id_number)
        )
    time_entries = te_q.all()

    # โครงข้อมูลผลลัพธ์
    report: Dict[Tuple[int, date], dict] = {}

    def ensure_row(emp_id: int, d: date) -> dict:
        key = (emp_id, d)
        if key not in report:
            emp = emp_by_id.get(emp_id)
            full_name = (f"{getattr(emp,'first_name','') or ''} {getattr(emp,'last_name','') or ''}").strip() if emp else ""
            report[key] = {
                "employee_id": emp_id,
                "employee_id_number": getattr(emp, "employee_id_number", None),
                "full_name": full_name,
                "date": d.isoformat(),
                "check_in_time": None,
                "check_out_time": None,
                "late_minutes": 0,
                "early_leave_minutes": 0,
                "is_workday": False,
                "leaves": defaultdict(float),   # name -> days
                "ot_hours": defaultdict(float), # name -> hours
            }
        return report[key]

    # เติมข้อมูลเวลาเข้าออก + สาย/ออกก่อน
    for te in time_entries:
        d = (te.check_in_time or te.check_out_time).date()
        if d < date_from or d > date_to:
            continue
        row = ensure_row(te.employee_id, d)

        segs = _dr_day_segments(db, te.employee_id, d)
        row["is_workday"] = bool(segs)
        row["check_in_time"]  = te.check_in_time.isoformat() if te.check_in_time else None
        row["check_out_time"] = te.check_out_time.isoformat() if te.check_out_time else None

        if segs:
            # ใช้ช่วงแรก/สุดท้ายเป็นเกณฑ์
            day_start = datetime.combine(d, segs[0][0])
            day_end   = datetime.combine(d, segs[-1][1])
            if te.check_in_time:
                late_raw = max(0, int((te.check_in_time - day_start).total_seconds() // 60))
                row["late_minutes"] = max(0, late_raw - DEF_LATE_GRACE_MIN)
            if te.check_out_time:
                early_raw = max(0, int((day_end - te.check_out_time).total_seconds() // 60))
                row["early_leave_minutes"] = max(0, early_raw - DEF_EARLY_LEAVE_GRACE_MIN)

    # Leaves (Approved) → แจกตามวัน/ส่วนของวัน
    if include_leaves:
        # รองรับ enum/สตริง
        LS = LeaveStatus
        approved_leave_vals = [getattr(LS, "APPROVED", None)]
        approved_leave_vals = [v for v in approved_leave_vals if v is not None]
        approved_leave_vals += ["APPROVED", "Approved", "อนุมัติ"]

        lr_q = (
            db.query(LeaveRequest)
            .filter(
                LeaveRequest.status.in_(approved_leave_vals),
                LeaveRequest.start_date <= end_dt,
                LeaveRequest.end_date >= start_dt,
            )
        )
        if employee_id_number:
            lr_q = (
                lr_q.join(Employee, LeaveRequest.employee_id == Employee.id)
                    .filter(Employee.employee_id_number == employee_id_number)
            )

        for lr in lr_q.all():
            s = max(lr.start_date, start_dt)
            e = min(lr.end_date,   end_dt)
            for d in _dr_daterange(s.date(), e.date()):
                segs = _dr_day_segments(db, lr.employee_id, d)
                frac = _dr_leave_fraction_on_day(s, e, d, segs)
                if not frac:
                    continue
                row = ensure_row(lr.employee_id, d)
                row["is_workday"] = row["is_workday"] or bool(segs)
                lt_name = lt_id2name.get(lr.leave_type_id, f"Leave#{lr.leave_type_id}")
                row["leaves"][lt_name] += float(frac)

    # OT (Approved only) → รวมเป็นชั่วโมงตามประเภท
    if include_ot and hasattr(models, "OvertimeRequest"):
        OS = getattr(models, "OvertimeStatus", None)
        approved_ot_vals = []
        if OS and hasattr(OS, "APPROVED"):
            approved_ot_vals.append(OS.APPROVED)
        approved_ot_vals += ["APPROVED", "Approved", "อนุมัติ"]

        ot_q = (
            db.query(models.OvertimeRequest)
            .filter(
                models.OvertimeRequest.status.in_(approved_ot_vals),
                models.OvertimeRequest.start_time <= end_dt,
                models.OvertimeRequest.end_time >= start_dt,
            )
        )
        if employee_id_number:
            ot_q = (
                ot_q.join(Employee, models.OvertimeRequest.employee_id == Employee.id)
                    .filter(Employee.employee_id_number == employee_id_number)
            )

        for req in ot_q.all():
            # เฉลี่ยลง “วันของช่วงที่ทับกับหน้ารายงาน” แบบง่าย: ลงวันที่เริ่มทับ
            s_clip = max(req.start_time, start_dt)
            e_clip = min(req.end_time,   end_dt)
            if e_clip <= s_clip:
                continue
            d = s_clip.date()
            hrs = (e_clip - s_clip).total_seconds() / 3600.0
            if hrs <= 0:
                continue
            row = ensure_row(req.employee_id, d)
            name = ot_id2name.get(getattr(req, "ot_type_id", None), "OT")
            row["ot_hours"][name] += round(hrs, 2)

    # ปิด defaultdict
    out = []
    for r in report.values():
        r["leaves"] = dict(r["leaves"])
        r["ot_hours"] = dict(r["ot_hours"])
        out.append(r)

    out.sort(key=lambda x: (x["employee_id"], x["date"]))
    return out

# =====================================================================
# Working Schedule CRUD
# =====================================================================

def create_working_schedule(db: Session, schedule: schemas.WorkingScheduleCreate):
    obj = models.WorkingSchedule(**schedule.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_working_schedule(db: Session, schedule_id: int):
    return db.query(models.WorkingSchedule).filter(models.WorkingSchedule.id == schedule_id).first()

def get_working_schedules(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.WorkingSchedule).offset(skip).limit(limit).all()

def update_working_schedule(db: Session, schedule_id: int, schedule_update: schemas.WorkingScheduleUpdate):
    obj = get_working_schedule(db, schedule_id)
    if not obj:
        return None
    for k, v in schedule_update.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_working_schedule(db: Session, schedule_id: int):
    obj = get_working_schedule(db, schedule_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return {"message": "ตารางเวลาทำงานถูกลบแล้ว"}

# =====================================================================
# Time Entry CRUD
# =====================================================================

def create_time_entry(db: Session, time_entry: schemas.TimeEntryCreate):
    obj = models.TimeEntry(**time_entry.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_time_entry(db: Session, entry_id: int):
    return (
        db.query(models.TimeEntry)
        .options(joinedload(models.TimeEntry.employee))
        .filter(models.TimeEntry.id == entry_id)
        .first()
    )

def get_time_entries(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.TimeEntry)
        .options(joinedload(models.TimeEntry.employee))
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_time_entry(db: Session, entry_id: int, time_entry_update: schemas.TimeEntryUpdate):
    obj = get_time_entry(db, entry_id)
    if not obj:
        return None
    for k, v in time_entry_update.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_time_entry(db: Session, entry_id: int):
    obj = get_time_entry(db, entry_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return {"message": "บันทึกเวลาถูกลบแล้ว"}

# =====================================================================
# Leave Types CRUD
# =====================================================================

def create_leave_type(db: Session, leave_type: schemas.LeaveTypeCreate):
    obj = models.LeaveType(**leave_type.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_leave_type(db: Session, leave_type_id: int):
    return db.query(models.LeaveType).filter(models.LeaveType.id == leave_type_id).first()

def get_leave_types(db: Session, skip=0, limit=100, affects_balance: bool | None = None):
    q = db.query(models.LeaveType)
    if affects_balance is not None:
        q = q.filter(models.LeaveType.affects_balance == affects_balance)
    return q.offset(skip).limit(limit).all()

def update_leave_type(db: Session, leave_type_id: int, leave_type_update: schemas.LeaveTypeUpdate):
    obj = get_leave_type(db, leave_type_id)
    if not obj:
        return None
    for k, v in leave_type_update.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_leave_type(db: Session, leave_type_id: int):
    obj = get_leave_type(db, leave_type_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return {"message": "ประเภทการลาถูกลบแล้ว"}

# =====================================================================
# Leave Requests CRUD (+ overlap)
# =====================================================================

def check_for_overlapping_leave(
    db: Session,
    employee_id: int,
    start_date: datetime,
    end_date: datetime,
    existing_request_id: Optional[int] = None,
):
    q = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee_id,
        models.LeaveRequest.status.in_([models.LeaveStatus.PENDING, models.LeaveStatus.APPROVED]),
        models.LeaveRequest.start_date < end_date,
        models.LeaveRequest.end_date > start_date,
    )
    if existing_request_id:
        q = q.filter(models.LeaveRequest.id != existing_request_id)
    overlap = q.first()
    if overlap:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An overlapping leave request (ID: {overlap.id}) already exists for this period.",
        )

def create_leave_request(db: Session, leave_request: schemas.LeaveRequestCreate):
    check_for_overlapping_leave(
        db, leave_request.employee_id, leave_request.start_date, leave_request.end_date
    )

    if str(getattr(leave_request, "status", "Pending")).lower() == "approved":
        _ensure_enough_balance(
            db,
            leave_request.employee_id,
            leave_request.leave_type_id,
            leave_request.start_date,
            leave_request.end_date,
        )

    obj = models.LeaveRequest(**leave_request.model_dump(), request_date=datetime.utcnow())
    db.add(obj)
    db.commit()
    db.refresh(obj)

    if str(obj.status).lower() == "approved":
        _apply_usage(db, obj.employee_id, obj.leave_type_id, obj.start_date, obj.end_date, +1)
    return obj

def get_leave_request(db: Session, request_id: int):
    obj = (
        db.query(models.LeaveRequest)
        .options(joinedload(models.LeaveRequest.employee), joinedload(models.LeaveRequest.leave_type))
        .filter(models.LeaveRequest.id == request_id)
        .first()
    )
    if obj:
        delta = obj.end_date - obj.start_date
        obj.num_days = delta.total_seconds() / (8 * 3600)
    return obj

def get_leave_requests(db: Session, skip: int = 0, limit: int = 100):
    rows = (
        db.query(models.LeaveRequest)
        .options(joinedload(models.LeaveRequest.employee), joinedload(models.LeaveRequest.leave_type))
        .offset(skip)
        .limit(limit)
        .all()
    )
    for r in rows:
        delta = r.end_date - r.start_date
        r.num_days = delta.total_seconds() / (8 * 3600)
    return rows

def update_leave_request(db: Session, request_id: int, leave_request_update: schemas.LeaveRequestUpdate):
    obj = db.query(models.LeaveRequest).filter(models.LeaveRequest.id == request_id).first()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")

    old_status = str(obj.status).lower()
    old_start, old_end = obj.start_date, obj.end_date
    old_type, old_emp = obj.leave_type_id, obj.employee_id

    data = leave_request_update.model_dump(exclude_unset=True)

    check_for_overlapping_leave(
        db,
        data.get("employee_id", obj.employee_id),
        data.get("start_date", obj.start_date),
        data.get("end_date", obj.end_date),
        existing_request_id=request_id,
    )

    new_status = str(data.get("status", obj.status)).lower()
    new_start = data.get("start_date", obj.start_date)
    new_end = data.get("end_date", obj.end_date)
    new_type = data.get("leave_type_id", obj.leave_type_id)
    new_emp = data.get("employee_id", obj.employee_id)

    if new_status == "approved":
        _ensure_enough_balance(db, new_emp, new_type, new_start, new_end)

    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)

    cur_status = str(obj.status).lower()

    if old_status == "approved" and cur_status != "approved":
        _apply_usage(db, old_emp, old_type, old_start, old_end, -1)

    if old_status != "approved" and cur_status == "approved":
        _apply_usage(db, obj.employee_id, obj.leave_type_id, obj.start_date, obj.end_date, +1)

    if old_status == "approved" and cur_status == "approved":
        if (old_start, old_end, old_type, old_emp) != (
            obj.start_date,
            obj.end_date,
            obj.leave_type_id,
            obj.employee_id,
        ):
            _apply_usage(db, old_emp, old_type, old_start, old_end, -1)
            _ensure_enough_balance(db, obj.employee_id, obj.leave_type_id, obj.start_date, obj.end_date)
            _apply_usage(db, obj.employee_id, obj.leave_type_id, obj.start_date, obj.end_date, +1)

    delta = obj.end_date - obj.start_date
    obj.num_days = delta.total_seconds() / (8 * 3600)
    return obj

def delete_leave_request(db: Session, request_id: int):
    obj = get_leave_request(db, request_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return {"message": "คำขอลาถูกลบแล้ว"}

# =====================================================================
# Attendance compute (daily classify + rebuild + metrics)
# =====================================================================

def _minutes_between(a: Optional[datetime], b: Optional[datetime]) -> int:
    if not a or not b:
        return 0
    return max(0, int((b - a).total_seconds() // 60))

def _calc_break_minutes(ws) -> int:
    if getattr(ws, "break_minutes_override", None) is not None:
        return int(ws.break_minutes_override or 0)
    bst = getattr(ws, "break_start_time", None)
    bet = getattr(ws, "break_end_time", None)
    if bst and bet:
        dummy = datetime(2000, 1, 1)
        return _minutes_between(datetime.combine(dummy, bst), datetime.combine(dummy, bet))
    return 0

def _get_schedule_for_day(db: Session, employee_id: int, day: date):
    wd_idx = day.weekday()
    idx_to_enum = {
        0: DayOfWeek.MONDAY,
        1: DayOfWeek.TUESDAY,
        2: DayOfWeek.WEDNESDAY,
        3: DayOfWeek.THURSDAY,
        4: DayOfWeek.FRIDAY,
        5: DayOfWeek.SATURDAY,
        6: DayOfWeek.SUNDAY,
    }
    dow = idx_to_enum[wd_idx]

    base_q = (
        db.query(models.WorkingSchedule)
        .filter(models.WorkingSchedule.day_of_week == dow)
        .filter(models.WorkingSchedule.is_active == True)
    )
    sch = (
        base_q.filter(models.WorkingSchedule.employee_id == employee_id)
        .order_by(models.WorkingSchedule.is_default.desc(), models.WorkingSchedule.id.asc())
        .first()
    )
    if sch:
        return sch
    return (
        base_q.filter(models.WorkingSchedule.employee_id.is_(None))
        .order_by(models.WorkingSchedule.is_default.desc(), models.WorkingSchedule.id.asc())
        .first()
    )

def _policy_from_schedule(sch) -> dict:
    late_grace = getattr(sch, "late_grace_min", None)
    early_grace = getattr(sch, "early_leave_grace_min", None) or getattr(sch, "early_grace_min", None)
    absence_after = getattr(sch, "absence_after_min", None)
    std_minutes = getattr(sch, "standard_daily_minutes", None)
    break_min = _calc_break_minutes(sch)
    is_working = getattr(sch, "is_working_day", True)
    start_t = getattr(sch, "start_time", None) or DEF_START_TIME
    end_t = getattr(sch, "end_time", None) or DEF_END_TIME
    return {
        "start_time": start_t,
        "end_time": end_t,
        "late_grace_min": late_grace if isinstance(late_grace, int) else DEF_LATE_GRACE_MIN,
        "early_leave_grace_min": early_grace if isinstance(early_grace, int) else DEF_EARLY_LEAVE_GRACE_MIN,
        "absence_after_min": absence_after if isinstance(absence_after, int) else DEF_ABSENCE_AFTER_MIN,
        "standard_daily_minutes": std_minutes if isinstance(std_minutes, int) else DEF_STD_DAILY_MINUTES,
        "break_minutes": break_min,
        "is_workday": bool(is_working),
    }

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
        # วันลาไม่คิด OT
        is_paid = True
        try:
            lt = db.query(models.LeaveType).get(lr.leave_type_id)
            if hasattr(lt, "is_paid_leave"):
                is_paid = bool(lt.is_paid_leave)
            elif hasattr(lt, "is_paid"):
                is_paid = bool(lt.is_paid)
        except Exception:
            pass
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
        return None
    policy = _policy_from_schedule(sch)
    if not policy["is_workday"]:
        return None

    # time entry ของวันนั้น
    day_start = datetime.combine(day, time(0, 0, 0))
    day_end = day_start + timedelta(days=1)
    te = (
        db.query(models.TimeEntry)
        .filter(models.TimeEntry.employee_id == employee_id)
        .filter(models.TimeEntry.check_in_time >= day_start)
        .filter(models.TimeEntry.check_in_time < day_end)
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
    end_dt = datetime.combine(day, policy["end_time"])
    ci = te.check_in_time or start_dt
    co = te.check_out_time or ci
    if co < ci:
        co = ci

    raw_late = max(0, int((ci - start_dt).total_seconds() // 60))
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

    # OT วันทำงาน (นับเกินเวลาออก)
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
        ot_holiday_minutes=0,
    )

def rebuild_attendance_range(
    db: Session, start: date, end: date, employee_id: Optional[int] = None, debug: bool = True
):
    # ลบข้อมูลเดิมในช่วง
    q_del = db.query(AttendanceDaily).filter(AttendanceDaily.day >= start, AttendanceDaily.day <= end)
    if employee_id:
        q_del = q_del.filter(AttendanceDaily.employee_id == employee_id)
    q_del.delete(synchronize_session=False)

    # เลือกพนักงาน
    q_emp = db.query(Employee)
    if employee_id:
        q_emp = q_emp.filter(Employee.id == employee_id)
    employees = q_emp.all()

    cur = start
    while cur <= end:
        for emp in employees:
            res = _classify_attendance_for_day(db, emp.id, cur)

            if debug:
                if res:
                    print(
                        f"[ATT] emp={emp.id} day={cur} status={res.get('status_code')} "
                        f"work={res.get('work_minutes', 0)} late={res.get('late_minutes', 0)} "
                        f"early={res.get('early_leave_minutes', 0)}"
                    )
                else:
                    print(f"[ATT] emp={emp.id} day={cur} status=SKIP (no schedule / non-working day)")

            if not res:
                continue

            status_code = res.get("status_code", AttendanceStatus.PRESENT.value)
            work_minutes = int(res.get("work_minutes", 0) or 0)
            late_minutes = int(res.get("late_minutes", 0) or 0)
            early_leave_minutes = int(res.get("early_leave_minutes", 0) or 0)
            is_paid_leave = bool(res.get("is_paid_leave", True))
            ot_wd = int(res.get("ot_weekday_minutes", 0) or 0)
            ot_hol = int(res.get("ot_holiday_minutes", 0) or 0)

            if status_code == AttendanceStatus.ABSENCE.value:
                late_minutes = 0
                early_leave_minutes = 0
                ot_wd = 0
                ot_hol = 0

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

# ---- OT fallback helpers (ใช้ใน metrics) ----

def _get_break_override_minutes(db: Session, employee_id: int, weekday: int) -> int:
    """
    คืนค่านาทีพักจาก WorkingSchedule ของวันในสัปดาห์นั้น (0=Mon..6=Sun)
    เลือกของพนักงานก่อน ถ้าไม่มีใช้ template (employee_id is NULL)
    """
    try:
        WS = getattr(models, "WorkingSchedule")
    except Exception:
        return 0

    q = (
        db.query(WS)
        .filter(WS.is_active == True, WS.day_of_week == weekday)
        .filter(or_(WS.employee_id == employee_id, WS.employee_id == None))
        .order_by(WS.employee_id.desc())
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

# ---- Metrics ----

def get_attendance_metrics(db: Session, employee_id: int, start: date, end: date) -> dict:
    rows = (
        db.query(AttendanceDaily)
        .filter(
            AttendanceDaily.employee_id == employee_id,
            AttendanceDaily.day >= start,
            AttendanceDaily.day <= end,
        )
        .all()
    )

    late_minutes = sum((getattr(r, "late_minutes", 0) or 0) for r in rows)
    early_leave_minutes = (
        sum((getattr(r, "early_leave_minutes", 0) or 0) for r in rows)
        if "early_leave_minutes" in AttendanceDaily.__table__.c
        else 0
    )
    absent_days = sum(1 for r in rows if r.status_code == AttendanceStatus.ABSENCE.value)
    unpaid_leave_days = sum(
        1
        for r in rows
        if (r.status_code == AttendanceStatus.LEAVE.value and not bool(getattr(r, "is_paid_leave", False)))
    )
    work_minutes = (
        sum((getattr(r, "work_minutes", 0) or 0) for r in rows)
        if "work_minutes" in AttendanceDaily.__table__.c
        else 0
    )

    has_ot_wd = "ot_weekday_minutes" in AttendanceDaily.__table__.c
    has_ot_hol = "ot_holiday_minutes" in AttendanceDaily.__table__.c
    ot_weekday_minutes = sum((getattr(r, "ot_weekday_minutes", 0) or 0) for r in rows) if has_ot_wd else 0
    ot_holiday_minutes = sum((getattr(r, "ot_holiday_minutes", 0) or 0) for r in rows) if has_ot_hol else 0

    # Fallback โดยอ่านจาก OT Requests (ถ้าไม่มีคอลัมน์ OT หรือรวมแล้วยัง 0)
    wd1_min = 0
    wd15_min = 0
    hol3_min = 0

    if (not has_ot_wd and not has_ot_hol) or (ot_weekday_minutes + ot_holiday_minutes) == 0:
        OTRequest = getattr(models, "OvertimeRequest", None) or getattr(models, "OTRequest", None)
        OTType = getattr(models, "OvertimeType", None) or getattr(models, "OTType", None)

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
            p_end_dt = datetime.combine(end, time.max)

            q = (
                db.query(OTRequest, OTType)
                .join(OTType, OTType.id == OTRequest.ot_type_id)
                .filter(
                    OTRequest.employee_id == employee_id,
                    OTRequest.start_time <= p_end_dt,
                    OTRequest.end_time >= p_start_dt,
                )
            )
            for req, t in q.all():
                raw_status = getattr(req, "status", None)
                if not _is_approved(raw_status):
                    continue

                s = max(req.start_time, p_start_dt)
                e = min(req.end_time, p_end_dt)
                if e <= s:
                    continue

                mins = int((e - s).total_seconds() // 60)
                brk = _get_break_override_minutes(db, employee_id, s.weekday())
                eff_mins = max(0, mins - brk)

                mult = _extract_multiplier(t)

                if _is_holiday_type(t):
                    hol3_min += eff_mins
                elif mult >= 1.4:
                    wd15_min += eff_mins
                else:
                    wd1_min += eff_mins

            ot_weekday_minutes = wd15_min
            ot_holiday_minutes = hol3_min

    ot_total_minutes = (wd1_min + wd15_min + hol3_min) if (wd1_min or wd15_min or hol3_min) else (ot_weekday_minutes + ot_holiday_minutes)

    return {
        "late_minutes": late_minutes,
        "early_leave_minutes": early_leave_minutes,
        "absent_days": absent_days,
        "unpaid_leave_days": unpaid_leave_days,
        "work_minutes": work_minutes,
        # คีย์เดิม (ให้สูตรเดิมใช้ได้ต่อ)
        "ot_weekday_minutes": ot_weekday_minutes,  # 1.5x
        "ot_holiday_minutes": ot_holiday_minutes,  # 3x
        # คีย์ใหม่ (ถ้าอยากแยก)
        "ot1x_minutes": wd1_min,
        "ot15x_minutes": wd15_min,
        "ot3x_minutes": hol3_min,
        "ot_total_minutes": ot_total_minutes,
    }

# =====================================================================
# Overtime Types / Requests
# =====================================================================

def create_ot_type(db: Session, ot_type: schemas.OvertimeTypeCreate):
    obj = models.OvertimeType(**ot_type.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_ot_type(db: Session, ot_type_id: int):
    return db.query(models.OvertimeType).filter(models.OvertimeType.id == ot_type_id).first()

def get_ot_types(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.OvertimeType).offset(skip).limit(limit).all()

def update_ot_type(db: Session, ot_type_id: int, ot_type_update: schemas.OvertimeTypeUpdate):
    obj = get_ot_type(db, ot_type_id)
    if not obj:
        return None
    for k, v in ot_type_update.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_ot_type(db: Session, ot_type_id: int):
    obj = get_ot_type(db, ot_type_id)
    if not obj:
        return None
    if getattr(obj, "ot_requests", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete Overtime Type because it is currently in use by OT requests.",
        )
    db.delete(obj)
    db.commit()
    return {"message": "Overtime Type deleted successfully."}

def check_for_overlapping_ot(
    db: Session,
    employee_id: int,
    start_time: datetime,
    end_time: datetime,
    existing_request_id: Optional[int] = None,
):
    active_statuses = []
    if hasattr(models, "OvertimeStatus"):
        active_statuses += [models.OvertimeStatus.PENDING, models.OvertimeStatus.APPROVED]
    if hasattr(models, "LeaveStatus"):
        active_statuses += [models.LeaveStatus.PENDING, models.LeaveStatus.APPROVED]
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
            detail=f"An overlapping OT request (ID: {overlap.id}) already exists for this period.",
        )

def create_ot_request(db: Session, ot_request: schemas.OvertimeRequestCreate):
    check_for_overlapping_ot(db, ot_request.employee_id, ot_request.start_time, ot_request.end_time)
    obj = models.OvertimeRequest(**ot_request.model_dump(), request_date=datetime.utcnow())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_ot_request(db: Session, request_id: int):
    return (
        db.query(models.OvertimeRequest)
        .options(joinedload(models.OvertimeRequest.employee), joinedload(models.OvertimeRequest.ot_type))
        .filter(models.OvertimeRequest.id == request_id)
        .first()
    )

def get_ot_requests(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.OvertimeRequest)
        .options(joinedload(models.OvertimeRequest.employee), joinedload(models.OvertimeRequest.ot_type))
        .order_by(models.OvertimeRequest.request_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_ot_request(db: Session, request_id: int, ot_request_update: schemas.OvertimeRequestUpdate):
    obj = get_ot_request(db, request_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OT request not found")
    data = ot_request_update.model_dump(exclude_unset=True)
    check_for_overlapping_ot(
        db,
        data.get("employee_id", obj.employee_id),
        data.get("start_time", obj.start_time),
        data.get("end_time", obj.end_time),
        existing_request_id=request_id,
    )
    for k, v in data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_ot_request(db: Session, request_id: int):
    obj = get_ot_request(db, request_id)
    if not obj:
        return None
    db.delete(obj)
    db.commit()
    return {"message": "OT request deleted successfully."}

# =====================================================================
# Debug Helper
# =====================================================================

def debug_att_day(db: Session, employee_id: int, day: date):
    sch = _get_schedule_for_day(db, employee_id, day)
    print("=== DEBUG ATT ===")
    print("emp:", employee_id, "day:", day)
    if not sch:
        print("No schedule")
        return
    policy = _policy_from_schedule(sch)
    print("policy:", policy)

    start_of_day = datetime.combine(day, time.min)
    end_of_day = start_of_day + timedelta(days=1)
    te = (
        db.query(models.TimeEntry)
        .filter(models.TimeEntry.employee_id == employee_id)
        .filter(models.TimeEntry.check_in_time >= start_of_day)
        .filter(models.TimeEntry.check_in_time < end_of_day)
        .order_by(models.TimeEntry.check_in_time.asc())
        .first()
    )
    print("time entry:", getattr(te, "check_in_time", None), getattr(te, "check_out_time", None))
    if not te:
        print("=> ABSENCE (no TE)")
        return

    start_dt = datetime.combine(day, policy["start_time"])
    end_dt = datetime.combine(day, policy["end_time"])
    ci = te.check_in_time or start_dt
    co = te.check_out_time or ci
    raw_late = max(0, int((ci - start_dt).total_seconds() // 60))
    late_m = max(0, raw_late - policy["late_grace_min"])
    raw_early = max(0, int((end_dt - co).total_seconds() // 60))
    early_m = max(0, raw_early - policy["early_leave_grace_min"])
    work_m = max(0, int((co - ci).total_seconds() // 60) - int(policy["break_minutes"]))
    print(
        f"calc: start={start_dt.time()} end={end_dt.time()} "
        f"ci={ci.time()} co={co.time()} work={work_m} late={late_m} early={early_m}"
    )
    if work_m < int(policy["absence_after_min"]):
        print("=> ABSENCE (work_minutes below threshold)")
    else:
        print("=>", "LATE" if late_m > 0 else "PRESENT", "(early_leave:", early_m, ")")
