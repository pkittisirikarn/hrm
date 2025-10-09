# modules/time_tracking/schemas.py
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import date, time, datetime
from typing import Optional
from . import models
from .models import DayOfWeek

# --------- helpers: normalize day_of_week ----------
_EN_MAP = {
    "mon": "Monday", "monday": "Monday",
    "tue": "Tuesday", "tues": "Tuesday", "tuesday": "Tuesday",
    "wed": "Wednesday", "weds": "Wednesday", "wednesday": "Wednesday",
    "thu": "Thursday", "thur": "Thursday", "thurs": "Thursday", "thursday": "Thursday",
    "fri": "Friday", "friday": "Friday",
    "sat": "Saturday", "saturday": "Saturday",
    "sun": "Sunday", "sunday": "Sunday",
}

_TH_MAP = {
    "จันทร์": "Monday",
    "อังคาร": "Tuesday",
    "พุธ": "Wednesday",
    "พฤหัสบดี": "Thursday",
    "พฤหัส": "Thursday",
    "ศุกร์": "Friday",
    "เสาร์": "Saturday",
    "อาทิตย์": "Sunday",
    "วันจันทร์": "Monday",
    "วันอังคาร": "Tuesday",
    "วันพุธ": "Wednesday",
    "วันพฤหัสบดี": "Thursday",
    "วันพฤหัส": "Thursday",
    "วันศุกร์": "Friday",
    "วันเสาร์": "Saturday",
    "วันอาทิตย์": "Sunday",
}

def _coerce_day_of_week(value):
    """return models.DayOfWeek or raise ValueError"""
    if value is None:
        return value
    if isinstance(value, models.DayOfWeek):
        return value
    if isinstance(value, str):
        s = value.strip().replace(" ", "")
        if s.startswith("วัน") and s in _TH_MAP:
            s_norm = _TH_MAP[s]
        else:
            if s in _TH_MAP:
                s_norm = _TH_MAP[s]
            else:
                key = s.lower().replace(".", "")
                s_norm = _EN_MAP.get(key, s)
        for member in models.DayOfWeek:
            if member.value.lower() == s_norm.lower() or member.name.lower() == s_norm.lower():
                return member
    try:
        return models.DayOfWeek[str(value).upper()]
    except Exception:
        pass
    raise ValueError("Input should be a valid day of week")

# --- Working Schedule Schemas ---
class WorkingScheduleBase(BaseModel):
    # อนุญาตให้ None เพื่อใช้เป็น "global/default schedule" ได้
    employee_id: Optional[int] = None
    name: str
    day_of_week: DayOfWeek
    is_working_day: bool = True
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_start_time: Optional[time] = None
    break_end_time: Optional[time] = None
    is_active: bool = True
    is_default: bool = False

    # ===== ฟิลด์ตั้งค่าใหม่ (กำหนดจากฐานข้อมูล) =====
    late_grace_min: Optional[int] = None             # มาสายเกิน X นาทีถึงนับ
    early_leave_grace_min: Optional[int] = None      # ออกก่อนเกิน X นาทีถึงนับ
    absence_after_min: Optional[int] = None          # ทำงานต่ำกว่า X นาที = ขาด
    standard_daily_minutes: Optional[int] = None     # เวลามาตรฐาน/วัน (นาที)
    break_minutes_override: Optional[int] = None     # override เวลาพัก (นาที)

    @field_validator("day_of_week", mode="before")
    @classmethod
    def _normalize_dow(cls, v):
        return _coerce_day_of_week(v)

class WorkingScheduleCreate(WorkingScheduleBase):
    pass

class WorkingScheduleUpdate(BaseModel):
    employee_id: Optional[int] = None
    name: Optional[str] = None
    day_of_week: Optional[DayOfWeek] = None
    is_working_day: Optional[bool] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    break_start_time: Optional[time] = None
    break_end_time: Optional[time] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None

    late_grace_min: Optional[int] = None
    early_leave_grace_min: Optional[int] = None
    absence_after_min: Optional[int] = None
    standard_daily_minutes: Optional[int] = None
    break_minutes_override: Optional[int] = None

    @field_validator("day_of_week", mode="before")
    @classmethod
    def _normalize_dow(cls, v):
        return _coerce_day_of_week(v)

