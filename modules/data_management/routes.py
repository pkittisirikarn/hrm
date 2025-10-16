from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from core.templates import templates
# from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
import os, shutil, datetime
from .schemas import EmployeeOut

from database.connection import get_db
from modules.data_management import schemas, services
from modules.security.deps import get_current_employee
from modules.security.model import UserRole
from modules.security.deps import require_perm

ui_router = APIRouter()
api_router = APIRouter()
# templates = Jinja2Templates(directory="templates")

# ---------- UI ----------
@ui_router.get("/", response_class=HTMLResponse)
async def read_data_management_root_ui(request: Request):
    return templates.TemplateResponse("data_management/index.html", {"request": request})

@ui_router.get("/departments", response_class=HTMLResponse)
async def read_departments_ui(request: Request):
    return templates.TemplateResponse("data_management/departments.html", {"request": request})

@ui_router.get("/positions", response_class=HTMLResponse)
async def read_positions_ui(request: Request):
    return templates.TemplateResponse("data_management/positions.html", {"request": request})

@ui_router.get("/employees", response_class=HTMLResponse, dependencies=[Depends(require_perm("employees.view"))])
async def read_employees_ui(request: Request):
    return templates.TemplateResponse("data_management/employees.html", {"request": request})

# ---------- Helpers (clean form/json) ----------
def _clean_optional_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None

