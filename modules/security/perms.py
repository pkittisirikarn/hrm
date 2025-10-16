# modules/security/perms.py
from typing import List, Tuple, Set
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# ---- ค่าเริ่มต้น ----
DEFAULT_ROLES: List[str] = ["ADMIN", "MANAGER", "USER"]

# code, description
DEFAULT_PERMS: List[Tuple[str, str]] = [
    ("security.manage", "จัดการบทบาทและสิทธิ์"),
    ("employees.view", "ดูข้อมูลพนักงาน"),
    ("employees.edit", "แก้ไขข้อมูลพนักงาน"),
    ("departments.manage", "จัดการแผนก"),
    ("positions.manage", "จัดการตำแหน่ง"),
    ("time.view", "ดูเวลาทำงาน/ลางาน/โอที"),
    ("time.edit", "จัดการบันทึกเวลา/ลางาน/โอที"),
    ("payroll.view", "ดูข้อมูลเงินเดือน"),
    ("payroll.edit", "จัดการโครงสร้าง/รอบ/เอนทรี่เงินเดือน"),
    ("meeting.manage", "จัดการห้องประชุม"),
    ("recruitment.manage", "จัดการผู้สมัคร/ประกาศงาน"),
]

# สร้างตาราง permissions (ซ้ำกับ ensure_security_tables ก็ไม่เป็นไร ปลอดภัย)
def ensure_permissions_schema(engine):
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT
        )
        """))

# ให้ ADMIN มีสิทธิ์จัดการความปลอดภัย (และ ensure ตารางก่อน)
def seed_admin_all(engine):
    # กันพลาดเรื่องลำดับ: ถ้ายังไม่มีตาราง ให้สร้างก่อน
    try:
        from .permissions_service import ensure_security_tables
        ensure_security_tables(engine)
    except Exception:
        pass

    with engine.begin() as conn:
        # roles หลัก
        for r in ("ADMIN", "MANAGER", "USER"):
            conn.execute(text("INSERT OR IGNORE INTO security_roles(name) VALUES(:n)"), {"n": r})
        # perm หลักอย่างน้อย 1 ตัว
        conn.execute(text("""
            INSERT OR IGNORE INTO security_permissions(code, description)
            VALUES('security.manage','Manage roles & permissions')
        """))
        # map ADMIN -> security.manage
        conn.execute(text("""
            INSERT OR IGNORE INTO security_role_permissions(role_id, perm_id)
            SELECT r.id, p.id
            FROM security_roles r, security_permissions p
            WHERE r.name='ADMIN' AND p.code='security.manage'
        """))

# ---- รวมสิทธิ์ของผู้ใช้ตาม role (รวมทั้ง id-based และ legacy) ----
def compute_user_perms(db: Session, emp_id: int, role_name: str) -> Set[str]:
    codes: Set[str] = set()

    # จาก security_role_permissions -> security_permissions
    rows = db.execute(text("""
        SELECT p.code
        FROM security_roles r
        JOIN security_role_permissions rp ON rp.role_id = r.id
        JOIN security_permissions p ON p.id = rp.perm_id
        WHERE r.name = :role
    """), {"role": role_name}).scalars().all()
    codes.update(rows)

    # จากตาราง legacy role_permissions
    legacy = db.execute(text("SELECT perm FROM role_permissions WHERE role=:r"), {"r": role_name}).scalars().all()
    codes.update(legacy)

    return codes

# ---- ตัวช่วยให้ template เรียก ----
def has_perm(session: dict, code: str) -> bool:
    try:
        perms = session.get("perms") or []
        return code in perms
    except Exception:
        return False
