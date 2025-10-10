# modules/security/passwords.py
"""
Password hashing helpers (PBKDF2-HMAC-SHA256).
- ถ้ามี werkzeug: ใช้ generate_password_hash / check_password_hash (pbkdf2:sha256)
- ถ้าไม่มี: ใช้ hashlib.pbkdf2_hmac (pure python) พร้อมฟอร์แมตของเราเอง
"""

from typing import Optional

# ---- ทางเลือกที่ 1: ใช้ werkzeug ถ้ามี ----
try:
    from werkzeug.security import generate_password_hash, check_password_hash  # type: ignore

    def hash_password(password: str) -> str:
        # ใช้ pbkdf2:sha256 + random salt 16 bytes
        return generate_password_hash(password or "", method="pbkdf2:sha256", salt_length=16)

    def verify_password(password: str, password_hash: Optional[str]) -> bool:
        if not password_hash:
            return False
        return check_password_hash(password_hash, password or "")

# ---- ทางเลือกที่ 2: fallback เป็น hashlib.pbkdf2_hmac (pure python) ----
except Exception:
    import os, hmac, binascii, hashlib

    _ALG = "pbkdf2_sha256"
    _ITER = 200_000
    _SALT_BYTES = 16

    def _hex(b: bytes) -> str:
        return binascii.hexlify(b).decode("ascii")

    def _unhex(s: str) -> bytes:
        return binascii.unhexlify(s.encode("ascii"))

    def hash_password(password: str) -> str:
        salt = os.urandom(_SALT_BYTES)
        dk = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, _ITER)
        # ฟอร์แมต: pbkdf2_sha256$ITER$salt_hex$dk_hex
        return f"{_ALG}${_ITER}${_hex(salt)}${_hex(dk)}"

    def verify_password(password: str, password_hash: Optional[str]) -> bool:
        if not password_hash:
            return False
        try:
            alg, iter_s, salt_hex, dk_hex = password_hash.split("$", 3)
            if alg != _ALG:
                return False
            iters = int(iter_s)
            salt = _unhex(salt_hex)
            expected = _unhex(dk_hex)
            candidate = hashlib.pbkdf2_hmac(
                "sha256", (password or "").encode("utf-8"), salt, iters
            )
            return hmac.compare_digest(candidate, expected)
        except Exception:
            return False
