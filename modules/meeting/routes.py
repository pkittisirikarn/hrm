# modules/meeting/routes.py
from __future__ import annotations

import os
import uuid
from datetime import date
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    UploadFile,
    File,
    Query,
)
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from starlette.templating import Jinja2Templates
from modules.meeting import models
from database.connection import get_db

# models/schemas
from modules.meeting.schemas import BookingStatus 
from modules.meeting import models  # ใช้ models.* ให้ครบ
from modules.meeting.models import MeetingRoom, Booking
from modules.meeting.schemas import (
    MeetingRoomCreate,
    MeetingRoomUpdate,
    MeetingRoomOut,
    BookingCreate,
    BookingUpdate,
    BookingOut,
    BookingStatus as SBookingStatus,  # <- enum ฝั่ง schema สำหรับรับจาก API
)

# services
from modules.meeting import services
from modules.meeting.services import (
    assert_no_overlap,
    create_booking as svc_create_booking,
    update_booking as svc_update_booking,
)

api = APIRouter(prefix="/api/v1/meeting", tags=["Meeting API"])
pages = APIRouter()
templates = Jinja2Templates(directory="templates")

# อัปโหลดรูปห้อง
UPLOAD_DIR = os.path.join("static", "uploads", "rooms")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ---------- Rooms ----------
@api.get("/rooms/", response_model=List[MeetingRoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(MeetingRoom).order_by(MeetingRoom.name.asc()).all()


@api.post("/rooms/", response_model=MeetingRoomOut)
def create_room(payload: MeetingRoomCreate, db: Session = Depends(get_db)):
    if db.query(MeetingRoom).filter(MeetingRoom.name == payload.name).first():
        raise HTTPException(status_code=400, detail="ชื่อห้องซ้ำ")
    room = MeetingRoom(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room

@api.put("/rooms/{room_id}", response_model=MeetingRoomOut)
def update_room(room_id: int, payload: MeetingRoomUpdate, db: Session = Depends(get_db)):
    room = db.get(MeetingRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="ไม่พบห้อง")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(room, k, v)
    db.commit()
    db.refresh(room)
    return room

@api.post("/rooms/{room_id}/image", response_model=MeetingRoomOut)
def upload_room_image(room_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    room = db.get(MeetingRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="ไม่พบห้อง")

    ext = (os.path.splitext(file.filename)[1] or ".jpg").lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        ext = ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    with open(path, "wb") as f:
        f.write(file.file.read())

    room.image_url = f"/static/uploads/rooms/{fname}"
    db.commit()
    db.refresh(room)
    return room

@api.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(MeetingRoom, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="ไม่พบห้อง")
    db.delete(room)
    db.commit()
    return None

# ---------- Bookings ----------
@api.get("/bookings/", response_model=List[BookingOut])
def list_bookings(db: Session = Depends(get_db)):
    # โหลดพร้อม room + attendees เพื่อให้ frontend มีชื่อผู้เข้าร่วม
    rows = (
        db.query(models.Booking)
        .options(joinedload(models.Booking.room), joinedload(models.Booking.attendees))
        .order_by(models.Booking.start_time.desc())
        .all()
    )
    return rows

@api.post("/bookings/", response_model=BookingOut)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    room = db.get(models.MeetingRoom, payload.room_id)
    if not room or not room.is_active:
        raise HTTPException(status_code=400, detail="ห้องไม่พร้อมใช้งาน")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="ช่วงเวลาผิดพลาด")
    assert_no_overlap(db, payload.room_id, payload.start_time, payload.end_time)
    booking = svc_create_booking(db, payload)
    return booking

@api.put("/bookings/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: int, payload: BookingUpdate, db: Session = Depends(get_db)):
    st = payload.start_time
    et = payload.end_time
    rid = payload.room_id
    if st and et and et <= st:
        raise HTTPException(status_code=400, detail="ช่วงเวลาผิดพลาด")
    if rid and st and et:
        assert_no_overlap(db, rid, st, et, exclude_booking_id=booking_id)
    return svc_update_booking(db, booking_id, payload)

@api.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="ไม่พบการจอง")
    b.status = models.BookingStatus.CANCELLED
    db.commit()
    db.refresh(b)
    services.send_booking_email(db, b)
    return b

@api.post("/bookings/{booking_id}/status", response_model=BookingOut)
def set_booking_status(
    booking_id: int,
    status: BookingStatus = Query(..., description="PENDING|APPROVED|REJECTED"),
    db: Session = Depends(get_db),
):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="ไม่พบการจอง")

    # map schema enum -> model enum
    b.status = getattr(models.BookingStatus, status.name)
    db.commit()
    db.refresh(b)

    services.send_booking_email(db, b)  # ส่งเมลแจ้งสถานะใหม่
    return b

@api.post("/bookings/{booking_id}/reject", response_model=BookingOut)
def reject_booking(booking_id: int, db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="ไม่พบการจอง")
    b.status = models.BookingStatus.REJECTED
    db.commit()
    db.refresh(b)
    services.send_booking_email(db, b)
    return b


@api.delete("/bookings/{booking_id}", status_code=204)
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="ไม่พบการจอง")
    db.delete(b)
    db.commit()
    return None


# ---------- Booking dashboard summary (API) ----------
@api.get("/rooms/booking-summary")
def booking_summary_api(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    return services.booking_summary(db=db, date_from=date_from, date_to=date_to)

# ---------- UI Pages ----------
@pages.get("/meeting/rooms", response_class=HTMLResponse, include_in_schema=False)
def rooms_page(request: Request):
    return templates.TemplateResponse("meeting/rooms.html", {"request": request})

@pages.get("/meeting/bookings", response_class=HTMLResponse, include_in_schema=False)
def bookings_page(request: Request):
    return templates.TemplateResponse("meeting/bookings.html", {"request": request})

# ✅ หน้า Dashboard ตามที่ต้องการ
@pages.get("/meeting/dashboard", response_class=HTMLResponse, include_in_schema=False)
def meeting_dashboard_page(request: Request):
    return templates.TemplateResponse("meeting/dashboard.html", {"request": request})

