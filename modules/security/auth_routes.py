# modules/security/auth_routes.py
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from database.connection import get_db
from modules.security.passwords import verify_password, hash_password, is_bcrypt_hash
from modules.security.perms import compute_user_perms

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    templates = request.app.state.templates
    return templates.TemplateResponse("security/login.html", {"request": request})

@router.post("/login")
def do_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    templates = request.app.state.templates

    # อนุญาตกรอกเฉพาะ user ส่วนหน้าแล้วต่อโดเมนอัตโนมัติ
    if "@" not in email:
        email = f"{email}@hrm.local"

    row = db.execute(
        text("""
            SELECT id, first_name, last_name, email, role, password_hash
            FROM employees
            WHERE lower(email) = lower(:email)
        """),
        {"email": email},
    ).mappings().first()

    if not row or not verify_password(password, row["password_hash"]):
        return templates.TemplateResponse(
            "security/login.html",
            {"request": request, "error": "อีเมลหรือรหัสผ่านไม่ถูกต้อง", "email": email},
            status_code=400
        )

    # migrate hash (ถ้าเป็น bcrypt เก่า) -> เปลี่ยนเป็นปัจจุบัน
    if is_bcrypt_hash(row["password_hash"]):
        db.execute(
            text("UPDATE employees SET password_hash=:ph WHERE id=:id"),
            {"ph": hash_password(password), "id": row["id"]},
        )
        db.commit()

    # เซสชันหลัก
    request.session["emp_id"] = row["id"]
    request.session["employee_id"] = row["id"]
    request.session["user_id"] = row["id"]
    request.session["email"] = row["email"]
    request.session["role"] = row["role"]

    # คำนวณ perms และเซฟลง session (กัน None ให้เรียบร้อย)
    perms = compute_user_perms(db, emp_id=row["id"], role_name=row["role"])
    request.session["perms"] = sorted([p for p in perms if isinstance(p, str) and p.strip()])

    return RedirectResponse("/dashboard", status_code=303)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=303)
