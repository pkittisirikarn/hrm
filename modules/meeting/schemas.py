# modules/meeting/schemas.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List
import enum

from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict

# ---------- BookingStatus ----------
class BookingStatus(str, enum.Enum):
    PENDING   = "PENDING"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    CANCELLED = "CANCELLED"


# ---------- Rooms ----------
class MeetingRoomBase(BaseModel):
    name: str
    location: Optional[str] = None
    capacity: int = Field(ge=1, default=4)
    is_active: bool = True
    # เอาออก: equipment, contact_name
    coordinator_employee_id: Optional[int] = None
    coordinator_email: Optional[EmailStr] = None
    notes: Optional[str] = None

class MeetingRoomCreate(MeetingRoomBase):
    pass

class MeetingRoomUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None
    coordinator_employee_id: Optional[int] = None
    coordinator_email: Optional[EmailStr] = None
    notes: Optional[str] = None

class MeetingRoomOut(MeetingRoomBase):
    id: int
    image_url: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

# ---------- Bookings ----------
def _normalize_status(value) -> BookingStatus | None:
    if value is None:
        return None
    if isinstance(value, BookingStatus):
        return value
    s = str(value).strip().upper()
    # รองรับค่าประวัติเดิมจาก DB / ฟรอนต์
    if s == "BOOKED":
        s = "APPROVED"
    if s == "CANCELED":  # สะกดแบบอเมริกัน
        s = "CANCELLED"
    return BookingStatus(s)

class BookingBase(BaseModel):
    room_id: int
    subject: str = Field(..., min_length=1, max_length=200)
    requester_email: EmailStr
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    contact_person: Optional[str] = None
    status: Optional[BookingStatus] = BookingStatus.PENDING
    attendee_employee_ids: Optional[List[int]] = None

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, v):
        if v is None:
            return v
        # enum อยู่แล้ว
        if isinstance(v, BookingStatus):
            return v
        # เผื่อ frontend เผลอส่งเป็น dict เช่น {"VALUE":"PENDING"} หรือ {"value":"APPROVED"}
        if isinstance(v, dict):
            v = v.get("value") or v.get("VALUE") or v.get("status") or next(iter(v.values()), None)
        # เผื่อส่งเป็น object enum แบบมี name
        if hasattr(v, "name"):
            v = v.name
        # เหลือเป็นสตริง
        return BookingStatus(str(v).strip().upper())

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BaseModel):
    room_id: Optional[int] = None
    subject: Optional[str] = Field(default=None, min_length=1, max_length=200)
    requester_email: Optional[EmailStr] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    contact_person: Optional[str] = None
    status: Optional[BookingStatus] = None
    attendee_employee_ids: Optional[List[int]] = None

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, v):
        if v is None:
            return v
        if hasattr(v, "value"):
            v = v.value
        s = str(v).strip()
        if "." in s:
            s = s.split(".")[-1]
        return BookingStatus(s.upper())

class BookingAttendeeOut(BaseModel):
    id: int
    employee_id: Optional[int] = None
    attendee_name: Optional[str] = None
    attendee_email: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class BookingOut(BookingBase):
    id: int
    room: Optional[MeetingRoomOut] = None         # <- สำคัญ! เพื่อให้มี image_url
    attendees: List[BookingAttendeeOut] = []      # <- ให้มีค่าเริ่มต้นเป็น list ว่าง
    # ไม่อยากโชว์ attendee_employee_ids ใน output ก็ซ่อนไว้ได้ (optional)
    attendee_employee_ids: Optional[List[int]] = Field(default=None, exclude=True)
    model_config = ConfigDict(from_attributes=True)
