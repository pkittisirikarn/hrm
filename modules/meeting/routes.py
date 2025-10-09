from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile, File
import os, uuid
from sqlalchemy.orm import Session
from typing import List
from starlette.templating import Jinja2Templates

from database.connection import get_db
from modules.common.email_service import EmailService
from config.settings import email_settings
from modules.meeting.models import MeetingRoom, Booking, BookingStatus
from modules.meeting.schemas import MeetingRoomCreate, MeetingRoomUpdate, MeetingRoomOut, BookingCreate, BookingUpdate, BookingOut
from modules.meeting.services import assert_no_overlap, create_booking as svc_create_booking, update_booking as svc_update_booking

api = APIRouter(prefix="/api/v1/meeting", tags=["meeting"])
pages = APIRouter()
templates = Jinja2Templates(directory="templates")

# ---------- Rooms ----------
@api.get("/rooms/", response_model=List[MeetingRoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(MeetingRoom).order_by(MeetingRoom.name.asc()).all()

@api.post("/rooms/", response_model=MeetingRoomOut)
def create_room(payload: MeetingRoomCreate, db: Session = Depends(get_db)):
    if db.query(MeetingRoom).filter(MeetingRoom.name == payload.name).first():
        raise HTTPException(400, "ชื่อห้องซ้ำ")
    room = MeetingRoom(**payload.model_dump())
    db.add(room); db.commit(); db.refresh(room)
    return room

@api.put("/rooms/{room_id}", response_model=MeetingRoomOut)
def update_room(room_id: int, payload: MeetingRoomUpdate, db: Session = Depends(get_db)):
    room = db.get(MeetingRoom, room_id)
    if not room: raise HTTPException(404, "ไม่พบห้อง")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(room, k, v)
    db.commit(); db.refresh(room)
    return room

@api.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(MeetingRoom, room_id)
    if not room: raise HTTPException(404, "ไม่พบห้อง")
    db.delete(room); db.commit()

# ---------- Bookings ----------
@api.get("/bookings/", response_model=List[BookingOut])
def list_bookings(db: Session = Depends(get_db)):
    return db.query(Booking).order_by(Booking.start_time.desc()).all()

@api.post("/bookings/", response_model=BookingOut)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    room = db.get(MeetingRoom, payload.room_id)
    if not room or not room.is_active:
        raise HTTPException(400, "ห้องไม่พร้อมใช้งาน")
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "ช่วงเวลาผิดพลาด")

    assert_no_overlap(db, payload.room_id, payload.start_time, payload.end_time)
    return svc_create_booking(db, payload)

@api.put("/bookings/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: int, payload: BookingUpdate, db: Session = Depends(get_db)):
    if payload.end_time <= payload.start_time:
        raise HTTPException(400, "ช่วงเวลาผิดพลาด")
    assert_no_overlap(db, payload.room_id, payload.start_time, payload.end_time, exclude_booking_id=booking_id)
    return svc_update_booking(db, booking_id, payload)

@api.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b: raise HTTPException(404, "ไม่พบการจอง")
    b.status = BookingStatus.CANCELLED
    db.commit(); db.refresh(b)
    return b

@api.delete("/bookings/{booking_id}", status_code=204)
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b: raise HTTPException(404, "ไม่พบการจอง")
    db.delete(b); db.commit()

# ---------- Pages ----------
@pages.get("/meeting/rooms")
def rooms_page(request: Request):
    return templates.TemplateResponse("meeting/rooms.html", {"request": request})

@pages.get("/meeting/bookings")
def bookings_page(request: Request):
    return templates.TemplateResponse("meeting/bookings.html", {"request": request})
