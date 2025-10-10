# modules/security/deps.py
from types import SimpleNamespace
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
from database.connection import get_db

def _has_column(table: str, col: str, request=None) -> bool:
    try:
        insp = inspect(request.app.state.db_engine if hasattr(request.app.state, "db_engine") else None)
    except Exception:
        insp = inspect(Depends(get_db))
    try:
        return any(c["name"] == col for c in inspect(Depends(get_db)).get_columns(table))
    except Exception:
        # fallback แบบไม่ใช้ inspector ที่ app เก็บไว้
        return True  # ถ้าสงสัย ให้ถือว่ามี (จะ select ผ่าน text ได้หากมีจริง)
    
def get_current_employee(request: Request, db: Session = Depends(get_db)):
    emp_id = request.session.get("emp_id")
    if not emp_id:
        raise HTTPException(401, "Unauthorized")

    # ดึง role / email / name ขั้นต่ำพอใช้
    cols = ["id", "first_name", "last_name", "email"]
    # ถ้ามีคอลัมน์ role จะดึงด้วย (โปรเจคคุณมี)
    cols.append("role")

    sql = f"SELECT {', '.join(cols)} FROM employees WHERE id=:id LIMIT 1"
    row = db.execute(text(sql), {"id": emp_id}).mappings().first()
    if not row:
        raise HTTPException(401, "Unauthorized")

    return SimpleNamespace(
        id=row["id"],
        first_name=row.get("first_name") or "",
        last_name=row.get("last_name") or "",
        email=row.get("email") or "",
        role=row.get("role") or "user",
        name=((row.get("first_name") or "") + " " + (row.get("last_name") or "")).strip(),
    )

def is_admin(me) -> bool:
    return (getattr(me, "role", None) or "").upper() == "ADMIN"
