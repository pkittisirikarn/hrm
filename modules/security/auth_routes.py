# modules/security/auth_routes.py
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db
from modules.security.passwords import verify_password
from modules.security.deps import compute_user_perms

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
def login_page(request: Request):
    # แสดงฟอร์มเสมอ เพื่อตัดลูป 302
    return templates.TemplateResponse(
        "security/login.html",
        {"request": request, "hide_nav": True}
    )

@router.post("/login")
def do_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user_input = email.strip()
    if "@" not in user_input:
        user_input = f"{user_input}@hrm.local"

    row = db.execute(
        text("""
            SELECT id, email,
                   COALESCE(password_hash,'') AS password_hash,
                   COALESCE(role,'ADMIN')     AS role
            FROM employees WHERE email=:email
        """), {"email": user_input}
    ).mappings().first()

    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(status_code=400, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

    request.session["emp_id"] = row["id"]
    request.session["email"]  = row["email"]
    request.session["role"]   = row["role"]

    # 👇 คำนวณสิทธิ์ของ user แล้วเก็บใน session
    request.session["perms"] = list(compute_user_perms(db, row["id"], row["role"]))

    return RedirectResponse("/", status_code=302)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/auth/login", status_code=302)
