from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func

from .models import MeetingRoom, Amenity, RoomBooking, BookingStatus
from . import schemas

# ---- Email helper (ปรับให้ใช้ SMTP/proj ของคุณ) ----
def send_email(to: str, subject: str, body: str) -> None:
    # TODO: ผูก SMTP จริง หรือ utility เดิมในโปรเจกต์
    # ปัจจุบันทำเป็นสตับไว้เฉย ๆ
    print(f"[EMAIL] to={to} subject={subject}\n{body}\n")

# ---- Overlap checker ----
def _ensure_room_free(db: Session, room_id: int, start: datetime, end: datetime, exclude_id: Optional[int] = None):
    if end <= start:
        raise HTTPException(status_code=400, detail="End time must be after start time.")
    q = db.query(RoomBooking).filter(
        RoomBooking.room_id == room_id,
        RoomBooking.status.in_([BookingStatus.PENDING.value, BookingStatus.APPROVED.value]),
        RoomBooking.start_time < end,
        RoomBooking.end_time > start,
    )
    if exclude_id:
        q = q.filter(RoomBooking.id != exclude_id)
    if db.query(q.exists()).scalar():
        raise HTTPException(status_code=409, detail="Time slot overlaps an existing booking.")

# ---- Amenities ----
def create_amenity(db: Session, data: schemas.AmenityCreate) -> Amenity:
    obj = Amenity(name=data.name.strip())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def list_amenities(db: Session) -> List[Amenity]:
    return db.query(Amenity).order_by(Amenity.name.asc()).all()

# ---- Rooms ----
def create_room(db: Session, data: schemas.RoomCreate) -> MeetingRoom:
    room = MeetingRoom(
        code=data.code,
        name=data.name,
        capacity=data.capacity,
        description=data.description,
        image_url=data.image_url,
        is_active=data.is_active,
    )
    if data.amenity_ids:
        room.amenities = db.query(Amenity).filter(Amenity.id.in_(data.amenity_ids)).all()
    db.add(room); db.commit(); db.refresh(room)
    return room

def update_room(db: Session, room_id: int, data: schemas.RoomUpdate) -> Optional[MeetingRoom]:
    room = db.get(MeetingRoom, room_id)
    if not room: return None
    for f in ("code","name","capacity","description","image_url","is_active"):
        setattr(room, f, getattr(data, f))
    if data.amenity_ids is not None:
        room.amenities = db.query(Amenity).filter(Amenity.id.in_(data.amenity_ids)).all()
    db.commit(); db.refresh(room)
    return room

def list_rooms(db: Session) -> List[MeetingRoom]:
    return (db.query(MeetingRoom)
              .options(joinedload(MeetingRoom.amenities))
              .order_by(MeetingRoom.name.asc()).all())

def get_room(db: Session, room_id: int) -> Optional[MeetingRoom]:
    return (db.query(MeetingRoom)
              .options(joinedload(MeetingRoom.amenities))
              .filter(MeetingRoom.id == room_id).first())

def delete_room(db: Session, room_id: int) -> bool:
    room = db.get(MeetingRoom, room_id)
    if not room: return False
    db.delete(room); db.commit(); return True

# ---- Bookings ----
def create_booking(db: Session, data: schemas.BookingCreate) -> RoomBooking:
    _ensure_room_free(db, data.room_id, data.start_time, data.end_time)

    booking = RoomBooking(
        room_id=data.room_id,
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        participants=data.participants,
        booked_by_user_id=data.booked_by_user_id,
        booked_by_name=data.booked_by_name,
        booked_by_email=data.booked_by_email,
        coordinator_user_id=data.coordinator_user_id,
        coordinator_name=data.coordinator_name,
        coordinator_email=data.coordinator_email,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        status=BookingStatus.PENDING.value,
    )
    db.add(booking); db.commit(); db.refresh(booking)

    # Email: แจ้งผู้จอง + ผู้ประสานงาน + ผู้ติดต่อ
    subj = f"[Booking Created] {booking.title}"
    body = f"Your booking request for room #{booking.room_id} ({booking.title}) " \
           f"on {booking.start_time} - {booking.end_time} is submitted and pending approval."
    if booking.booked_by_email: send_email(booking.booked_by_email, subj, body)
    for extra in [booking.coordinator_email, booking.contact_email]:
        if extra: send_email(extra, subj, f"New booking pending approval.\n{body}")

    return booking

def update_booking(db: Session, booking_id: int, data: schemas.BookingUpdate) -> Optional[RoomBooking]:
    bk = db.get(RoomBooking, booking_id)
    if not bk: return None
    _ensure_room_free(db, data.room_id, data.start_time, data.end_time, exclude_id=bk.id)
    for f in ("room_id","title","start_time","end_time","participants",
              "booked_by_user_id","booked_by_name","booked_by_email",
              "coordinator_user_id","coordinator_name","coordinator_email",
              "contact_name","contact_email"):
        setattr(bk, f, getattr(data, f))
    db.commit(); db.refresh(bk)
    return bk

def list_bookings(db: Session) -> List[RoomBooking]:
    return (db.query(RoomBooking)
              .options(joinedload(RoomBooking.room))
              .order_by(RoomBooking.start_time.desc()).all())

def get_booking(db: Session, booking_id: int) -> Optional[RoomBooking]:
    return (db.query(RoomBooking)
              .options(joinedload(RoomBooking.room))
              .filter(RoomBooking.id == booking_id).first())

def set_booking_status(db: Session, booking_id: int, status: BookingStatus) -> Optional[RoomBooking]:
    bk = db.get(RoomBooking, booking_id)
    if not bk: return None
    bk.status = status.value
    db.commit(); db.refresh(bk)

    subj = f"[Booking {status.value}] {bk.title}"
    body = f"Your booking for room #{bk.room_id} ({bk.title}) on {bk.start_time} - {bk.end_time} is {status.value.lower()}."
    if bk.booked_by_email: send_email(bk.booked_by_email, subj, body)
    for extra in [bk.coordinator_email, bk.contact_email]:
        if extra: send_email(extra, subj, body)
    return bk

# ---- Dashboard ----
def dashboard_now(db: Session) -> schemas.DashboardPie:
    now = func.now()
    total = db.query(func.count(MeetingRoom.id)).scalar() or 0
    in_use = (db.query(func.count(RoomBooking.id))
                .filter(RoomBooking.status == BookingStatus.APPROVED.value)
                .filter(RoomBooking.start_time <= now, RoomBooking.end_time >= now)
                .scalar() or 0)
    return schemas.DashboardPie(
        total_rooms=total,
        in_use_now=in_use,
        free_now=max(0, total - in_use),
    )
