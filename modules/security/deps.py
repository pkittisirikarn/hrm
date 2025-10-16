# modules/security/deps.py
from __future__ import annotations

from typing import Callable, Set
from types import SimpleNamespace

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.connection import get_db
from modules.security.perms import compute_user_perms  # มีอยู่แล้ว

# ------------------------------------------------------------
# Helpers: อ่าน employee จาก DB
# ------------------------------------------------------------
def _fetch_employee(db: Session, employee_id: int | None):
    if not employee_id:
        return None
    row = db.execute(
        text(
            """
            SELECT id, first_name, last_name, email, role
            FROM employees
            WHERE id = :id
            """
        ),
        {"id": employee_id},
    ).mappings().first()
    return SimpleNamespace(**row) if row else None


def _get_session_user_id(request: Request) -> int | None:
    # รองรับทั้งคีย์แบบเก่า/ใหม่
    return request.session.get("employee_id") or request.session.get("user_id")


# ------------------------------------------------------------
# Current employee dependencies
# ------------------------------------------------------------
def get_current_employee(
    request: Request, db: Session = Depends(get_db)
):
    """
    คืนข้อมูล employee ปัจจุบันจาก session; ถ้าไม่ล็อกอิน -> 401
    """
    uid = _get_session_user_id(request)
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LOGIN_REQUIRED")

    emp = _fetch_employee(db, uid)
    if not emp:
        # session มี uid แต่หาใน DB ไม่เจอ -> บังคับให้ล็อกอินใหม่
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LOGIN_REQUIRED")

    # ensure session['role'] ให้สอดคล้อง DB (กันเคส session เก่า)
    if request.session.get("role") != emp.role:
        request.session["role"] = emp.role
        request.session.pop("perms", None)  # ให้คำนวณสิทธิ์ใหม่

    return emp


def get_current_employee_id(request: Request) -> int:
    uid = _get_session_user_id(request)
    if not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LOGIN_REQUIRED")
    return int(uid)

# ✅ ฟังก์ชันที่ขาด: ใช้เป็น dependency ตรวจว่าเป็น ADMIN เท่านั้น
def is_admin(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    อนุญาตเฉพาะผู้มี role 'ADMIN'
    - ถ้ายังไม่ล็อกอิน → 303 ไป /auth/login
    - ถ้า role ไม่ใช่ ADMIN → 403 Forbidden
    """
    uid = request.session.get("employee_id") or request.session.get("user_id")
    if not uid:
        raise HTTPException(
            status_code=303,
            detail="LOGIN_REQUIRED",
            headers={"Location": "/auth/login"},
        )

    # เช็คจาก session ก่อน (เร็ว)
    if request.session.get("role") == "ADMIN":
        return True

    # กัน session เพี้ยน → ยืนยันจาก DB อีกชั้น
    role_db = db.execute(
        text("SELECT role FROM employees WHERE id=:id"),
        {"id": uid},
    ).scalar()

    if role_db == "ADMIN":
        # sync กลับเข้า session เผื่อที่อื่นใช้ต่อ
        request.session["role"] = "ADMIN"
        return True

    # ไม่ใช่แอดมิน
    raise HTTPException(status_code=403, detail="Administrator required")

# ------------------------------------------------------------
# Permissions helpers (cache ลง session)
# ------------------------------------------------------------
def _ensure_session_perms(request: Request, db: Session) -> Set[str]:
    perms_in_sess = request.session.get("perms")
    if isinstance(perms_in_sess, list):
        return set(perms_in_sess)

    uid = _get_session_user_id(request)
    if not uid:
        return set()

    role = request.session.get("role")
    # ถ้าไม่มี role ใน session ให้โหลดจาก DB
    if not role:
        emp = _fetch_employee(db, uid)
        role = emp.role if emp else None
        if role:
            request.session["role"] = role

    codes = compute_user_perms(db, uid, role or "USER")
    request.session["perms"] = list(codes)
    return set(codes)


def has_perm(request: Request, code: str, db: Session) -> bool:
    return code in _ensure_session_perms(request, db)


def require_perm(code: str) -> Callable:
    """
    ใช้เป็น FastAPI dependency:
      @router.get(..., dependencies=[Depends(require_perm("employees.view"))])
    """
    def _dep(request: Request, db: Session = Depends(get_db)):
        # ต้องล็อกอินก่อน
        uid = _get_session_user_id(request)
        if not uid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LOGIN_REQUIRED")
        # ตรวจสิทธิ์
        if not has_perm(request, code, db):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"PERMISSION_DENIED: {code}")
        return True
    return _dep
