from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database.connection import get_db
from modules.data_management.models import Employee
from modules.security.model import AppModule, ModulePermission, UserRole

def get_current_employee(request: Request, db: Session = Depends(get_db)):
    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(401, "Unauthorized")
    me = db.query(Employee).filter(Employee.id == uid).first()
    if not me:
        raise HTTPException(401, "Unauthorized")
    request.state.current_user = me
    return me

def is_admin(user) -> bool:
    # ถ้ามี enum UserRole.ADMIN ให้ใช้ตามนั้น ไม่งั้นเทียบกับ string
    try:
        admin_val = UserRole.ADMIN.value
    except Exception:
        admin_val = "admin"
    # 1) มีฟิลด์ role และเป็น admin
    if getattr(user, "role", None) == admin_val:
        return True
    # 2) fallback: บัญชี seed เริ่มต้น
    if getattr(user, "email", "").lower() == "admin@hrm.local":
        return True
    return False

def require_module(module: AppModule, action: str = "view"):
    def _dep(request: Request, db: Session = Depends(get_db), me=Depends(get_current_employee)):
        if is_admin(me):
            return me
        if module == AppModule.PERSONAL_PROFILE:
            return me
        perm = db.query(ModulePermission).filter_by(employee_id=me.id, module=module).first()
        if not perm:
            raise HTTPException(403, "Forbidden")
        if action == "view" and not perm.can_view:
            raise HTTPException(403, "Forbidden")
        if action == "edit" and not (perm.can_edit or perm.can_view):
            raise HTTPException(403, "Forbidden")
        return me
    return _dep
