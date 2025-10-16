# modules/security/password_routes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from core.templates import templates
# from starlette.templating import Jinja2Templates

from database.connection import get_db
from modules.security.deps import require_perm, get_current_employee
from modules.security.passwords import hash_password, verify_password

# templates = Jinja2Templates(directory="templates")

# ---------------- UI PAGES (expects: pages) ----------------
pages = APIRouter()

@pages.get(
    "/security/password",
    response_class=HTMLResponse,
    dependencies=[Depends(require_perm("security.manage"))],
)
def password_page(request: Request):
    # เทมเพลตเดียวกับที่เราเพิ่มฟอร์ม 2 ส่วน (เปลี่ยนของตัวเอง / แอดมินตั้งให้ผู้อื่น)
    return templates.TemplateResponse("security/password.html", {"request": request})


# ---------------- API ROUTES (expects: api_pw) ----------------
api_pw = APIRouter(prefix="/api/v1/security/password", tags=["security"])

@api_pw.post("/reset", dependencies=[Depends(require_perm("security.manage"))])
def reset_password(
    user_id: int = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร")

    pw_hash = hash_password(new_password)  # ใช้ PBKDF2 ให้ตรงกับระบบล็อกอิน
    db.execute(
        text("UPDATE employees SET password_hash = :h WHERE id = :uid"),
        {"h": pw_hash, "uid": user_id},
    )
    db.commit()
    return {"ok": True}


@api_pw.post("/change")
def change_password(
    current_password: str | None = Form(None),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    me=Depends(get_current_employee),
):
    if not new_password or len(new_password) < 8:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร")

    row = db.execute(
        text("SELECT password_hash FROM employees WHERE id=:id"),
        {"id": me.id},
    ).mappings().first()
    current_hash = row["password_hash"] if row else None

    # ถ้ามีรหัสเดิม ต้องตรวจสอบก่อน
    if current_hash and not verify_password(current_password or "", current_hash):
        raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")

    new_hash = hash_password(new_password)
    db.execute(
        text("UPDATE employees SET password_hash = :h WHERE id = :id"),
        {"h": new_hash, "id": me.id},
    )
    db.commit()
    return {"ok": True}


# ---------------- UTIL (expects: ensure_password_hash_column) ----------------
def ensure_password_hash_column(engine=None) -> None:
    """
    เพิ่มคอลัมน์ password_hash ให้ตาราง employees ถ้ายังไม่มี
    รองรับ SQLite (PRAGMA table_info + ALTER TABLE ADD COLUMN)
    """
    from database.connection import engine as _eng
    eng = engine or _eng
    with eng.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(employees)")).fetchall()
        cols = {r[1] for r in rows}  # r[1] = name
        if "password_hash" not in cols:
            conn.execute(text("ALTER TABLE employees ADD COLUMN password_hash TEXT"))
            # ไม่ต้อง commit: connection ของ SQLAlchemy จะจัดการเองเมื่อปิด context
