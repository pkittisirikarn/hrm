# modules/time_tracking/models.py
from sqlalchemy import (
    Column, Integer, String, Date, DateTime, Time, Boolean,
    ForeignKey, Text, Enum, Float, UniqueConstraint
)
from sqlalchemy.orm import relationship
from database.base import Base
import datetime
import enum

class LeaveStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"

class TimeEntryStatus(enum.Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class DayOfWeek(enum.Enum):
    MONDAY = "Monday"
    TUESDAY = "Tuesday"
    WEDNESDAY = "Wednesday"
    THURSDAY = "Thursday"
    FRIDAY = "Friday"
    SATURDAY = "Saturday"
    SUNDAY = "Sunday"

# ---------------- Leave Balance ----------------
class LeaveBalance(Base):
    __tablename__ = "leave_balances"
    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)

    # ใช้ชื่อคอลัมน์ให้ตรงกับตารางจริง
    opening_quota = Column(Float, default=0.0)  # โควต้าต้นปี/ยกมา
    accrued       = Column(Float, default=0.0)  # เติมระหว่างปี
    used          = Column(Float, default=0.0)  # ใช้ไปแล้ว
    adjusted      = Column(Float, default=0.0)  # ปรับมือ (+/-)
    carry_in      = Column(Float, default=0.0)  # โอนจากปีก่อน (ถ้าใช้)
    updated_at    = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    @property
    def available(self) -> float:
        # คำนวณฝั่งแอป (ไม่พึ่ง virtual column)
        return float((self.opening_quota or 0)
                     + (self.accrued or 0)
                     + (self.carry_in or 0)
                     + (self.adjusted or 0)
                     - (self.used or 0))

    employee = relationship("Employee", backref="leave_balances")
    leave_type = relationship("LeaveType", backref="leave_balances")

    __table_args__ = (
        UniqueConstraint("employee_id", "leave_type_id", "year", name="uq_leave_balance_emp_type_year"),
    )

# ---------------- Leave Type ----------------.
class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    # quota เดิม
    max_days_per_year = Column(Integer, default=0)
    annual_quota = Column(Float, default=0.0)
    affects_balance = Column(Boolean, default=True)
    is_paid_leave = Column(Boolean, default=True)

    # ✅ ใหม่: ตั้งค่าผ่าน UI
    accrue_per_year = Column(Float, default=0.0)  # เพิ่มสิทธิ์ต่อปี
    max_quota = Column(Float, default=0.0)        # เพดานสูงสุด

    leave_requests = relationship("LeaveRequest", back_populates="leave_type")

# ---------------- Time Entry ----------------
class TimeEntry(Base):
    __tablename__ = "time_entries"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    check_in_time = Column(DateTime, nullable=False)
    check_out_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    is_late = Column(Boolean, default=False)
    late_minutes = Column(Float, default=0.0)
    is_early_exit = Column(Boolean, default=False)
    early_exit_minutes = Column(Float, default=0.0)
    status = Column(Enum(TimeEntryStatus), default=TimeEntryStatus.PENDING, nullable=False)

    employee = relationship("Employee", back_populates="time_entries")

# ---------------- Leave Request ----------------
class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    leave_type_id = Column(Integer, ForeignKey("leave_types.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    request_date = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    employee = relationship("Employee", back_populates="leave_requests")
    leave_type = relationship("LeaveType", back_populates="leave_requests")

# ---------------- Working Schedule ----------------
class WorkingSchedule(Base):
    __tablename__ = "working_schedules"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    name = Column(String, index=True, nullable=False)
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    is_working_day = Column(Boolean, default=True)
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)
    break_start_time = Column(Time, nullable=True)
    break_end_time = Column(Time, nullable=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)

    late_grace_min         = Column(Integer, nullable=True)
    early_leave_grace_min  = Column(Integer, nullable=True)
    absence_after_min      = Column(Integer, nullable=True)
    standard_daily_minutes = Column(Integer, nullable=True)
    break_minutes_override = Column(Integer, nullable=True)

# ---------------- Holiday ----------------
class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    holiday_date = Column(Date, unique=True, nullable=False)
    is_recurring = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

# ---------------- OT ----------------
class OvertimeType(Base):
    __tablename__ = "ot_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    rate_multiplier = Column(Float, nullable=False, default=1.0)
    is_active = Column(Boolean, default=True)

    ot_requests = relationship("OvertimeRequest", back_populates="ot_type")

class OvertimeRequest(Base):
    __tablename__ = "ot_requests"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    ot_type_id = Column(Integer, ForeignKey("ot_types.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    status = Column(Enum(LeaveStatus), default=LeaveStatus.PENDING, nullable=False)
    request_date = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    employee = relationship("Employee", back_populates="ot_requests")
    ot_type = relationship("OvertimeType", back_populates="ot_requests")

# ---------------- Attendance ----------------
class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    LATE    = "LATE"
    LEAVE   = "LEAVE"
    ABSENCE = "ABSENCE"

class AttendanceDaily(Base):
    __tablename__ = "attendance_daily"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    day = Column(Date, nullable=False, index=True)
    status_code = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)
    work_minutes = Column(Integer, nullable=False, default=0)
    late_minutes = Column(Integer, nullable=False, default=0)
    early_leave_minutes = Column(Integer, nullable=False, default=0)
    is_paid_leave = Column(Boolean, nullable=False, default=True)
