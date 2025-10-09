# modules/security/password_routes.py
from fastapi import APIRouter, Depends, HTTPException, Form, Request
from sqlalchemy.orm import Session
from starlette.templating import Jinja2Templates

from database.connection import get_db
from modules.security.deps import get_current_employee
from modules.security.passwords import hash_password, verify_password

# ----- Templates -----
templates = Jinja2Templates(directory="templates")

# ----- UI Page (ให้ main.py import ใช้ได้) -----
def password_page(request: Request):
    # แสดงหน้าเปลี่ยนรหัสผ่าน (ต้องล็อกอินแล้วถึงจะใช้งานได้ในฝั่ง API)
    return templates.TemplateResponse("security/password.html", {"request": request})

# ----- API -----
api_pw = APIRouter(prefix="/api/v1/security", tags=["security"])

@api_pw.post("/password/change")
def change_password(
    old_password: str = Form(""),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    me = Depends(get_current_employee),
):
    if len(new_password) < 8:
        raise HTTPException(400, "รหัสผ่านอย่างน้อย 8 ตัวอักษร")

    # ตั้งครั้งแรก (ยังไม่มี hash เดิม)
    if not getattr(me, "password_hash", None):
        me.password_hash = hash_password(new_password)
        db.add(me); db.commit()
        return {"ok": True, "first_set": True}

    # มีรหัสเดิมแล้ว → ต้องตรวจ old_password
    if not verify_password(old_password, me.password_hash):
        raise HTTPException(400, "รหัสผ่านเดิมไม่ถูกต้อง")

    me.password_hash = hash_password(new_password)
    db.add(me); db.commit()
    return {"ok": True}

__all__ = ["api_pw", "password_page"]
