# modules/data_management/routes.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from modules.data_management import schemas, services
from fastapi.templating import Jinja2Templates
from typing import List
import os, shutil, datetime

ui_router = APIRouter()
api_router = APIRouter()
templates = Jinja2Templates(directory="templates")

# ---------- UI ROUTES ----------
@ui_router.get("/", response_class=HTMLResponse)
async def read_data_management_root_ui(request: Request):
    return templates.TemplateResponse("data_management/index.html", {"request": request})

@ui_router.get("/departments", response_class=HTMLResponse)
async def read_departments_ui(request: Request):
    return templates.TemplateResponse("data_management/departments.html", {"request": request})

@ui_router.get("/positions", response_class=HTMLResponse)
async def read_positions_ui(request: Request):
    return templates.TemplateResponse("data_management/positions.html", {"request": request})

@ui_router.get("/employees", response_class=HTMLResponse)
async def read_employees_ui(request: Request):
    return templates.TemplateResponse("data_management/employees.html", {"request": request})

# ---------- API ROUTES : Departments ----------
@api_router.post("/departments/", response_model=schemas.DepartmentInDB, status_code=status.HTTP_201_CREATED)
def create_department_route(department: schemas.DepartmentCreate, db: Session = Depends(get_db)):
    return services.create_department(db=db, department=department)

@api_router.get("/departments/", response_model=List[schemas.DepartmentInDB])
def read_departments_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_departments(db=db, skip=skip, limit=limit)

@api_router.get("/departments/{department_id}", response_model=schemas.DepartmentInDB)
def read_department_route(department_id: int, db: Session = Depends(get_db)):
    db_department = services.get_department(db=db, department_id=department_id)
    if db_department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบแผนก")
    return db_department

@api_router.put("/departments/{department_id}", response_model=schemas.DepartmentInDB)
def update_department_route(department_id: int, department: schemas.DepartmentUpdate, db: Session = Depends(get_db)):
    return services.update_department(db=db, department_id=department_id, department_update=department)

@api_router.delete("/departments/{department_id}", status_code=status.HTTP_200_OK)
def delete_department_route(department_id: int, db: Session = Depends(get_db)):
    return services.delete_department(db=db, department_id=department_id)

# ---------- API ROUTES : Positions ----------
@api_router.post("/positions/", response_model=schemas.PositionInDB, status_code=status.HTTP_201_CREATED)
def create_position_route(position: schemas.PositionCreate, db: Session = Depends(get_db)):
    return services.create_position(db=db, position=position)

@api_router.get("/positions/", response_model=List[schemas.PositionInDB])
def read_positions_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_positions(db=db, skip=skip, limit=limit)

@api_router.get("/positions/{position_id}", response_model=schemas.PositionInDB)
def read_position_route(position_id: int, db: Session = Depends(get_db)):
    db_position = services.get_position(db=db, position_id=position_id)
    if db_position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบตำแหน่ง")
    return db_position

@api_router.put("/positions/{position_id}", response_model=schemas.PositionInDB)
def update_position_route(position_id: int, position: schemas.PositionUpdate, db: Session = Depends(get_db)):
    return services.update_position(db=db, position_id=position_id, position_update=position)

@api_router.delete("/positions/{position_id}", status_code=status.HTTP_200_OK)
def delete_position_route(position_id: int, db: Session = Depends(get_db)):
    return services.delete_position(db=db, position_id=position_id)

# ---------- API ROUTES : Employees ----------
@api_router.post("/employees/", response_model=schemas.EmployeeInDB, status_code=status.HTTP_201_CREATED)
def create_employee_route(employee: schemas.EmployeeCreate, db: Session = Depends(get_db)):
    return services.create_employee(db=db, employee=employee)

@api_router.get("/employees/", response_model=List[schemas.EmployeeInDB])
def read_employees_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_employees(db=db, skip=skip, limit=limit)

@api_router.get("/employees/{employee_id}", response_model=schemas.EmployeeInDB)
def read_employee_route(employee_id: int, db: Session = Depends(get_db)):
    db_employee = services.get_employee(db=db, employee_id=employee_id)
    if db_employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบพนักงาน")
    return db_employee

@api_router.put("/employees/{employee_id}", response_model=schemas.EmployeeInDB)
def update_employee_route(employee_id: int, employee: schemas.EmployeeUpdate, db: Session = Depends(get_db)):
    return services.update_employee(db=db, employee_id=employee_id, employee_update=employee)

@api_router.delete("/employees/{employee_id}", status_code=status.HTTP_200_OK)
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
    db_employee = services.get_employee(db=db, employee_id=employee_id)
    if not db_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบพนักงานที่ระบุ")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ไฟล์ที่อัปโหลดไม่ใช่รูปภาพ")

    ext = os.path.splitext(file.filename)[1]
    new_filename = f"employee_{employee_id}_profile_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file_location = os.path.join(PROFILE_PICTURE_DIR, new_filename)
    try:
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"filename": new_filename, "file_path": f"/{file_location}"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"เกิดข้อผิดพลาดในการอัปโหลดรูปภาพ: {e}")

@api_router.post("/employees/{employee_id}/upload-documents", response_model=dict)
async def upload_application_documents(employee_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    db_employee = services.get_employee(db=db, employee_id=employee_id)
    if not db_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบพนักงานที่ระบุ")

    uploaded_paths = []
    for file in files:
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ไฟล์ '{file.filename}' ไม่ใช่ไฟล์ PDF")
        ext = os.path.splitext(file.filename)[1]
        new_filename = f"employee_{employee_id}_doc_{datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f')}{ext}"
        file_location = os.path.join(DOCUMENT_DIR, new_filename)
        try:
            with open(file_location, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            uploaded_paths.append(f"/{file_location}")
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"เกิดข้อผิดพลาดในการอัปโหลดไฟล์ '{file.filename}': {e}")
    return {"uploaded_files": uploaded_paths}
