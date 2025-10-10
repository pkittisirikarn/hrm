# modules/security/password_routes.py
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from starlette.templating import Jinja2Templates
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session
from database.connection import get_db
from modules.security.deps import get_current_employee
from modules.security.passwords import hash_password, verify_password

api_pw = APIRouter(prefix="/api/v1/security", tags=["security"])
pages = APIRouter()
templates = Jinja2Templates(directory="templates")

@pages.get("/security/password")
def password_page(request: Request, me=Depends(get_current_employee)):
    # เปิดหน้าเปลี่ยนรหัสผ่าน (ต้องมี me)
    if not me:
        raise HTTPException(401, "Unauthorized")
    return templates.TemplateResponse("security/password.html", {"request": request})

@api_pw.post("/password/change")
def change_password(
    old_password: str = Form(""),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    me=Depends(get_current_employee),
):
    if not me:
        raise HTTPException(401, "Unauthorized")

    # ensure column password_hash
    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("employees")}
    if "password_hash" not in cols:
        db.execute(text("ALTER TABLE employees ADD COLUMN password_hash TEXT"))

    row = db.execute(
        text("SELECT password_hash FROM employees WHERE id=:i"),
        {"i": me.id},
    ).first()
    cur_hash = row.password_hash if row else None

    # ถ้ามีรหัสเดิมอยู่ ต้อง verify ให้ผ่านก่อน
    if cur_hash and not verify_password(old_password, cur_hash):
        raise HTTPException(400, "รหัสผ่านเดิมไม่ถูกต้อง")

    db.execute(
        text("UPDATE employees SET password_hash=:h WHERE id=:i"),
        {"h": hash_password(new_password), "i": me.id},
    )
    db.commit()
    return {"ok": True}
