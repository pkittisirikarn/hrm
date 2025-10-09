# modules/meeting/migrations.py
from __future__ import annotations

from typing import Set
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from database.connection import engine as default_engine


def _get_columns(engine: Engine, table: str) -> Set[str]:
    """
    คืนชุดชื่อคอลัมน์ของตารางแบบ cross-DB:
    - ปกติ: ใช้ SQLAlchemy inspector
    - SQLite: fallback เป็น PRAGMA ถ้าจำเป็น
    """
    insp = inspect(engine)
    try:
        cols = {c["name"] for c in insp.get_columns(table)}
        if cols:
            return cols
    except Exception:
        pass

    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            return {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
    return set()


# -------------------------------------------------------------------
# meeting_rooms
# -------------------------------------------------------------------
def migrate_meeting_rooms_columns(engine: Engine = default_engine) -> None:
    """
    เพิ่มเฉพาะคอลัมน์ที่ยังใช้อยู่ในชุดล่าสุด
    - notes, is_active
    - image_url, coordinator_employee_id, coordinator_email
    - approval_status (string; Pending/Approved/Rejected)
    หมายเหตุ: ไม่เพิ่ม contact_name อีกต่อไป
    """
    with engine.begin() as conn:
        cols = _get_columns(engine, "meeting_rooms")

        # เดิม
        if "notes" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN notes TEXT"))
        if "is_active" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.execute(text("UPDATE meeting_rooms SET is_active = 1 WHERE is_active IS NULL"))

        # ใช้งานจริงปัจจุบัน
        if "image_url" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN image_url VARCHAR(300)"))
        if "coordinator_employee_id" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN coordinator_employee_id INTEGER"))
        if "coordinator_email" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN coordinator_email VARCHAR(200)"))
        if "approval_status" not in cols:
            conn.execute(
                text("ALTER TABLE meeting_rooms ADD COLUMN approval_status VARCHAR(20) DEFAULT 'Approved'")
            )
        # ไม่เพิ่ม contact_name แล้ว (ปล่อยไว้หากมีอยู่เดิม)


# -------------------------------------------------------------------
# meeting_bookings
# -------------------------------------------------------------------
def ensure_meeting_bookings_columns(engine: Engine = default_engine) -> None:
    """
    เพิ่มคอลัมน์ใหม่ตามชุดล่าสุด:
    - contact_person: ผู้ติดต่อของ "การจอง"
    - attendee_count: เก็บจำนวนผู้เข้าร่วมแบบ denormalized (ออปชัน แต่มีประโยชน์กับตาราง)
    """
    with engine.begin() as conn:
        cols = _get_columns(engine, "meeting_bookings")

        # ผู้ติดต่อสำหรับการจอง
        if "contact_person" not in cols:
            conn.execute(text("ALTER TABLE meeting_bookings ADD COLUMN contact_person VARCHAR(200)"))
            print("✓ Migrated meeting_bookings: added contact_person")

        # จำนวนผู้เข้าร่วม (denormalized)
        if "attendee_count" not in cols:
            conn.execute(text("ALTER TABLE meeting_bookings ADD COLUMN attendee_count INTEGER DEFAULT 0"))
            # backfill หากมีตาราง attendees แล้ว
            try:
                conn.execute(text("""
                    UPDATE meeting_bookings
                    SET attendee_count = (
                        SELECT COUNT(*)
                        FROM meeting_booking_attendees a
                        WHERE a.booking_id = meeting_bookings.id
                    )
                """))
            except Exception:
                # ถ้ายังไม่มีตาราง attendees ให้ข้ามไป
                pass
            print("✓ Migrated meeting_bookings: added attendee_count")


# -------------------------------------------------------------------
# Entry for app startup
# -------------------------------------------------------------------
def run_startup_migrations(engine: Engine = default_engine) -> None:
    """
    เรียกฟังก์ชันนี้ตอนแอปสตาร์ท (หลัง create_all)
    """
    migrate_meeting_rooms_columns(engine)
    ensure_meeting_bookings_columns(engine)
