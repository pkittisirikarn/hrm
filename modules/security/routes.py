# modules/security/routes.py
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from database.connection import get_db
from modules.security.model import AppModule, ModulePermission
from modules.security.deps import get_current_employee, is_admin

# API สำหรับจัดการสิทธิ์ (prefix /api/v1/security)
api = APIRouter(prefix="/api/v1/security", tags=["security"])

# เพจ UI (ไม่มี prefix)
pages = APIRouter()
templates = Jinja2Templates(directory="templates")

# ---------------------- Pages ---------------------- #

@pages.get("/data-management/backup")
def data_mgmt_backup_page(request: Request, me=Depends(get_current_employee)):
    if not is_admin(me):
        raise HTTPException(403, "Admins only")
    return templates.TemplateResponse("data_management/backup.html", {"request": request})

@pages.get("/security/permissions")
def page_permissions(request: Request, me=Depends(get_current_employee)):
    if not is_admin(me):
        raise HTTPException(403, "Admins only")
    return templates.TemplateResponse(
        "security/permissions.html",
        {"request": request, "modules": [m.value for m in AppModule]},
    )

# ---------------------- APIs ---------------------- #

@api.get("/employees")
def list_employees(db: Session = Depends(get_db)):
    """
    คืนรายชื่อพนักงานแบบย่อสำหรับ dropdown หน้า permissions
    """
    rows = db.execute(text("""
        SELECT
            id,
            COALESCE(first_name,'') AS fn,
            COALESCE(last_name,'')  AS ln,
            COALESCE(role,'user')   AS role
        FROM employees
        ORDER BY fn, ln
    """)).fetchall()
    return [{"id": r.id, "name": f"{r.fn} {r.ln}".strip(), "role": r.role} for r in rows]

@api.get("/permissions")
def get_permissions(employee_id: int, db: Session = Depends(get_db)):
    """
    อ่านสิทธิ์รายโมดูลของพนักงานคนหนึ่ง
    """
    items = (
        db.query(ModulePermission)
        .filter(ModulePermission.employee_id == employee_id)
        .all()
    )
    return [
        {
            "module": p.module.value,
            "can_view": p.can_view,
            "can_edit": p.can_edit,
            "id": p.id,
        }
        for p in items
    ]

@api.post("/permissions/update")
def update_permissions(
    employee_id: int = Form(...),
    modules_view: Optional[str] = Form(""),
    modules_edit: Optional[str] = Form(""),
    db: Session = Depends(get_db),
    me=Depends(get_current_employee),
):
    """
    อัปเดตสิทธิ์ของพนักงานแบบ bulk
    - modules_view: csv ของ module ที่ให้ดู
    - modules_edit: csv ของ module ที่ให้แก้ไข
    หมายเหตุ: PERSONAL_PROFILE จะให้ can_view เสมอ (ฝั่ง handler อื่นต้องบังคับให้ user เห็นได้เฉพาะของตน)
    """
    if not is_admin(me):
        raise HTTPException(403, "Admins only")

    allow_view = {m for m in (modules_view or "").split(",") if m}
    allow_edit = {m for m in (modules_edit or "").split(",") if m}

    # ลบของเดิมแล้วเขียนใหม่
    db.query(ModulePermission).filter(
        ModulePermission.employee_id == employee_id
    ).delete()

    for m in AppModule:
        db.add(
            ModulePermission(
                employee_id=employee_id,
                module=m,  # SQLEnum(AppModule) รองรับ enum โดยตรง
                can_view=(m.value in allow_view) or (m == AppModule.PERSONAL_PROFILE),
                can_edit=(m.value in allow_edit),
            )
        )

    db.commit()
    return {"ok": True}

__all__ = ["api", "pages"]
