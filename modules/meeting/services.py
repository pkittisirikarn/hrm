# modules/meeting/services.py
from __future__ import annotations

from datetime import datetime, date, time
from typing import List, Optional, Dict
from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from modules.meeting import models, schemas
from modules.common.email_service import EmailService
from config.settings import email_settings
from modules.data_management.models import Employee as DMEmployee

email_svc = EmailService(email_settings)

# ----------------------------- helpers -----------------------------
def _emails_from_employee_ids(db: Session, employee_ids: Optional[List[int]]) -> List[str]:
    if not employee_ids:
        return []
    rows = db.query(DMEmployee).filter(DMEmployee.id.in_(employee_ids)).all()
    return [(r.email or "").strip() for r in rows if (r.email or "").strip()]

def _get_room_coordinator_emails(db: Session, room: models.MeetingRoom) -> List[str]:
    emails: List[str] = []
    if room.coordinator_employee_id:
        emp = db.get(DMEmployee, room.coordinator_employee_id)
        if emp and (emp.email or "").strip():
            emails.append(emp.email.strip())
    if (room.coordinator_email or "").strip():
        emails.append(room.coordinator_email.strip())
    return sorted({e for e in emails if "@" in e})

# -------------------------- overlap guard --------------------------
def assert_no_overlap(
    db: Session,
    room_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: Optional[int] = None,
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
        raise HTTPException(status_code=400, detail="ช่วงเวลานี้ถูกจองแล้ว (ห้องเดียวกันและเวลาซ้อนทับ)")

# ----------------------------- email ------------------------------
def _format_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")

def send_booking_email(db: Session, booking: models.Booking, extra_to: Optional[List[str]] = None) -> None:
    room = db.get(models.MeetingRoom, booking.room_id)
    if not room:
        return

    to_list: List[str] = []
    if booking.requester_email:
        to_list.append(booking.requester_email)

    # from attendees (relationship)
    try:
        for a in (booking.attendees or []):
            if (a.attendee_email or "").strip():
                to_list.append(a.attendee_email.strip())
            elif a.employee_id:
                emp = db.get(DMEmployee, a.employee_id)
                if emp and (emp.email or "").strip():
                    to_list.append(emp.email.strip())
    except Exception:
        pass

    to_list += _get_room_coordinator_emails(db, room)
    if extra_to:
        to_list += extra_to
    to_list = sorted({e for e in to_list if e and "@" in e})
    if not to_list:
        return

    attendee_lines: List[str] = []
    try:
        for a in (booking.attendees or []):
            label = (a.attendee_name or "") or (a.attendee_email or "")
            if a.employee_id and not label:
                emp = db.get(DMEmployee, a.employee_id)
                label = (f"{(emp.first_name or '').strip()} {(emp.last_name or '').strip()}").strip() or (emp.email or "")
            if label:
                attendee_lines.append(label)
    except Exception:
        pass
    attendees_html = "<ul>" + "".join([f"<li>{line}</li>" for line in attendee_lines]) + "</ul>" if attendee_lines else "<p>-</p>"

    subj = f"[Meeting {booking.status.name}] {booking.subject}"
    html = f"""
    <h3>รายละเอียดการจองห้องประชุม</h3>
    <p><b>สถานะ:</b> {booking.status.name}</p>
    <p><b>ห้อง:</b> {room.name}</p>
    <p><b>หัวข้อ:</b> {booking.subject}</p>
    <p><b>ผู้ติดต่อ:</b> {getattr(booking, 'contact_person', None) or '-'}</p>
    <p><b>เวลา:</b> {_format_dt(booking.start_time)} - {_format_dt(booking.end_time)}</p>
    <p><b>ผู้จอง:</b> {booking.requester_email or '-'}</p>
    <p><b>ผู้เข้าร่วม:</b></p>
    {attendees_html}
    """
    email_svc.send(to=to_list, subject=subj, html=html)

# --------- create/update booking (save attendees + email) ----------
def create_booking(db: Session, payload: schemas.BookingCreate) -> models.Booking:
    room = db.get(models.MeetingRoom, payload.room_id)
    if not room or not room.is_active:
        raise HTTPException(status_code=400, detail="ห้องไม่พร้อมใช้งาน")

    # status จาก payload (default PENDING)
    status_model = models.BookingStatus.PENDING
    if getattr(payload, "status", None):
        status_model = getattr(models.BookingStatus, payload.status.name, models.BookingStatus.PENDING)

    booking = models.Booking(
        room_id=payload.room_id,
        subject=payload.subject,
        requester_email=(payload.requester_email or "").strip() or None,
        contact_person=(getattr(payload, "contact_person", None) or "").strip() or None,
        start_time=payload.start_time,
        end_time=payload.end_time,
        notes=payload.notes,
        status=status_model,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # บันทึกผู้เข้าร่วม
    attendee_count = 0
    if getattr(payload, "attendee_employee_ids", None):
        emps = db.query(DMEmployee).filter(DMEmployee.id.in_(payload.attendee_employee_ids)).all()
        for emp in emps:
            full_name = f"{emp.first_name or ''} {emp.last_name or ''}".strip()
            db.add(models.BookingAttendee(
                booking_id=booking.id,
                employee_id=emp.id,
                attendee_name=full_name or None,
                attendee_email=(emp.email or None),
            ))
            attendee_count += 1
        # เฉพาะกรณีที่ model มีคอลัมน์นี้
        if hasattr(booking, "attendee_count"):
            booking.attendee_count = attendee_count
        db.commit()

    # ส่งเมลครั้งแรก (แนบรายชื่อจาก employee_ids ด้วย)
    extra = _emails_from_employee_ids(db, getattr(payload, "attendee_employee_ids", None))
    send_booking_email(db, booking, extra_to=extra)

    # โหลดความสัมพันธ์ให้ response
    booking = (
        db.query(models.Booking)
        .options(joinedload(models.Booking.attendees), joinedload(models.Booking.room))
        .get(booking.id)
    )
    return booking

def update_booking(db: Session, booking_id: int, payload: schemas.BookingUpdate) -> models.Booking:
    booking = db.get(models.Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจอง")

    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] is not None:
        data["status"] = getattr(models.BookingStatus, payload.status.name)

    # เผื่อ schema ยังไม่มี contact_person / attendee_count ก็ไม่ล่ม
    for k, v in data.items():
        if hasattr(booking, k):
            setattr(booking, k, v)

    db.commit()
    db.refresh(booking)
    return booking

# ------------------------- dashboard summary -----------------------
def _hours_between(s: datetime, e: datetime) -> float:
    return max(0.0, (e - s).total_seconds() / 3600.0)

def booking_summary(db: Session, date_from: date, date_to: date) -> Dict:
    start_dt = datetime.combine(date_from, time.min)
    end_dt = datetime.combine(date_to, time.max)

    q = (
        db.query(models.Booking)
        .filter(models.Booking.start_time <= end_dt, models.Booking.end_time >= start_dt)
        .filter(models.Booking.status != models.BookingStatus.CANCELLED)
    )
    bookings = q.all()

    total_rooms = db.query(func.count(models.MeetingRoom.id)).scalar() or 0
    total_bookings = len(bookings)
    total_hours = 0.0

    by_room = defaultdict(lambda: {"count": 0, "hours": 0.0})
    by_coord = defaultdict(lambda: {"count": 0, "hours": 0.0})

    for b in bookings:
        s = max(b.start_time, start_dt)
        e = min(b.end_time, end_dt)
        hrs = _hours_between(s, e)
        total_hours += hrs

        room_name = getattr(b.room, "name", f"Room#{b.room_id}") if hasattr(b, "room") else f"Room#{b.room_id}"
        by_room[room_name]["count"] += 1
        by_room[room_name]["hours"] += hrs

        coord_key = "-"
        try:
            room = b.room
            if room and room.coordinator_employee_id:
                emp = db.get(DMEmployee, room.coordinator_employee_id)
                if emp:
                    coord_key = (f"{(emp.first_name or '').strip()} {(emp.last_name or '').strip()}").strip() or (emp.email or "-")
        except Exception:
            pass
        by_coord[coord_key]["count"] += 1
        by_coord[coord_key]["hours"] += hrs

    days = (date_to - date_from).days + 1
    denom = float(max(1, days) * 8 * max(1, total_rooms))
    util = (total_hours / denom * 100.0) if denom > 0 else 0.0

    top_rooms = [
        {"room_name": k, "count": v["count"], "hours": v["hours"]}
        for k, v in sorted(by_room.items(), key=lambda x: (-x[1]["count"], -x[1]["hours"]))[:10]
    ]
    by_coordinator = [
        {"coordinator_name": k, "count": v["count"], "hours": v["hours"]}
        for k, v in sorted(by_coord.items(), key=lambda x: (-x[1]["count"], -x[1]["hours"]))
    ]

    return {
        "total_rooms": total_rooms,
        "total_bookings": total_bookings,
        "total_hours": round(total_hours, 1),
        "utilization_pct": round(util, 1),
        "top_rooms": top_rooms,
        "by_coordinator": by_coordinator,
    }
