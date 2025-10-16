# modules/security/deps.py
from fastapi import Depends, HTTPException, Request
from types import SimpleNamespace
from sqlalchemy.orm import Session
from database.connection import get_db
from .perms import compute_user_perms

def get_current_employee(request: Request) -> SimpleNamespace:
    return SimpleNamespace(
        id=request.session.get("emp_id"),
        role=request.session.get("role", "USER"),
        email=request.session.get("email"),
        name=request.session.get("name"),
    )

def is_admin(me: SimpleNamespace) -> bool:
    return (getattr(me, "role", "") or "").upper() == "ADMIN"

def has_perm(request: Request, code: str, db: Session) -> bool:
    # ADMIN ผ่านทุกสิทธิ์
    if (request.session.get("role") or "").upper() == "ADMIN":
        return True
    perms = request.session.get("perms")
    if not perms:
        emp_id = request.session.get("emp_id")
        role = request.session.get("role", "USER")
        perms = list(compute_user_perms(db, emp_id, role))
        request.session["perms"] = perms
    return code in perms

def require_perm(code: str):
    def _dep(request: Request, db: Session = Depends(get_db)):
        if not has_perm(request, code, db):
            raise HTTPException(403, "Forbidden")
        return True
    return _dep
