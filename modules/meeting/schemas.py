from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

class AmenityBase(BaseModel):
    name: str

class AmenityCreate(AmenityBase): pass
class AmenityOut(AmenityBase):
    id: int
    class Config: from_attributes = True

class RoomBase(BaseModel):
    code: Optional[str] = None
    name: str
    capacity: int = 0
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: bool = True
    amenity_ids: List[int] = Field(default_factory=list)

class RoomCreate(RoomBase): pass
class RoomUpdate(RoomBase): pass

class RoomOut(RoomBase):
    id: int
    amenities: List[AmenityOut] = []
    class Config: from_attributes = True

class BookingBase(BaseModel):
    room_id: int
    title: str
    start_time: datetime
    end_time: datetime
    participants: int = 0

    booked_by_user_id: Optional[int] = None
    booked_by_name: str
    booked_by_email: Optional[EmailStr] = None

    coordinator_user_id: Optional[int] = None
    coordinator_name: Optional[str] = None
    coordinator_email: Optional[EmailStr] = None

    contact_name: Optional[str] = None
    contact_email: Optional[EmailStr] = None

class BookingCreate(BookingBase): pass
class BookingUpdate(BookingBase): pass

class BookingOut(BookingBase):
    id: int
    status: str
    class Config: from_attributes = True

# Dashboard
class DashboardPie(BaseModel):
    total_rooms: int
    in_use_now: int
    free_now: int
