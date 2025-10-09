"""init meeting tables matching ORM models"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "20251003_meeting_init"
down_revision = None  # ถ้ามีรีวิชันก่อนหน้าในโปรเจ็กต์ ให้ใส่รหัสนั้นแทน
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "meeting_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
    )

    op.create_table(
        "meeting_bookings",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("meeting_rooms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("requester_email", sa.String(200), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False, index=True),
        sa.Column("end_time", sa.DateTime(), nullable=False, index=True),
        sa.Column("status", sa.Enum("Pending", "Booked", "Cancelled", name="bookingstatus"), nullable=False, server_default="Booked"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_meeting_bookings_room_time", "meeting_bookings", ["room_id", "start_time", "end_time"])

    op.create_table(
        "meeting_booking_attendees",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("booking_id", sa.Integer(), sa.ForeignKey("meeting_bookings.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("attendee_name", sa.String(200), nullable=True),
        sa.Column("attendee_email", sa.String(200), nullable=True),
    )

def downgrade():
    op.drop_table("meeting_booking_attendees")
    op.drop_index("ix_meeting_bookings_room_time", table_name="meeting_bookings")
    op.drop_table("meeting_bookings")
    op.drop_table("meeting_rooms")
