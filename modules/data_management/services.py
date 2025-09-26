# modules/data_management/services.py
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from . import models, schemas

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def _has_related_records(emp) -> bool:
    """
    กันไว้สำหรับช่วงที่เรายังไม่เปิด relations ข้ามโมดูลจริง ๆ
    เช็คแบบ defensive: ถ้ามี attribute และมีข้อมูลสัมพันธ์อยู่ ให้ถือว่ามี related records
    """
    for attr in ("time_entries", "leave_requests"):
        if hasattr(emp, attr):
            rel = getattr(emp, attr)
            try:
                if rel and len(rel) > 0:
                    return True
            except TypeError:
                if rel:
                    return True
    return False

# ถ้าต้องการยืดหยุ่นเรื่อง enum ที่มาจาก frontend (เช่น "active", "on_leave")
# ให้เปิดใช้ฟังก์ชันนี้ โดยแทนที่ตอนสร้าง/อัปเดตพนักงาน
def _normalize_employee_status(value):
    if value is None:
        return None
    if isinstance(value, models.EmployeeStatus):
        return value
    v = str(value).strip().lower()
    mapping = {
        "active": models.EmployeeStatus.ACTIVE,
        "inactive": models.EmployeeStatus.INACTIVE,
        "on leave": models.EmployeeStatus.ON_LEAVE,
        "on_leave": models.EmployeeStatus.ON_LEAVE,
        "terminated": models.EmployeeStatus.TERMINATED,
    }
    return mapping.get(v, models.EmployeeStatus.ACTIVE)

# -------------------------------------------------
# Department Services
# -------------------------------------------------

def get_department(db: Session, department_id: int):
    return (
        db.query(models.Department)
        .filter(models.Department.id == department_id)
        .first()
    )

def get_department_by_name(db: Session, name: str):
    return (
        db.query(models.Department)
        .filter(models.Department.name == name)
        .first()
    )

def get_departments(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Department)
        .order_by(models.Department.id.desc())
        .offset(skip).limit(limit).all()
    )

def create_department(db: Session, department: schemas.DepartmentCreate):
    if get_department_by_name(db, name=department.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name already exists",
        )
    db_department = models.Department(**department.model_dump())
    db.add(db_department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Department name already exists",
        )
    db.refresh(db_department)
    return db_department

def update_department(db: Session, department_id: int, department_update: schemas.DepartmentUpdate):
    db_department = get_department(db, department_id)
    if not db_department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

    if department_update.name and department_update.name != db_department.name:
        existing_department = get_department_by_name(db, name=department_update.name)
        if existing_department and existing_department.id != department_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New department name already exists",
            )

    update_data = department_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_department, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to unique constraint",
        )
    db.refresh(db_department)
    return db_department

def delete_department(db: Session, department_id: int):
    db_department = get_department(db, department_id)
    if not db_department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    if db_department.employees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department with employees",
        )
    db.delete(db_department)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete department due to related records",
        )
    return {"message": "Department deleted successfully"}

# -------------------------------------------------
# Position Services
# -------------------------------------------------

def get_position(db: Session, position_id: int):
    return (
        db.query(models.Position)
        .filter(models.Position.id == position_id)
        .first()
    )

def get_position_by_name(db: Session, name: str):
    return (
        db.query(models.Position)
        .filter(models.Position.name == name)
        .first()
    )

def get_positions(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Position)
        .order_by(models.Position.id.desc())
        .offset(skip).limit(limit).all()
    )

def create_position(db: Session, position: schemas.PositionCreate):
    if get_position_by_name(db, name=position.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position name already exists",
        )
    db_position = models.Position(**position.model_dump())
    db.add(db_position)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Position name already exists",
        )
    db.refresh(db_position)
    return db_position

def update_position(db: Session, position_id: int, position_update: schemas.PositionUpdate):
    db_position = get_position(db, position_id)
    if not db_position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    if position_update.name and position_update.name != db_position.name:
        existing_position = get_position_by_name(db, name=position_update.name)
        if existing_position and existing_position.id != position_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="New position name already exists",
            )

    update_data = position_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_position, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to unique constraint",
        )
    db.refresh(db_position)
    return db_position

