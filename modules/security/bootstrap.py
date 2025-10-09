# modules/security/bootstrap.py
from database.connection import SessionLocal
from sqlalchemy import inspect, text
from modules.data_management.models import Employee
from modules.security.passwords import hash_password  # PBKDF2 (werkzeug / hashlib)

def _ensure_column(db, table: str, column: str, ddl_sql: str):
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns(table)}
    if column not in cols:
        db.execute(text(ddl_sql))
        db.commit()
        print(f"✓ Added column {table}.{column}")

def _pick_unique_emp_no(db) -> str:
    """
    สร้าง employee_id_number ที่ไม่ซ้ำในตาราง employees
    ลองค่า default ง่าย ๆ ก่อน แล้วค่อยรัน ADMIN-001, ADMIN-002, ...
    """
    candidates = ["ADMIN", "ADM-0001", "EMP-ADMIN"]
    for cand in candidates:
        row = db.execute(
            text("SELECT 1 FROM employees WHERE employee_id_number = :v LIMIT 1"),
            {"v": cand},
        ).first()
        if not row:
            return cand
    i = 1
    while True:
        cand = f"ADMIN-{i:03d}"
        row = db.execute(
            text("SELECT 1 FROM employees WHERE employee_id_number = :v LIMIT 1"),
            {"v": cand},
        ).first()
        if not row:
            return cand
        i += 1

def ensure_default_admin():
    """
    ถ้ายังไม่มีผู้ใช้ admin → สร้าง admin@hrm.local / admin
    - ใส่เฉพาะฟิลด์ที่มีอยู่จริงในตาราง
    - ถ้า employee_id_number เป็น NOT NULL → ใส่ค่าอัตโนมัติแบบไม่ซ้ำ
    - ถ้าไม่มี password_hash → เพิ่มคอลัมน์ให้อัตโนมัติ
    """
    email = "admin@hrm.local"
    with SessionLocal() as db:
        # ensure มีคอลัมน์สำหรับเก็บรหัสผ่าน
        _ensure_column(
            db, "employees", "password_hash",
            "ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255)"
        )

        insp = inspect(db.bind)
        cols_meta = {c["name"]: c for c in insp.get_columns("employees")}
        cols = set(cols_meta.keys())

        user = db.query(Employee).filter(Employee.email == email).first()
        if not user:
            payload = {}
            if "first_name" in cols: payload["first_name"] = "Admin"
            if "last_name"  in cols: payload["last_name"]  = ""
            if "email"      in cols: payload["email"]      = email

            # ถ้า employee_id_number เป็น NOT NULL → ใส่ค่าอัตโนมัติ
            if "employee_id_number" in cols and not cols_meta["employee_id_number"].get("nullable", True):
                payload["employee_id_number"] = _pick_unique_emp_no(db)

            # บาง schema บังคับ status → ตั้ง ACTIVE ให้ (ถ้ามีคอลัมน์)
            if "employee_status" in cols and not cols_meta["employee_status"].get("nullable", True):
                payload.setdefault("employee_status", "ACTIVE")

            user = Employee(**payload)
            user.password_hash = hash_password("admin")
            db.add(user)
            db.commit()
            print("✓ Seeded default admin account: admin@hrm.local / admin")
        else:
            if not getattr(user, "password_hash", None):
                user.password_hash = hash_password("admin")
                db.add(user); db.commit()
                print("✓ Ensured default admin password")
