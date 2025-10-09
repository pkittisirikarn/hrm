from sqlalchemy import inspect, text
from database.connection import engine, Base
from .models import Candidate, Interview, CandidateFile


def ensure_tables():
    # สร้างเฉพาะตารางของโมดูลนี้ (ไม่กระทบตารางอื่น)
    Candidate.__table__.create(bind=engine, checkfirst=True)
    Interview.__table__.create(bind=engine, checkfirst=True)
    CandidateFile.__table__.create(bind=engine, checkfirst=True)

def has_column(table: str, column: str) -> bool:
    insp = inspect(engine)
    try:
        cols = [c['name'] for c in insp.get_columns(table)]
    except Exception:
        cols = []
    return column in cols


def add_column(table: str, ddl: str):
    # ตัวอย่าง ddl: "stage_updated_at TIMESTAMP"
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))


def run():
    ensure_tables()
    # เพิ่มคอลัมน์ใหม่สำหรับโปรเจกต์ที่มีตารางแล้ว
    if not has_column('candidates', 'first_name'):
        add_column('candidates', 'first_name VARCHAR(120)')
    if not has_column('candidates', 'last_name'):
        add_column('candidates', 'last_name VARCHAR(120)')
    if not has_column('candidates', 'full_name'):
        add_column('candidates', 'full_name VARCHAR(200)')
    if not has_column('candidates', 'education'):
        add_column('candidates', 'education VARCHAR(200)')
    if not has_column('candidates', 'photo_url'):
        add_column('candidates', 'photo_url TEXT')


if __name__ == "__main__":
    run()
    print("[recruitment] migrations ensured")