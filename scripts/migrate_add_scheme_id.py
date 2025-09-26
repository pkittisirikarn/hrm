# scripts/migrate_fix_payroll_runs_columns.py
# รันครั้งเดียวเพื่อให้ตาราง payroll_runs มีคอลัมน์ที่โค้ดต้องใช้

# ถ้ารันด้วย "python scripts\..." ให้ปลดคอมเมนต์ 3 บรรทัดนี้
# import sys, os
# sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import inspect, text
from database.connection import engine, SessionLocal
from modules.payroll import services

def add_column_if_missing(conn, table: str, col: str, ddl: str):
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns(table)]
    if col not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        print(f"✅ Added column '{col}' to {table}")
    else:
        print(f"📦 Column '{col}' already exists on {table}")

def main():
    # 1) เพิ่มคอลัมน์ที่จำเป็น
    with engine.begin() as conn:
        add_column_if_missing(conn, "payroll_runs", "scheme_id",    "INTEGER")
        add_column_if_missing(conn, "payroll_runs", "period_start", "DATE")
        add_column_if_missing(conn, "payroll_runs", "period_end",   "DATE")
        add_column_if_missing(conn, "payroll_runs", "created_at",   "DATETIME")

        # backfill period_* จากคอลัมน์เก่า ถ้ามี (หรือใช้วันที่ created_at)
        insp = inspect(engine)
        cols = [c["name"] for c in insp.get_columns("payroll_runs")]

        if "pay_period_start" in cols:
            conn.execute(text("""
                UPDATE payroll_runs
                SET period_start = pay_period_start
                WHERE period_start IS NULL
            """))
        else:
            conn.execute(text("""
                UPDATE payroll_runs
                SET period_start = COALESCE(period_start, DATE(COALESCE(created_at, CURRENT_TIMESTAMP)))
            """))

        if "pay_period_end" in cols:
            conn.execute(text("""
                UPDATE payroll_runs
                SET period_end = pay_period_end
                WHERE period_end IS NULL
            """))
        else:
            conn.execute(text("""
                UPDATE payroll_runs
                SET period_end = COALESCE(period_end, DATE(COALESCE(created_at, CURRENT_TIMESTAMP)))
            """))

        # backfill created_at ถ้ายังว่าง
        conn.execute(text("""
            UPDATE payroll_runs
            SET created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
        """))

    # 2) ให้แน่ใจว่ามี Default Scheme และอัปเดต scheme_id
    with SessionLocal() as db:
        scheme = services.ensure_default_scheme_and_formulas(db)
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE payroll_runs SET scheme_id = :sid WHERE scheme_id IS NULL"),
                {"sid": scheme.id},
            )
        print(f"✅ Backfilled payroll_runs.scheme_id -> {scheme.id}")

    print("🎉 Migration finished.")

if __name__ == "__main__":
    main()
