# modules/meeting/models.py
from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from database.base import Base


class BookingStatus(str, Enum):
    PENDING = "Pending"
    BOOKED = "Booked"
    CANCELLED = "Cancelled"


class RoomApproval(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

class MeetingRoom(Base):
    __tablename__ = "meeting_rooms"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    location = Column(String(200), nullable=True)
    capacity = Column(Integer, nullable=True)

    # NEW
    image_url = Column(String(300), nullable=True)
    contact_name = Column(String(120), nullable=True)
    coordinator_employee_id = Column(Integer, nullable=True)
    coordinator_email = Column(String(200), nullable=True)
    approval_status = Column(SAEnum(RoomApproval), default=RoomApproval.APPROVED, nullable=False)

    notes = Column(Text, nullable=True)
    is_active = Column(Integer, default=1)

    bookings = relationship("Booking", back_populates="room", cascade="all, delete-orphan")

class Booking(Base):
    __tablename__ = "meeting_bookings"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(Integer, ForeignKey("meeting_rooms.id", ondelete="CASCADE"), nullable=False)
    subject = Column(String(200), nullable=False)
    requester_email = Column(String(200), nullable=False)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    status = Column(SAEnum(BookingStatus), default=BookingStatus.BOOKED, nullable=False)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    room = relationship("MeetingRoom", back_populates="bookings")
    attendees = relationship(
        "BookingAttendee",
        back_populates="booking",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class BookingAttendee(Base):
    __tablename__ = "meeting_booking_attendees"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(
        Integer,
        ForeignKey("meeting_bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ผูกกับพนักงาน (ถ้ามี) เก็บเป็น id ไว้ก่อน เผื่อ lookup อีเมลจาก data_management
    employee_id = Column(Integer, nullable=True)

    # กันเหนียว เก็บชื่อ/อีเมลที่ใช้ตอนสร้างไว้ด้วย (เผื่อพนักงานถูกลบ/แก้ในอนาคต)
    attendee_name = Column(String(200), nullable=True)
    attendee_email = Column(String(200), nullable=True)

    booking = relationship("Booking", back_populates="attendees")
