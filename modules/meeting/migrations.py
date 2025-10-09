# modules/meeting/migrations.py
from sqlalchemy import inspect, text

def migrate_meeting_rooms_columns(engine):
    with engine.begin() as conn:
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("meeting_rooms")}

        if "notes" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN notes TEXT"))
        if "is_active" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.execute(text("UPDATE meeting_rooms SET is_active = 1 WHERE is_active IS NULL"))

        # NEW
        if "image_url" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN image_url VARCHAR(300)"))
        if "contact_name" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN contact_name VARCHAR(120)"))
        if "coordinator_employee_id" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN coordinator_employee_id INTEGER"))
        if "coordinator_email" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN coordinator_email VARCHAR(200)"))
        if "approval_status" not in cols:
            conn.execute(text("ALTER TABLE meeting_rooms ADD COLUMN approval_status VARCHAR(20) DEFAULT 'Approved'"))

