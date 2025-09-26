from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from . import schemas, services
from .models import BookingStatus
from database.connection import get_db  # <- ใช้ dependency เดิมของโปรเจกต์คุณ

router = APIRouter(prefix="/api/v1/meeting", tags=["Meeting Rooms"])

# Amenities
@router.post("/amenities/", response_model=schemas.AmenityOut)
def create_amenity_api(data: schemas.AmenityCreate, db: Session = Depends(get_db)):
    return services.create_amenity(db, data)

@router.get("/amenities/", response_model=List[schemas.AmenityOut])
def list_amenities_api(db: Session = Depends(get_db)):
    return services.list_amenities(db)

# Rooms
@router.post("/rooms/", response_model=schemas.RoomOut)
def create_room_api(data: schemas.RoomCreate, db: Session = Depends(get_db)):
    return services.create_room(db, data)

@router.get("/rooms/", response_model=List[schemas.RoomOut])
def list_rooms_api(db: Session = Depends(get_db)):
    return services.list_rooms(db)

@router.get("/rooms/{room_id}", response_model=schemas.RoomOut)
def get_room_api(room_id: int, db: Session = Depends(get_db)):
    obj = services.get_room(db, room_id)
    if not obj: raise HTTPException(404, "Room not found")
    return obj

@router.put("/rooms/{room_id}", response_model=schemas.RoomOut)
def update_room_api(room_id: int, data: schemas.RoomUpdate, db: Session = Depends(get_db)):
    obj = services.update_room(db, room_id, data)
    if not obj: raise HTTPException(404, "Room not found")
    return obj

@router.delete("/rooms/{room_id}")
def delete_room_api(room_id: int, db: Session = Depends(get_db)):
    ok = services.delete_room(db, room_id)
    if not ok: raise HTTPException(404, "Room not found")
    return {"message": "Room deleted"}

# Bookings
@router.post("/bookings/", response_model=schemas.BookingOut)
def create_booking_api(data: schemas.BookingCreate, db: Session = Depends(get_db)):
    return services.create_booking(db, data)

@router.get("/bookings/", response_model=List[schemas.BookingOut])
def list_bookings_api(db: Session = Depends(get_db)):
    return services.list_bookings(db)

@router.get("/bookings/{booking_id}", response_model=schemas.BookingOut)
def get_booking_api(booking_id: int, db: Session = Depends(get_db)):
    obj = services.get_booking(db, booking_id)
    if not obj: raise HTTPException(404, "Booking not found")
    return obj

@router.put("/bookings/{booking_id}", response_model=schemas.BookingOut)
def update_booking_api(booking_id: int, data: schemas.BookingUpdate, db: Session = Depends(get_db)):
    obj = services.update_booking(db, booking_id, data)
    if not obj: raise HTTPException(404, "Booking not found")
    return obj

@router.post("/bookings/{booking_id}/approve", response_model=schemas.BookingOut)
def approve_booking_api(booking_id: int, db: Session = Depends(get_db)):
    obj = services.set_booking_status(db, booking_id, BookingStatus.APPROVED)
    if not obj: raise HTTPException(404, "Booking not found")
    return obj

@router.post("/bookings/{booking_id}/reject", response_model=schemas.BookingOut)
def reject_booking_api(booking_id: int, db: Session = Depends(get_db)):
    obj = services.set_booking_status(db, booking_id, BookingStatus.REJECTED)
    if not obj: raise HTTPException(404, "Booking not found")
    return obj

@router.post("/bookings/{booking_id}/cancel", response_model=schemas.BookingOut)
def cancel_booking_api(booking_id: int, db: Session = Depends(get_db)):
    obj = services.set_booking_status(db, booking_id, BookingStatus.CANCELLED)
    if not obj: raise HTTPException(404, "Booking not found")
    return obj

# Dashboard
@router.get("/dashboard/now", response_model=schemas.DashboardPie)
def dashboard_now_api(db: Session = Depends(get_db)):
    return services.dashboard_now(db)
