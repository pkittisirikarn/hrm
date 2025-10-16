# modules/security/perms.py
from typing import List, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy.engine import Engine
from sqlalchemy import text
from .model import AppModule

DEFAULT_ROLES: List[str] = ["ADMIN", "MANAGER", "USER"]

DEFAULT_PERMS: List[Tuple[str, str]] = [
    ("security.manage", "จัดการบทบาทและสิทธิ์"),
    ("employees.view", "ดูข้อมูลพนักงาน"),
    ("employees.edit", "แก้ไขข้อมูลพนักงาน"),
    ("departments.manage", "จัดการแผนก"),
    ("positions.manage", "จัดการตำแหน่ง"),
    ("time.view", "ดูเวลาทำงาน/ลางาน/โอที"),
    ("time.edit", "จัดการบันทึกเวลา/ลางาน/โอที"),
    ("time.leave.request", "เข้าหน้าคำขอลา"),
    ("time.ot.request", "เข้าหน้าคำขอ OT"),
    ("payroll.view", "ดูข้อมูลเงินเดือน"),
    ("payroll.edit", "จัดการโครงสร้าง/รอบ/เอนทรี่เงินเดือน"),
    ("payroll.report.view", "ดูรายงานเงินเดือน"),
    ("meeting.view", "ดูข้อมูลห้องประชุม"),
    ("meeting.manage", "จัดการห้องประชุม"),
    ("recruitment.view", "ดูข้อมูลสรรหา/ผู้สมัคร"),
    ("recruitment.manage", "จัดการผู้สมัคร/ประกาศงาน"),
    ("security.password.change", "เปลี่ยนรหัสผ่านตนเอง"),
]

def ensure_permissions_schema(engine: Engine):
    from sqlalchemy import text as _t
    with engine.begin() as conn:
        conn.execute(_t("""
        CREATE TABLE IF NOT EXISTS security_permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT
        )
        """))
        for code, desc in DEFAULT_PERMS:
            conn.execute(_t(
                "INSERT OR IGNORE INTO security_permissions(code, description) VALUES(:c,:d)"
            ), {"c": code, "d": desc})

def seed_admin_all(engine: Engine):
    from sqlalchemy import text as _t
    try:
        from .permissions_service import ensure_security_tables
        ensure_security_tables(engine)
    except Exception:
        pass

    with engine.begin() as conn:
        for r in ("ADMIN", "MANAGER", "USER"):
            conn.execute(_t("INSERT OR IGNORE INTO security_roles(name) VALUES(:n)"), {"n": r})
        # ให้ ADMIN ได้ทุกสิทธิ์
        conn.execute(_t("""
            INSERT OR IGNORE INTO security_role_permissions(role_id, perm_id)
            SELECT r.id, p.id
            FROM security_roles r, security_permissions p
            WHERE r.name='ADMIN'
        """))

def is_admin_session(session: dict | None) -> bool:
    return ((session or {}).get("role") == "ADMIN")

def has_perm_session(session: dict, code: str) -> bool:
    try:
        if is_admin_session(session):
            return True
        perms = (session or {}).get("perms") or []
        return code in perms
    except Exception:
        return False

# สำหรับ template
def has_perm(session: dict, code: str) -> bool:
    return has_perm_session(session, code)

def compute_user_perms(db: Session, emp_id: int, role_name: str) -> Set[str]:
    codes: Set[str] = set()

    rows = db.execute(text("""
        SELECT p.code
        FROM security_roles r
        JOIN security_role_permissions rp ON rp.role_id = r.id
        JOIN security_permissions p ON p.id = rp.perm_id
        WHERE r.name = :role
    """), {"role": role_name}).scalars().all()
    codes.update(rows)

    extra_roles = db.execute(text("""
        SELECT r.name
        FROM security_user_roles ur
        JOIN security_roles r ON r.id = ur.role_id
        WHERE ur.user_id = :u
    """), {"u": emp_id}).scalars().all()
    for rname in extra_roles:
        rcodes = db.execute(text("""
            SELECT p.code
            FROM security_roles r
            JOIN security_role_permissions rp ON rp.role_id = r.id
            JOIN security_permissions p ON p.id = rp.perm_id
            WHERE r.name = :role
        """), {"role": rname}).scalars().all()
        codes.update(rcodes)

    mod_map = {
        AppModule.EMPLOYEES.value: ("employees.view", "employees.edit"),
        AppModule.PAYROLL.value: ("payroll.view", "payroll.edit"),
        AppModule.MEETING.value: ("meeting.view", "meeting.manage"),
        AppModule.TIME_TRACKING.value: ("time.view", "time.edit"),
        AppModule.RECRUITMENT.value: ("recruitment.view", "recruitment.manage"),
        AppModule.PERSONAL_PROFILE.value: ("personal_profile.view", "personal_profile.edit"),
        AppModule.DASHBOARD.value: ("dashboard.view", "dashboard.view"),
    }
    rows = db.execute(text("""
        SELECT module, can_view, can_edit
        FROM module_permissions
        WHERE employee_id = :u
    """), {"u": emp_id}).mappings().all()
    for r in rows:
        view_code, edit_code = mod_map.get(str(r["module"]).lower(), (None, None))
        if view_code:
            if r["can_view"]: codes.add(view_code)
            else: codes.discard(view_code)
        if edit_code:
            if r["can_edit"]: codes.add(edit_code)
            else: codes.discard(edit_code)

    legacy = db.execute(text("SELECT perm FROM role_permissions WHERE role=:r"),
                        {"r": role_name}).scalars().all()
    codes.update(legacy)

    # กัน None/ว่าง
    return {c for c in codes if isinstance(c, str) and c.strip()}
