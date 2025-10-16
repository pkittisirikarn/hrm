# modules/security/routes.py
from fastapi import APIRouter, Depends, Request, Form
from core.templates import templates
# from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db
from .deps import require_perm
from .perms import compute_user_perms
from .permissions_service import (
    list_roles, list_permissions, role_permission_ids,
    set_role_permission, list_user_roles, set_user_role
)

# Routers
api = APIRouter(prefix="/api/v1/security", tags=["Security API"])
pages = APIRouter(tags=["Security Pages"])
# templates = Jinja2Templates(directory="templates")

# ----------------------------
# Page: Roles & Permissions UI
# ----------------------------
@pages.get("/security/permissions", dependencies=[Depends(require_perm("security.manage"))])
def permissions_page(request: Request):
    return templates.TemplateResponse("security/permissions.html", {"request": request})

# ----------------------------
# Matrix APIs (roles / perms)
# ----------------------------
@api.get("/roles", dependencies=[Depends(require_perm("security.manage"))])
def api_list_roles(db: Session = Depends(get_db)):
    return {"roles": list_roles(db)}

@api.get("/perms", dependencies=[Depends(require_perm("security.manage"))])
def api_list_perms(db: Session = Depends(get_db)):
    return {"permissions": list_permissions(db)}

@api.get("/role-perms/{role_id}", dependencies=[Depends(require_perm("security.manage"))])
def api_role_perms(role_id: int, db: Session = Depends(get_db)):
    return {"permission_ids": role_permission_ids(db, role_id)}

@api.post("/role-perms/toggle", dependencies=[Depends(require_perm("security.manage"))])
def api_toggle_role_perm(
    request: Request,
    role_id: int = Form(...),
    perm_id: int = Form(...),
    enabled: bool = Form(...),
    db: Session = Depends(get_db),
):
    set_role_permission(db, role_id, perm_id, enabled)

    # ถ้าเป็น role เดียวกับที่ user ปัจจุบันใช้อยู่ ให้รีเฟรชสิทธิ์ใน session
    role_name = db.execute(text("SELECT name FROM security_roles WHERE id=:id"), {"id": role_id}).scalar()
    if role_name and request.session.get("role") == role_name:
        emp_id = request.session.get("emp_id")
        request.session["perms"] = list(compute_user_perms(db, emp_id, role_name))
    return {"ok": True}

# ----------------------------
# Employees & User-Role mapping
# ----------------------------
@api.get("/employees")
def api_list_employees(db: Session = Depends(get_db),
                       _ = Depends(require_perm("security.manage"))):
    rows = db.execute(text("""
        SELECT id,
               COALESCE(first_name,'') AS fn,
               COALESCE(last_name,'')  AS ln,
               COALESCE(email,'')      AS email,
               COALESCE(role,'USER')   AS role
        FROM employees
        ORDER BY fn, ln, id
    """)).fetchall()
    items = []
    for r in rows:
        name = f"{r.fn} {r.ln}".strip() or (r.email or f"Employee #{r.id}")
        items.append({"id": r.id, "name": name, "role": r.role})
    return items  # ← ส่งเป็น array

@api.get("/user-roles/{user_id}", dependencies=[Depends(require_perm("security.manage"))])
def api_user_roles(user_id: int, db: Session = Depends(get_db)):
    return {"role_ids": list_user_roles(db, user_id)}

@api.post("/user-roles/toggle", dependencies=[Depends(require_perm("security.manage"))])
def api_toggle_user_role(
    request: Request,
    user_id: int = Form(...),
    role_id: int = Form(...),
    enabled: bool = Form(...),
    db: Session = Depends(get_db),
):
    set_user_role(db, user_id, role_id, enabled)

    # ถ้าแก้ role ของ user ที่กำลังล็อกอิน และเป็น role ที่เขาใช้อยู่ -> รีเฟรชสิทธิ์
    if user_id == request.session.get("emp_id"):
        role_name = db.execute(text("SELECT name FROM security_roles WHERE id=:id"), {"id": role_id}).scalar()
        if role_name and request.session.get("role") == role_name:
            request.session["perms"] = list(compute_user_perms(db, user_id, role_name))
    return {"ok": True}

__all__ = ["api", "pages"]
