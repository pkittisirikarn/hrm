# modules/security/permissions_service.py
from sqlalchemy import text
from sqlalchemy.orm import Session

# --------- สร้างตาราง Security ทั้งหมด (id-based) ----------
def ensure_security_tables(engine) -> None:
    with engine.begin() as conn:
        # roles
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_roles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """))

        # permissions catalog
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            description TEXT
        )
        """))

        # mapping role <-> permission (id-based)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_role_permissions(
            role_id INTEGER NOT NULL,
            perm_id INTEGER NOT NULL,
            PRIMARY KEY(role_id, perm_id),
            FOREIGN KEY(role_id) REFERENCES security_roles(id) ON DELETE CASCADE,
            FOREIGN KEY(perm_id) REFERENCES security_permissions(id) ON DELETE CASCADE
        )
        """))

        # mapping user <-> role (id-based)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS security_user_roles(
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY(user_id, role_id)
        )
        """))

        # (ตัวเก่าแบบ string ก็เผื่อไว้ ไม่บังคับมี)
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS role_permissions(
            role TEXT NOT NULL,
            perm TEXT NOT NULL,
            PRIMARY KEY(role, perm)
        )
        """))

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
def seed_default_roles_permissions(db: Session):
    # ถ้าไม่มี permission อะไรเลย ให้ใส่อย่างน้อย security.manage
    db.execute(text("""
        INSERT OR IGNORE INTO security_permissions(code, description)
        VALUES('security.manage','Manage roles & permissions')
    """))
    # ใส่ roles หลัก
    for r in ("ADMIN", "MANAGER", "USER"):
        db.execute(text("INSERT OR IGNORE INTO security_roles(name) VALUES(:n)"), {"n": r})
    # map ADMIN -> security.manage
    db.execute(text("""
        INSERT OR IGNORE INTO security_role_permissions(role_id, perm_id)
        SELECT r.id, p.id
        FROM security_roles r, security_permissions p
        WHERE r.name='ADMIN' AND p.code='security.manage'
    """))
    db.commit()
