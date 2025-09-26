from __future__ import annotations
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# --- M2M: Room <-> Amenity
room_amenity = Table(
    "room_amenity",
    Base.metadata,
    Column("room_id", ForeignKey("meeting_rooms.id"), primary_key=True),
    Column("amenity_id", ForeignKey("meeting_amenities.id"), primary_key=True),
)

class BookingStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class MeetingRoom(Base):
    __tablename__ = "meeting_rooms"
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, index=True, nullable=True)
    name = Column(String(200), nullable=False)
    capacity = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)        # ถ้าอยากเก็บหลายรูป ให้ทำตาราง images แยก
    is_active = Column(Boolean, default=True)

    amenities = relationship("Amenity", secondary=room_amenity, back_populates="rooms")
    bookings = relationship("RoomBooking", back_populates="room", cascade="all,delete")

class Amenity(Base):
    __tablename__ = "meeting_amenities"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    rooms = relationship("MeetingRoom", secondary=room_amenity, back_populates="amenities")

class RoomBooking(Base):
    __tablename__ = "room_bookings"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False)

    # ข้อมูลการจอง
    title = Column(String(255), nullable=False)               # หัวข้อการประชุม
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    participants = Column(Integer, default=0)                 # จำนวนผู้เข้าร่วม

    # ผู้จอง (เลือกจากระบบหรืออิสระก็ได้)
    booked_by_user_id = Column(Integer, nullable=True)
    booked_by_name = Column(String(200), nullable=False)
    booked_by_email = Column(String(255), nullable=True)

    # ผู้ประสานงาน / ผู้ติดต่อ (เลือกจากผู้ใช้หรือกรอกเอง)
    coordinator_user_id = Column(Integer, nullable=True)
    coordinator_name = Column(String(200), nullable=True)
    coordinator_email = Column(String(255), nullable=True)

    contact_name = Column(String(200), nullable=True)
    contact_email = Column(String(255), nullable=True)

    # สถานะ
    status = Column(String(20), default=BookingStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("MeetingRoom", back_populates="bookings")