def delete_position(db: Session, position_id: int):
    db_position = get_position(db, position_id)
    if not db_position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    if db_position.employees:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete position with employees",
        )
    db.delete(db_position)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete position due to related records",
        )
    return {"message": "Position deleted successfully"}

# -------------------------------------------------
# Employee Services
# -------------------------------------------------

def get_employee(db: Session, employee_id: int):
    return (
        db.query(models.Employee)
        .options(
            joinedload(models.Employee.department),
            joinedload(models.Employee.position),
        )
        .filter(models.Employee.id == employee_id)
        .first()
    )

def get_employee_by_id_card_number(db: Session, id_card_number: str):
    return (
        db.query(models.Employee)
        .filter(models.Employee.id_card_number == id_card_number)
        .first()
    )

def get_employee_by_employee_id_number(db: Session, employee_id_number: str):
    return (
        db.query(models.Employee)
        .filter(models.Employee.employee_id_number == employee_id_number)
        .first()
    )

def get_employees(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Employee)
        .options(
            joinedload(models.Employee.department),
            joinedload(models.Employee.position),
        )
        .order_by(models.Employee.id.desc())
        .offset(skip).limit(limit).all()
    )

def create_employee(db: Session, employee: schemas.EmployeeCreate):
    if employee.id_card_number and get_employee_by_id_card_number(db, id_card_number=employee.id_card_number):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ID card number already exists")
    if get_employee_by_employee_id_number(db, employee_id_number=employee.employee_id_number):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee ID number already exists")

    data = employee.model_dump()
    # ถ้าต้องการ normalize enum ที่ไม่ได้ส่งมาเป๊ะ ให้เปิดใช้บรรทัดถัดไป
    # data["employee_status"] = _normalize_employee_status(data.get("employee_status"))

    db_employee = models.Employee(**data)
    db.add(db_employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee unique constraint violated (ID card or employee ID number)",
        )
    db.refresh(db_employee)
    # preload ความสัมพันธ์หลักก่อนคืน (กัน DetachedInstanceError)
    db.refresh(db_employee, attribute_names=["department", "position"])
    return db_employee

def update_employee(db: Session, employee_id: int, employee_update: schemas.EmployeeUpdate):
    db_employee = get_employee(db, employee_id)
    if not db_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    update_data = employee_update.model_dump(exclude_unset=True)

    if "id_card_number" in update_data and update_data["id_card_number"]:
        if update_data["id_card_number"] != db_employee.id_card_number:
            existing = get_employee_by_id_card_number(db, id_card_number=update_data["id_card_number"])
            if existing and existing.id != employee_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="New ID card number already exists")

    if "employee_id_number" in update_data and update_data["employee_id_number"]:
        if update_data["employee_id_number"] != db_employee.employee_id_number:
            existing = get_employee_by_employee_id_number(db, employee_id_number=update_data["employee_id_number"])
            if existing and existing.id != employee_id:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="New employee ID number already exists")

    # ถ้าต้องการ normalize enum ที่ไม่ได้ส่งมาเป๊ะ ให้เปิดใช้บรรทัดถัดไป
    # if "employee_status" in update_data:
    #     update_data["employee_status"] = _normalize_employee_status(update_data["employee_status"])

    for key, value in update_data.items():
        setattr(db_employee, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update failed due to unique constraint",
        )

    db.refresh(db_employee)
    db.refresh(db_employee, attribute_names=["department", "position"])
    return db_employee

def delete_employee(db: Session, employee_id: int):
    db_employee = get_employee(db, employee_id)
    if not db_employee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    if _has_related_records(db_employee):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete employee with related time entries or leave requests.",
        )

    try:
        db.delete(db_employee)
        db.commit()
    except IntegrityError:
        db.rollback()
        # ครอบไว้กันกรณีมี FK อื่น ๆ ที่ยังไม่เปิดใช้ relations ฝั่ง ORM
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete employee due to related records (foreign key constraints).",
        )
    return {"message": "Employee deleted successfully"}
