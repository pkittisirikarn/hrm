# modules/security/password_routes.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from database.connection import get_db, engine
from modules.security.deps import require_perm, get_current_employee
import bcrypt

# ---- Routers ----
api_pw = APIRouter(prefix="/api/v1/security/password", tags=["Security Password API"])
pages = APIRouter(tags=["Security Password Pages"])
templates = Jinja2Templates(directory="templates")

# ---- Migration helper: ensure employees.password_hash ----
def ensure_password_hash_column() -> None:
    """
    เพิ่มคอลัมน์ password_hash ในตาราง employees ถ้ายังไม่มี
    """
    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(employees)")).mappings().all()
        names = {c["name"] for c in cols}
        if "password_hash" not in names:
            conn.execute(text("ALTER TABLE employees ADD COLUMN password_hash TEXT"))

# ---- Page ----
@pages.get("/security/password")
def password_page(request: Request, _=Depends(require_perm("security.manage"))):
    return templates.TemplateResponse("security/password.html", {"request": request})

# ---- APIs ----
@api_pw.post("/reset", dependencies=[Depends(require_perm("security.manage"))])
def reset_password(
    user_id: int = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    ผู้ดูแลระบบรีเซ็ตรหัสผ่านให้ผู้ใช้คนอื่น
    """
    pw_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.execute(text("UPDATE employees SET password_hash=:h WHERE id=:uid"), {"h": pw_hash, "uid": user_id})
    db.commit()
    return {"ok": True}

@api_pw.post("/change")
def change_password(
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    me = Depends(get_current_employee),
    db: Session = Depends(get_db),
):
    """
    ผู้ใช้เปลี่ยนรหัสผ่านตัวเอง: ตรวจ current_password แล้วอัปเดตเป็นรหัสใหม่
    """
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="รหัสผ่านใหม่ไม่ตรงกัน")

    row = db.execute(text("SELECT password_hash FROM employees WHERE id=:id"), {"id": me.id}).first()
    current_hash = (row[0] if row else None) or ""

    if current_hash:
        ok = False
        try:
            ok = bcrypt.checkpw(current_password.encode("utf-8"), current_hash.encode("utf-8"))
        except Exception:
            ok = False
        if not ok:
            raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")
    # ถ้า current_hash ว่าง แปลว่ายังไม่เคยตั้งรหัสผ่าน -> อนุญาตตั้งได้เลย

    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    db.execute(text("UPDATE employees SET password_hash=:h WHERE id=:id"), {"h": new_hash, "id": me.id})
    db.commit()
    return {"ok": True}

__all__ = ["api_pw", "pages", "ensure_password_hash_column"]