class WorkingScheduleInDB(WorkingScheduleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Employee Schema for Nesting ---
class EmployeeForTimeEntry(BaseModel):
    """A simplified Employee schema for nesting inside TimeEntryInDB."""
    id: int
    employee_id_number: str
    first_name: str
    last_name: str
    model_config = ConfigDict(from_attributes=True)

# --- Time Entry Schemas ---
class TimeEntryBase(BaseModel):
    employee_id: int
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    notes: Optional[str] = None
    is_late: bool = False
    late_minutes: float = 0.0
    is_early_exit: bool = False
    early_exit_minutes: float = 0.0
    status: models.TimeEntryStatus = models.TimeEntryStatus.PENDING

class TimeEntryCreate(TimeEntryBase):
    pass

class LeaveBalanceUpdate(BaseModel):
    opening: Optional[float] = None
    accrued: Optional[float] = None
    adjusted: Optional[float] = None
    carry_in: Optional[float] = None
    
class LeaveTypeOut(BaseModel):
    id: int
    name: str
    annual_quota: float | int = 0
    affects_balance: bool = True
    is_paid_leave: bool = True
    description: Optional[str] = None
    class Config: from_attributes = True
    
class LeaveBalanceOut(BaseModel):
    id: int
    employee_id: int
    leave_type_id: int
    year: int
    opening: float = 0
    accrued: float = 0
    used: float = 0
    adjusted: float = 0
    carry_in: float = 0
    available: float = 0
    # เพิ่ม metadata ฝั่งแสดงผล (ถ้าต้องการ)
    leave_type_name: str
    class Config: from_attributes = True

class TimeEntryUpdate(BaseModel):
    employee_id: Optional[int] = None
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    notes: Optional[str] = None
    is_late: Optional[bool] = None
    late_minutes: Optional[float] = None
    is_early_exit: Optional[bool] = None
    early_exit_minutes: Optional[float] = None
    status: Optional[models.TimeEntryStatus] = None
    
class LeaveBalanceBase(BaseModel):
    employee_id: int
    leave_type_id: int
    year: int
    opening: float = 0
    accrued: float = 0
    used: float = 0
    adjusted: float = 0
    carry_in: float = 0

class LeaveBalanceInDB(LeaveBalanceBase):
    id: int
    available: float
    class Config:
        orm_mode = True

class LeaveBalanceAdjust(BaseModel):
    adjusted_delta: float           # + เพิ่ม / - ลด
    note: Optional[str] = None

class TimeEntryInDB(TimeEntryBase):
    id: int
    employee: EmployeeForTimeEntry
    model_config = ConfigDict(from_attributes=True)

# --- Leave Type Schemas ---
class LeaveTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    affects_balance: bool = True
    is_paid_leave: bool = True
    annual_quota: float = 0.0
    # ✅ ใหม่
    accrue_per_year: float = 0.0
    max_quota: float = 0.0

class LeaveTypeCreate(LeaveTypeBase):
    pass

class LeaveTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    affects_balance: Optional[bool] = None
    is_paid_leave: Optional[bool] = None
    annual_quota: Optional[float] = None
    # ✅ ใหม่
    accrue_per_year: Optional[float] = None
    max_quota: Optional[float] = None

class LeaveTypeInDB(LeaveTypeBase):
    id: int
    class Config:
        from_attributes = True

# --- Leave Request Schemas ---
class LeaveRequestBase(BaseModel):
    employee_id: int
    leave_type_id: int
    start_date: datetime
    end_date: datetime
    reason: Optional[str] = None
    status: models.LeaveStatus = models.LeaveStatus.PENDING

class LeaveRequestCreate(LeaveRequestBase):
    pass

class LeaveRequestUpdate(BaseModel):
    employee_id: Optional[int] = None
    leave_type_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[models.LeaveStatus] = None

class LeaveRequestInDB(LeaveRequestBase):
    id: int
    request_date: datetime
    updated_at: datetime
    num_days: float = 0.0
    model_config = ConfigDict(from_attributes=True)

# --- Holiday Schemas ---
class HolidayBase(BaseModel):
    name: str
    holiday_date: date
    is_recurring: bool = False
    is_active: bool = True

class HolidayCreate(HolidayBase):
    pass

class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    holiday_date: Optional[date] = None
    is_recurring: Optional[bool] = None
    is_active: Optional[bool] = None

class HolidayInDB(HolidayBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Overtime Type Schemas ---
class OvertimeTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    rate_multiplier: float = Field(..., gt=0, description="Rate multiplier, e.g., 1.5 for 1.5x")
    is_active: bool = True

class OvertimeTypeCreate(OvertimeTypeBase):
    pass

class OvertimeTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rate_multiplier: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None

class OvertimeTypeInDB(OvertimeTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- Overtime Request Schemas ---
class EmployeeForOvertime(BaseModel):
    id: int
    first_name: str
    last_name: str
    model_config = ConfigDict(from_attributes=True)

class OvertimeRequestBase(BaseModel):
    employee_id: int
    ot_type_id: int
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = None
    status: models.LeaveStatus = models.LeaveStatus.PENDING

class OvertimeRequestCreate(OvertimeRequestBase):
    pass

class OvertimeRequestUpdate(BaseModel):
    employee_id: Optional[int] = None
    ot_type_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason: Optional[str] = None
    status: Optional[models.LeaveStatus] = None

class OvertimeRequestInDB(OvertimeRequestBase):
    id: int
    request_date: datetime
    updated_at: datetime
    employee: EmployeeForOvertime
    ot_type: OvertimeTypeInDB
    model_config = ConfigDict(from_attributes=True)
