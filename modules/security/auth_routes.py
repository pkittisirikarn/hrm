from fastapi import APIRouter, Request, Depends, Form, HTTPException
from starlette.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database.connection import get_db
from modules.data_management.models import Employee
from modules.security.passwords import verify_password  # ✅

api = APIRouter(prefix="/auth", tags=["auth"])
pages = APIRouter()
templates = Jinja2Templates(directory="templates")

@pages.get("/auth/login")
def login_page(request: Request):
    return templates.TemplateResponse("security/login.html", {"request": request})

@api.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    ident = (email or "").strip().lower()
    if "@" not in ident:
        ident = f"{ident}@hrm.local"  # อนุญาตพิมพ์แค่ "admin"
    user = db.query(Employee).filter(Employee.email == ident).first()
    if not user or not verify_password(password, getattr(user, "password_hash", "")):
        raise HTTPException(400, "อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    request.session["uid"] = user.id
    return {"ok": True}

@api.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}
