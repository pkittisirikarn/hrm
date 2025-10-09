from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime

from modules.meeting import models, schemas
from modules.common.email_service import EmailService
from config.settings import email_settings
from modules.data_management import models as dm_models

email_svc = EmailService(email_settings)

def _emails_from_employee_ids(db: Session, employee_ids: Optional[List[int]]) -> List[str]:
    if not employee_ids:
        return []
    rows = db.query(dm_models.Employee).filter(dm_models.Employee.id.in_(employee_ids)).all()
    return [(r.email or "").strip() for r in rows if (r.email or "").strip()]

def assert_no_overlap(
    db: Session, room_id: int, start_time: datetime, end_time: datetime, exclude_booking_id: int | None = None
) -> None:
    q = (
        db.query(models.Booking)
        .filter(models.Booking.room_id == room_id)
        .filter(models.Booking.status != models.BookingStatus.CANCELLED)
        .filter(models.Booking.start_time < end_time)
        .filter(models.Booking.end_time > start_time)
    )
    if exclude_booking_id:
        q = q.filter(models.Booking.id != exclude_booking_id)
    if q.first():
        raise HTTPException(400, "ช่วงเวลานี้ถูกจองแล้ว (ห้องเดียวกันและเวลาซ้อนทับ)")

def create_booking(db: Session, payload: schemas.BookingCreate) -> models.Booking:
    attendee_emails = _emails_from_employee_ids(db, payload.attendee_employee_ids)
    booking = models.Booking(
        room_id=payload.room_id,
        subject=payload.subject,
        requester_email=(payload.requester_email or "").strip() or None,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
        status=models.BookingStatus.BOOKED,
    )
    db.add(booking); db.commit(); db.refresh(booking)

    # ส่งเมลผู้จอง + ผู้เข้าร่วม
    to_list = []
    if booking.requester_email: to_list.append(booking.requester_email)
    to_list += attendee_emails
    to_list = sorted({e for e in to_list if e and "@" in e})

    if to_list:
        html = f"""
        <h3>ยืนยันการจองห้องประชุม</h3>
        <p><b>ห้อง:</b> {booking.room_id}</p>
        <p><b>หัวข้อ:</b> {booking.subject}</p>
        <p><b>เวลา:</b> {booking.start_time} - {booking.end_time}</p>
        """
        email_svc.send(to=to_list, subject=f"[Meeting] {booking.subject}", html=html)
    return booking

def update_booking(db: Session, booking_id: int, payload: schemas.BookingUpdate) -> models.Booking:
    booking = db.query(models.Booking).get(booking_id)
    if not booking:
        raise HTTPException(404, "ไม่พบรายการจอง")

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(booking, k, v)
    db.commit(); db.refresh(booking)
    return booking
