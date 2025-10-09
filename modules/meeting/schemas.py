# modules/meeting/schemas.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# ---- Rooms ----
class MeetingRoomBase(BaseModel):
    name: str
    location: Optional[str] = None
    capacity: int = Field(ge=1, default=4)
    is_active: bool = True

    # NEW
    contact_name: Optional[str] = None
    coordinator_employee_id: Optional[int] = None
    coordinator_email: Optional[EmailStr] = None
    approval_status: Optional[str] = "Approved"  # Pending/Approved/Rejected

class MeetingRoomCreate(MeetingRoomBase):
    pass

class MeetingRoomUpdate(MeetingRoomBase):
    pass

class MeetingRoomOut(MeetingRoomBase):
    id: int
    image_url: Optional[str] = None
    class Config:
        from_attributes = True

# ---- Bookings ----
# modules/meeting/schemas.py
from pydantic import BaseModel, Field, EmailStr
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, List
from datetime import datetime

# ... (ส่วน Room เดิมของคุณคงไว้)

# ---- Bookings (ให้ตรงกับ model) ----
class BookingBase(BaseModel):
    room_id: int
    subject: str = Field(..., min_length=1, max_length=200)          # ← ชื่อเดียวกับ model
    requester_email: EmailStr                                       # ← ชื่อเดียวกับ model
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    status: str = Field(default="Booked")

    # รายชื่อผู้เข้าร่วมแบบอ้างอิงพนักงาน (ถ้ามี)
    attendee_employee_ids: Optional[List[int]] = None

class BookingCreate(BookingBase):
    pass

class BookingUpdate(BookingBase):
    pass

class BookingAttendeeOut(BaseModel):
    id: int
    employee_id: Optional[int] = None
    attendee_name: Optional[str] = None
    attendee_email: Optional[str] = None
    class Config:
        from_attributes = True

class BookingOut(BookingBase):
    id: int
    attendees: List[BookingAttendeeOut] | None = None
    class Config:
        from_attributes = True
    


# class BookingOut(BookingBase):
#     id: int
#     attendees: List[BookingAttendeeOut] | None = None
#     class Config:
#         from_attributes = True