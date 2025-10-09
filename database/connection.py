# database/connection.py
import os
from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from database.base import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hrm.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------- small helpers ----------
def _cols(insp, table: str) -> set[str]:
    """return set of column names for a table"""
    return {c["name"] for c in insp.get_columns(table)}

def _ensure_column(conn, table: str, column: str, ddl: str):
    """ALTER TABLE ... ADD COLUMN ... if not exists (sqlite style)"""
    insp = inspect(conn)
    if column not in _cols(insp, table):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        print(f"✓ Added column {table}.{column}")

# ---------- lightweight migrations ----------
def ensure_leave_balances_table_and_columns(engine):
    insp = inspect(engine)
    tables = set(insp.get_table_names())

    if "leave_balances" not in tables:
        # ... (ตามที่คุณมีอยู่)
        pass
    else:
        with engine.begin() as conn:
            # เพิ่มคอลัมน์ปัจจุบัน
            for col in ("opening", "accrued", "used", "adjusted", "carry_in"):
                _ensure_column(conn, "leave_balances", col, "REAL DEFAULT 0.0")

            # ถ้ามี legacy 'opening_quota' แต่ยังไม่มี 'opening' → เพิ่มแล้วคัดลอกค่า
            legacy_cols = _cols(inspect(conn), "leave_balances")
            if "opening_quota" in legacy_cols and "opening" in legacy_cols:
                # copy เฉพาะแถวที่ opening ยังเป็น 0
                conn.execute(text("""
                    UPDATE leave_balances
                    SET opening = COALESCE(opening, 0.0) + COALESCE(opening_quota, 0.0)
                    WHERE COALESCE(opening, 0.0) = 0.0
                """))
        print("✓ leave_balances table exists / columns ensured.")

def ensure_leave_types_columns(engine):
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("leave_types")}
    sqls = []
    if "annual_quota" not in cols:
        sqls.append("ALTER TABLE leave_types ADD COLUMN annual_quota REAL DEFAULT 0.0")
    if "affects_balance" not in cols:
        sqls.append("ALTER TABLE leave_types ADD COLUMN affects_balance INTEGER DEFAULT 1")
    # ✅ ใหม่
    if "accrue_per_year" not in cols:
        sqls.append("ALTER TABLE leave_types ADD COLUMN accrue_per_year REAL DEFAULT 0.0")
    if "max_quota" not in cols:
        sqls.append("ALTER TABLE leave_types ADD COLUMN max_quota REAL DEFAULT 0.0")

    if sqls:
        with engine.begin() as conn:
            for s in sqls:
                conn.execute(text(s))
        print("✓ Migrated leave_types: ensured annual_quota / affects_balance / accrue_per_year / max_quota.")
    else:
        print("✓ Migrated leave_types: columns already present.")

# ---------- session ----------
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- bootstrap ----------
def create_all_tables() -> None:
    # ต้อง import โมเดลก่อนสร้างตาราง
    from modules.data_management import models as _dm_models  # noqa: F401
    from modules.payroll         import models as _pr_models  # noqa: F401
    from modules.time_tracking   import models as _tt_models  # noqa: F401
    from modules.meeting         import models as _m_models   # noqa: F401

    Base.metadata.create_all(bind=engine)

    # ไลท์ไมเกรชัน
    ensure_leave_types_columns(engine)
    ensure_leave_balances_table_and_columns(engine)
