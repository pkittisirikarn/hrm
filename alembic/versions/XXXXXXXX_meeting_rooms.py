"""meeting rooms module (single-image)"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "XXXXXXXX_meeting_rooms"
down_revision = None  # ใส่เลข revision ก่อนหน้าในโปรเจกต์คุณ
branch_labels = None
depends_on = None


def upgrade():
    # meeting_rooms
    op.create_table(
        "meeting_rooms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=True, unique=True, index=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )

    # meeting_amenities
    op.create_table(
        "meeting_amenities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
    )

    # room_amenity (M2M)
    op.create_table(
        "room_amenity",
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("meeting_rooms.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("amenity_id", sa.Integer(), sa.ForeignKey("meeting_amenities.id", ondelete="CASCADE"), primary_key=True),
    )

    # room_bookings
    op.create_table(
        "room_bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("meeting_rooms.id", ondelete="CASCADE"), nullable=False, index=True),

        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False, index=True),
        sa.Column("end_time", sa.DateTime(), nullable=False, index=True),
        sa.Column("participants", sa.Integer(), nullable=False, server_default="0"),

        sa.Column("booked_by_user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("booked_by_name", sa.String(200), nullable=False),
        sa.Column("booked_by_email", sa.String(255), nullable=True, index=True),

        sa.Column("coordinator_user_id", sa.Integer(), nullable=True, index=True),
        sa.Column("coordinator_name", sa.String(200), nullable=True),
        sa.Column("coordinator_email", sa.String(255), nullable=True, index=True),

        sa.Column("contact_name", sa.String(200), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True, index=True),

        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # ดัชนีเสริม สำหรับค้นหาช่วงเวลาทับซ้อน/แดชบอร์ด
    op.create_index("ix_room_bookings_room_time", "room_bookings", ["room_id", "start_time", "end_time"])
    op.create_index("ix_meeting_rooms_active", "meeting_rooms", ["is_active"])


def downgrade():
    op.drop_index("ix_meeting_rooms_active", table_name="meeting_rooms")
    op.drop_index("ix_room_bookings_room_time", table_name="room_bookings")
    op.drop_table("room_bookings")
    op.drop_table("room_amenity")
    op.drop_table("meeting_amenities")
    op.drop_table("meeting_rooms")
