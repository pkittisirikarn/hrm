# modules/security/passwords.py
# ตัวช่วย hash/verify รหัสผ่าน แบบไม่พึ่ง passlib/bcrypt
from typing import Tuple

# พยายามใช้ werkzeug (pbkdf2:sha256) ก่อน
try:
    from werkzeug.security import generate_password_hash, check_password_hash

    def hash_password(password: str) -> str:
        # pbkdf2:sha256 + random salt (16 bytes)
        return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def verify_password(password: str, password_hash: str) -> bool:
        return check_password_hash(password_hash, password)
except Exception:
    # ถ้าไม่มี werkzeug → ใช้ hashlib.pbkdf2_hmac แทน (pure python)
    import os, hmac, binascii, hashlib

    _ALG = "pbkdf2_sha256"
    _ITER = 200_000

    def _encode_hex(b: bytes) -> str:
        return binascii.hexlify(b).decode()

    def _decode_hex(s: str) -> bytes:
        return binascii.unhexlify(s.encode())

    def hash_password(password: str) -> str:
        salt = os.urandom(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITER)
        return f"{_ALG}${_ITER}${_encode_hex(salt)}${_encode_hex(dk)}"

    def verify_password(password: str, password_hash: str) -> bool:
        try:
            alg, iter_s, salt_hex, dk_hex = password_hash.split("$", 3)
            if alg != _ALG:
                return False
            iters = int(iter_s)
            salt = _decode_hex(salt_hex)
            expect = _decode_hex(dk_hex)
            got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
            return hmac.compare_digest(got, expect)
        except Exception:
            return False
