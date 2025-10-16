# modules/security/permissions_service.py
from sqlalchemy import text
from sqlalchemy.orm import Session
from .perms import DEFAULT_PERMS

# --------- สร้างตาราง Security ทั้งหมด (id-based) ----------
def ensure_security_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_roles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT
        );"""))
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_role_permissions(
            role_id INTEGER NOT NULL,
            perm_id INTEGER NOT NULL,
            UNIQUE(role_id, perm_id)
        );"""))

# --------- ฟังก์ชันที่ routes เรียกใช้ ----------
def list_roles(db: Session):
    return db.execute(text("SELECT id, name FROM security_roles ORDER BY id")).mappings().all()

def list_permissions(db):
    return db.execute(
        text("SELECT id, code, description FROM security_permissions ORDER BY code")
    ).mappings().all()
    
def role_permission_ids(db: Session, role_id: int):
    rows = db.execute(text("SELECT perm_id FROM security_role_permissions WHERE role_id=:r"), {"r": role_id}).scalars().all()
    return list(rows)

def set_role_permission(db: Session, role_id: int, perm_id: int, enabled: bool):
    if enabled:
        db.execute(text("""
            INSERT OR IGNORE INTO security_role_permissions(role_id, perm_id)
            VALUES(:r, :p)
        """), {"r": role_id, "p": perm_id})
    else:
        db.execute(text("""
            DELETE FROM security_role_permissions
            WHERE role_id=:r AND perm_id=:p
        """), {"r": role_id, "p": perm_id})
    db.commit()

def list_user_roles(db: Session, user_id: int):
    return db.execute(text("SELECT role_id FROM security_user_roles WHERE user_id=:u"), {"u": user_id}).scalars().all()

def set_user_role(db: Session, user_id: int, role_id: int, enabled: bool):
    if enabled:
        db.execute(text("""
            INSERT OR IGNORE INTO security_user_roles(user_id, role_id)
            VALUES(:u, :r)
        """), {"u": user_id, "r": role_id})
    else:
        db.execute(text("""
            DELETE FROM security_user_roles WHERE user_id=:u AND role_id=:r
        """), {"u": user_id, "r": role_id})
    db.commit()

# seed mapping เริ่มต้นแบบเบา ๆ (ไม่บังคับว่าต้องมี perms ทั้งหมด)
def seed_default_roles_permissions(db):
    """
    ให้ USER เห็นเฉพาะเมนูตามภาพ:
    - employees.view
    - time.leave.request, time.ot.request
    - payroll.report.view
    - meeting.view
    - security.password.change
    MANAGER/ADMIN จะไปถูกเติมที่อื่นต่อ
    """
    wanted = [
        "employees.view",
        "time.leave.request",
        "time.ot.request",
        "payroll.report.view",
        "meeting.view",
        "security.password.change",
    ]
    # ensure roles exist
    db.execute(text("INSERT OR IGNORE INTO security_roles(name) VALUES ('ADMIN')"))
    db.execute(text("INSERT OR IGNORE INTO security_roles(name) VALUES ('MANAGER')"))
    db.execute(text("INSERT OR IGNORE INTO security_roles(name) VALUES ('USER')"))

    # map codes -> ids
    perm_rows = db.execute(text("SELECT id, code FROM security_permissions")).mappings().all()
    code2id = {r["code"]: r["id"] for r in perm_rows}
    role_id = db.execute(text("SELECT id FROM security_roles WHERE name='USER'")).scalar()

    for code in wanted:
        pid = code2id.get(code)
        if pid:
            db.execute(text("""
                INSERT OR IGNORE INTO security_role_permissions(role_id, perm_id)
                VALUES (:rid, :pid)
            """), {"rid": role_id, "pid": pid})
    db.commit()
    
def seed_full_permissions(db: Session):
    # ensure roles
    for r in ("ADMIN", "MANAGER", "USER"):
        db.execute(text("INSERT OR IGNORE INTO security_roles(name) VALUES(:n)"), {"n": r})
    # ensure permissions
    for code, desc in DEFAULT_PERMS:
        db.execute(text("""
            INSERT OR IGNORE INTO security_permissions(code, description)
            VALUES(:c, :d)
        """), {"c": code, "d": desc})
    # grant ADMIN all
    db.execute(text("""
        INSERT OR IGNORE INTO security_role_permissions(role_id, perm_id)
        SELECT r.id, p.id
        FROM security_roles r
        JOIN security_permissions p
        WHERE r.name='ADMIN'
    """))
    db.commit()