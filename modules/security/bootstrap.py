# modules/security/bootstrap.py
from datetime import date
from sqlalchemy import text, inspect
from database.connection import SessionLocal, engine
from modules.security.passwords import hash_password


def _tables():
    insp = inspect(engine)
    try:
        return set(insp.get_table_names())
    except Exception:
        return set()


def _has_column(table: str, col: str) -> bool:
    insp = inspect(engine)
    try:
        return any(c["name"] == col for c in insp.get_columns(table))
    except Exception:
        return False


def ensure_default_admin():
    """
    สร้างแอดมินเริ่มต้น (admin / admin) ถ้ายังไม่มี
    - สร้าง Department/Position เริ่มต้นเมื่อจำเป็น
    - เติมคอลัมน์ NOT NULL ที่ตาราง employees ต้องการให้ครบ
    - ถ้ามี employees.password_hash จะตั้งรหัสเริ่มต้นให้ด้วย
    """
    tbls = _tables()
    with SessionLocal() as db:
        # 1) ensure base dept/position
        dept_id = None
        pos_id = None

        if "departments" in tbls:
            dept_id = db.execute(
                text("SELECT id FROM departments WHERE name=:n LIMIT 1"),
                {"n": "General"},
            ).scalar()
            if not dept_id:
                # แทรก department เริ่มต้น
                db.execute(
                    text("INSERT INTO departments (name) VALUES (:n)"),
                    {"n": "General"},
                )
                dept_id = db.execute(
                    text("SELECT id FROM departments WHERE name=:n LIMIT 1"),
                    {"n": "General"},
                ).scalar()

        if "positions" in tbls:
            pos_id = db.execute(
                text("SELECT id FROM positions WHERE name=:n LIMIT 1"),
                {"n": "Administrator"},
            ).scalar()
            if not pos_id:
                if _has_column("positions", "department_id") and dept_id is not None:
                    db.execute(
                        text(
                            "INSERT INTO positions (name, department_id) "
                            "VALUES (:n, :d)"
                        ),
                        {"n": "Administrator", "d": dept_id},
                    )
                else:
                    db.execute(
                        text("INSERT INTO positions (name) VALUES (:n)"),
                        {"n": "Administrator"},
                    )
                pos_id = db.execute(
                    text("SELECT id FROM positions WHERE name=:n LIMIT 1"),
                    {"n": "Administrator"},
                ).scalar()

        # 2) if admin exists -> nothing to do
        eid = db.execute(
            text("SELECT id FROM employees WHERE email=:e LIMIT 1"),
            {"e": "admin@hrm.local"},
        ).scalar()
        if eid:
            return  # มีอยู่แล้ว

        # 3) build insert payload for employees (เติมคอลัมน์ที่เป็น NOT NULL ให้ครบ)
        # ค่า default แบบปลอดภัยกับ constraint ส่วนใหญ่
        base_payload = {
            "employee_id_number": "ADMIN",
            "first_name": "Admin",
            "last_name": "",
            "email": "admin@hrm.local",
            "employee_status": "ACTIVE",
            "date_of_birth": date(2000, 1, 1),  # กัน NOT NULL
            "hire_date": date.today(),          # กัน NOT NULL
            "address": "",
        }

        cols = ["employee_id_number", "first_name", "last_name",
                "email", "employee_status", "date_of_birth",
                "hire_date", "address"]

        # ออปชันเสริม: role
        if _has_column("employees", "role"):
            cols.append("role")
            base_payload["role"] = "ADMIN"

        # NOT NULL: department_id / position_id (ถ้ามีคอลัมน์และมีค่า id)
        if _has_column("employees", "department_id"):
            if dept_id is None:
                # ถ้าคอลัมน์มีและมัก NOT NULL ต้องมีค่าจริง ๆ
                # จะลองหยิบ department อะไรก็ได้ 1 รายการ
                dept_id = db.execute(
                    text("SELECT id FROM departments ORDER BY id LIMIT 1")
                ).scalar()
                if dept_id is None:
                    # เผื่อกรณีไม่มีตาราง departments แต่คอลัมน์ยังอยู่ (ไม่น่าเกิด แต่กันไว้)
                    # ให้เติมเป็น 1 แล้วคุณค่อยแก้ภายหลัง (หลีกเลี่ยง error ตอนบูต)
                    dept_id = 1
            cols.append("department_id")
            base_payload["department_id"] = dept_id

        if _has_column("employees", "position_id"):
            if pos_id is None:
                pos_id = db.execute(
                    text("SELECT id FROM positions ORDER BY id LIMIT 1")
                ).scalar()
                if pos_id is None:
                    pos_id = 1
            cols.append("position_id")
            base_payload["position_id"] = pos_id

        # 4) insert employee admin
        placeholders = ", ".join([f":{k}" for k in cols])
        sql = f"INSERT INTO employees ({', '.join(cols)}) VALUES ({placeholders})"
        db.execute(text(sql), base_payload)

        # id ใหม่
        eid = db.execute(
            text("SELECT id FROM employees WHERE email=:e"),
            {"e": "admin@hrm.local"},
        ).scalar()

        # 5) set default password if employees.password_hash exists
        if _has_column("employees", "password_hash"):
            db.execute(
                text("UPDATE employees SET password_hash=:ph WHERE id=:id"),
                {"ph": hash_password("admin"), "id": eid},
            )

        db.commit()
