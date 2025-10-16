from __future__ import annotations
from typing import Optional

# ใช้ werkzeug เป็นมาตรฐาน (PBKDF2) และรองรับ bcrypt เพื่อความเข้ากันได้ย้อนหลัง
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import bcrypt  # มีอยู่แล้วในโปรเจกต์
except Exception:
    bcrypt = None  # เผื่อสภาพแวดล้อมไม่มี (จะไม่ใช้เส้นทาง fallback นี้)


def is_bcrypt_hash(h: Optional[str]) -> bool:
    return isinstance(h, str) and h.startswith(("$2a$", "$2b$", "$2y$"))


def hash_password(password: str) -> str:
    """
    สร้างแฮชมาตรฐานเดียวกับระบบ (PBKDF2-SHA256 ของ werkzeug)
    """
    return generate_password_hash(password or "", method="pbkdf2:sha256", salt_length=16)


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    """
    ตรวจรหัสผ่าน:
    - ถ้าเป็น bcrypt (เริ่มด้วย $2a$/$2b$/$2y$) จะตรวจด้วย bcrypt เพื่อรองรับข้อมูลเก่า
    - มิฉะนั้นตรวจด้วย werkzeug PBKDF2
    """
    if not password_hash:
        return False

    if is_bcrypt_hash(password_hash) and bcrypt is not None:
        try:
            return bcrypt.checkpw((password or "").encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False

    try:
        return check_password_hash(password_hash, password or "")
    except Exception:
        return False
