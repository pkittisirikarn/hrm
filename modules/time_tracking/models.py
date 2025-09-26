# modules/time_tracking/models.py
from sqlalchemy import Column, Integer, String, Date, DateTime, Time, Boolean, ForeignKey, Text, Enum, Float
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

class LeaveType(Base):
    __tablename__ = "leave_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    max_days_per_year = Column(Integer, default=0)
    is_paid_leave = Column(Boolean, default=True)
    leave_requests = relationship("LeaveRequest", back_populates="leave_type")

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
    
    # ====== คอลัมน์ใหม่สำหรับตั้งค่าเกณฑ์จากฐานข้อมูล ======
    late_grace_min         = Column(Integer, nullable=True)  # มาสายเกิน X นาทีถึงนับ (เช่น 5)
    early_leave_grace_min  = Column(Integer, nullable=True)  # ออกก่อนเกิน X นาทีถึงนับ
    absence_after_min      = Column(Integer, nullable=True)  # ทำงานจริงต่ำกว่า X นาที = "ขาด"
    standard_daily_minutes = Column(Integer, nullable=True)  # เวลามาตรฐาน/วัน (นาที) เช่น 480
    # ถ้าต้องการ override เวลาพักให้เป็นค่าคงที่ ใช้คอลัมน์นี้; ถ้า NULL จะคำนวณจาก break_start_time/end_time
    break_minutes_override = Column(Integer, nullable=True)

class Holiday(Base):
    __tablename__ = "holidays"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    holiday_date = Column(Date, unique=True, nullable=False)
    is_recurring = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

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

class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"   # มา/ไม่สาย
    LATE    = "LATE"      # มาสาย
    LEAVE   = "LEAVE"     # ลา
    ABSENCE = "ABSENCE"   # ขาดงาน


class AttendanceDaily(Base):
    __tablename__ = "attendance_daily"

    id = Column(Integer, primary_key=True, index=True)

    # แนะนำให้มี FK ชี้ไปตาราง employees (จะช่วยเวลาทำ join/report ให้ชัดเจน)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # วันที่ของรายการสรุป (1 แถว/พนักงาน/วัน)
    day = Column(Date, nullable=False, index=True)

    # สถานะรายวัน ใช้ Enum ให้สอดคล้องกับคลาส AttendanceStatus
    status_code = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT)

    # นาทีทำงานจริงของวันนั้น (หลังหักพักแล้ว ถ้าใช้)
    work_minutes = Column(Integer, nullable=False, default=0)

    # นาทีกะ “มาสาย” ของวันนั้น (หัก grace แล้ว)
    late_minutes = Column(Integer, nullable=False, default=0)

    # นาทีกะ “ออกก่อน” ของวันนั้น (หัก grace แล้ว)
    early_leave_minutes = Column(Integer, nullable=False, default=0)

    # ถ้าเป็นวันลาที่ “จ่ายเงิน” ให้ True (เช่น ลาป่วยมีใบรับรอง/ลากิจตามนโยบาย)
    is_paid_leave = Column(Boolean, nullable=False, default=True)