def _drop_empty(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if v is None or v == "":
            continue
        out[k] = v
    return out

# ---------- API : Departments ----------
@api_router.post("/departments/", response_model=schemas.DepartmentInDB, status_code=status.HTTP_201_CREATED)
def create_department_route(department: schemas.DepartmentCreate, db: Session = Depends(get_db)):
    return services.create_department(db=db, department=department)

@api_router.get("/departments/", response_model=List[schemas.DepartmentInDB])
def read_departments_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_departments(db=db, skip=skip, limit=limit)

@api_router.get("/departments/{department_id}", response_model=schemas.DepartmentInDB)
def read_department_route(department_id: int, db: Session = Depends(get_db)):
    obj = services.get_department(db=db, department_id=department_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบแผนก")
    return obj

@api_router.put("/departments/{department_id}", response_model=schemas.DepartmentInDB)
def update_department_route(department_id: int, department: schemas.DepartmentUpdate, db: Session = Depends(get_db)):
    return services.update_department(db=db, department_id=department_id, department_update=department)

@api_router.delete("/departments/{department_id}", status_code=200)
def delete_department_route(department_id: int, db: Session = Depends(get_db)):
    return services.delete_department(db=db, department_id=department_id)

# ---------- API : Positions ----------
@api_router.post("/positions/", response_model=schemas.PositionInDB, status_code=status.HTTP_201_CREATED)
def create_position_route(position: schemas.PositionCreate, db: Session = Depends(get_db)):
    return services.create_position(db=db, position=position)

@api_router.get("/positions/", response_model=List[schemas.PositionInDB])
def read_positions_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_positions(db=db, skip=skip, limit=limit)

@api_router.get("/positions/{position_id}", response_model=schemas.PositionInDB)
def read_position_route(position_id: int, db: Session = Depends(get_db)):
    obj = services.get_position(db=db, position_id=position_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบตำแหน่ง")
    return obj

@api_router.put("/positions/{position_id}", response_model=schemas.PositionInDB)
def update_position_route(position_id: int, position: schemas.PositionUpdate, db: Session = Depends(get_db)):
    return services.update_position(db=db, position_id=position_id, position_update=position)

@api_router.delete("/positions/{position_id}", status_code=200)
def delete_position_route(position_id: int, db: Session = Depends(get_db)):
    return services.delete_position(db=db, position_id=position_id)

# ---------- API : Employees ----------
@api_router.post("/employees/", response_model=schemas.EmployeeInDB,
                 status_code=status.HTTP_201_CREATED,
                 dependencies=[Depends(require_perm("employees.edit"))])
async def create_employee_route(request: Request, db: Session = Depends(get_db)):
    if request.headers.get("content-type", "").startswith("application/json"):
        raw = await request.json()
    else:
        raw = dict(await request.form())

    payload = {
        "employee_id_number": str(raw.get("employee_id_number") or "").strip(),
        "first_name":        str(raw.get("first_name") or "").strip(),
        "last_name":         str(raw.get("last_name") or "").strip(),
        "date_of_birth":     str(raw.get("date_of_birth") or "").strip(),
        "address":           str(raw.get("address") or "").strip(),
        "id_card_number":    _clean_optional_str(raw.get("id_card_number")),
        "profile_picture_path": _clean_optional_str(raw.get("profile_picture_path")),
        "application_documents_paths": _clean_optional_str(raw.get("application_documents_paths")),
        "bank_account_number": _clean_optional_str(raw.get("bank_account_number")),
        "bank_name":           _clean_optional_str(raw.get("bank_name")),
        "email":               _clean_optional_str(raw.get("email")),
        "phone_number":        _clean_optional_str(raw.get("phone_number")),
        "hire_date":           str(raw.get("hire_date") or "").strip(),
        "termination_date":    _clean_optional_str(raw.get("termination_date")),
        "employee_status":     _clean_optional_str(raw.get("employee_status")) or "active",
        "department_id":       int(raw.get("department_id")),
        "position_id":         int(raw.get("position_id")),
    }
    return services.create_employee(db=db, employee=schemas.EmployeeCreate(**payload))

@api_router.get("/employees/", response_model=List[schemas.EmployeeInDB])
def read_employees_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_employees(db=db, skip=skip, limit=limit)

@api_router.get("/employees/{employee_id}", response_model=schemas.EmployeeInDB)
def read_employee_route(employee_id: int, db: Session = Depends(get_db)):
    obj = services.get_employee(db=db, employee_id=employee_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบพนักงาน")
    return obj

@api_router.put("/employees/{employee_id}", response_model=schemas.EmployeeInDB)
async def update_employee_route(employee_id: int, request: Request, db: Session = Depends(get_db)):
    if request.headers.get("content-type", "").startswith("application/json"):
        raw = await request.json()
    else:
        raw = dict(await request.form())

    upd = {
        "employee_id_number": _clean_optional_str(raw.get("employee_id_number")),
        "first_name":         _clean_optional_str(raw.get("first_name")),
        "last_name":          _clean_optional_str(raw.get("last_name")),
        "date_of_birth":      _clean_optional_str(raw.get("date_of_birth")),
        "address":            _clean_optional_str(raw.get("address")),
        "id_card_number":     _clean_optional_str(raw.get("id_card_number")),
        "profile_picture_path": _clean_optional_str(raw.get("profile_picture_path")),
        "application_documents_paths": _clean_optional_str(raw.get("application_documents_paths")),
        "bank_account_number": _clean_optional_str(raw.get("bank_account_number")),
        "bank_name":          _clean_optional_str(raw.get("bank_name")),
        "email":              _clean_optional_str(raw.get("email")),
        "phone_number":       _clean_optional_str(raw.get("phone_number")),
        "hire_date":          _clean_optional_str(raw.get("hire_date")),
        "termination_date":   _clean_optional_str(raw.get("termination_date")),
        "employee_status":    _clean_optional_str(raw.get("employee_status")),
        "department_id":      _clean_optional_str(raw.get("department_id")),
        "position_id":        _clean_optional_str(raw.get("position_id")),
    }
    upd = _drop_empty(upd)  # << ค่าว่างจะไม่ไปทับ DB

    return services.update_employee(
        db=db,
        employee_id=employee_id,
        employee_update=schemas.EmployeeUpdate(**upd)
    )

@api_router.delete("/employees/{employee_id}", status_code=200)
def delete_employee_route(employee_id: int, db: Session = Depends(get_db)):
    return services.delete_employee(db=db, employee_id=employee_id)

# ---------- File Upload ----------
UPLOAD_DIR = "static/uploads"
PROFILE_PICTURE_DIR = os.path.join(UPLOAD_DIR, "profile_pictures")
DOCUMENT_DIR = os.path.join(UPLOAD_DIR, "documents")
os.makedirs(PROFILE_PICTURE_DIR, exist_ok=True)
os.makedirs(DOCUMENT_DIR, exist_ok=True)

@api_router.post("/employees/{employee_id}/upload-profile-picture", response_model=dict)
async def upload_profile_picture(employee_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    emp = services.get_employee(db=db, employee_id=employee_id)
    if not emp:
        raise HTTPException(404, "ไม่พบพนักงานที่ระบุ")
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "ไฟล์ที่อัปโหลดไม่ใช่รูปภาพ")

    ext = os.path.splitext(file.filename)[1]
    new_filename = f"employee_{employee_id}_profile_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file_location = os.path.join(PROFILE_PICTURE_DIR, new_filename)
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"filename": new_filename, "file_path": f"/{file_location}"}
    except Exception as e:
        raise HTTPException(500, f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {e}")

@api_router.post("/employees/{employee_id}/upload-documents", response_model=dict)
async def upload_application_documents(employee_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    emp = services.get_employee(db=db, employee_id=employee_id)
    if not emp:
        raise HTTPException(404, "ไม่พบพนักงานที่ระบุ")

    uploaded_paths = []
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(400, f"ไฟล์ '{file.filename}' ไม่ใช่ PDF")
        ext = os.path.splitext(file.filename)[1]
        new_filename = f"employee_{employee_id}_doc_{datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f')}{ext}"
        file_location = os.path.join(DOCUMENT_DIR, new_filename)
        try:
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_paths.append(f"/{file_location}")
        except Exception as e:
            raise HTTPException(500, f"อัปโหลดไฟล์ '{file.filename}' ล้มเหลว: {e}")
    return {"uploaded_files": uploaded_paths}
