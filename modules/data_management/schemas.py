# modules/data_management/schemas.py
from __future__ import annotations

from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict

from modules.data_management import models  # ใช้ Enums จาก models.EmployeeStatus

# -------------------------------------------------
# Department Schemas
# -------------------------------------------------

class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="ชื่อแผนก")

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="ชื่อแผนก")

class DepartmentInDB(DepartmentBase):
    id: int = Field(..., gt=0, description="ID ของแผนก")
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------
# Position Schemas
# -------------------------------------------------

class PositionBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="ชื่อตำแหน่ง")

class PositionCreate(PositionBase):
    pass

class PositionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="ชื่อตำแหน่ง")

class PositionInDB(PositionBase):
    id: int = Field(..., gt=0, description="ID ของตำแหน่ง")
    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------
# Employee Schemas (เข้มงวดสำหรับรับข้อมูลเข้า)
# -------------------------------------------------

class EmployeeBase(BaseModel):
    employee_id_number: str = Field(..., min_length=1, max_length=50, description="รหัสพนักงาน")
    first_name: str = Field(..., min_length=2, max_length=100, description="ชื่อจริง")
    last_name: str = Field(..., min_length=2, max_length=100, description="นามสกุล")
    date_of_birth: date = Field(..., description="วันเกิด (YYYY-MM-DD)")
    address: str = Field(..., description="ที่อยู่")
    id_card_number: Optional[str] = Field(None, min_length=13, max_length=13, description="เลขบัตรประชาชน (13 หลัก)")
    profile_picture_path: Optional[str] = Field(None, description="Path รูปโปรไฟล์")
    application_documents_paths: Optional[str] = Field(None, description="Path เอกสารสมัครงาน (JSON string)")
    bank_account_number: Optional[str] = Field(None, description="เลขบัญชีธนาคาร")
    bank_name: Optional[str] = Field(None, description="ชื่อธนาคาร")
    email: Optional[EmailStr] = Field(None, description="อีเมลองค์กร/อีเมลที่ติดต่อได้")
    phone_number: Optional[str] = Field(
        None,
        description="หมายเลขโทรศัพท์ (รองรับ +, -, เว้นวรรค)",
        pattern=r'^\+?[0-9\- ]{7,20}$'
    )
    hire_date: date = Field(..., description="วันที่เริ่มทำงาน (YYYY-MM-DD)")
    termination_date: Optional[date] = Field(None, description="วันที่สิ้นสุดการทำงาน (YYYY-MM-DD)")
    employee_status: models.EmployeeStatus = Field(models.EmployeeStatus.ACTIVE, description="สถานะพนักงาน")
    department_id: int = Field(..., gt=0, description="ID แผนก")
    position_id: int = Field(..., gt=0, description="ID ตำแหน่ง")

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(BaseModel):
    employee_id_number: Optional[str] = Field(None, min_length=1, max_length=50, description="รหัสพนักงาน")
    first_name: Optional[str] = Field(None, min_length=2, max_length=100, description="ชื่อจริง")
    last_name: Optional[str] = Field(None, min_length=2, max_length=100, description="นามสกุล")
    date_of_birth: Optional[date] = Field(None, description="วันเกิด (YYYY-MM-DD)")
    address: Optional[str] = Field(None, description="ที่อยู่")
    id_card_number: Optional[str] = Field(None, min_length=13, max_length=13, description="เลขบัตรประชาชน (13 หลัก)")
    profile_picture_path: Optional[str] = Field(None, description="Path รูปโปรไฟล์")
    application_documents_paths: Optional[str] = Field(None, description="Path เอกสารสมัครงาน (JSON string)")
    bank_account_number: Optional[str] = Field(None, description="เลขบัญชีธนาคาร")
    bank_name: Optional[str] = Field(None, description="ชื่อธนาคาร")
    email: Optional[EmailStr] = Field(None, description="อีเมลองค์กร/อีเมลที่ติดต่อได้")
    phone_number: Optional[str] = Field(
        None,
        description="หมายเลขโทรศัพท์ (รองรับ +, -, เว้นวรรค)",
        pattern=r'^\+?[0-9\- ]{7,20}$'
    )
    hire_date: Optional[date] = Field(None, description="วันที่เริ่มทำงาน (YYYY-MM-DD)")
    termination_date: Optional[date] = Field(None, description="วันที่สิ้นสุดการทำงาน (YYYY-MM-DD)")
    employee_status: Optional[models.EmployeeStatus] = Field(None, description="สถานะพนักงาน")
    department_id: Optional[int] = Field(None, gt=0, description="ID แผนก")
    position_id: Optional[int] = Field(None, gt=0, description="ID ตำแหน่ง")


# -------------------------------------------------
# Employee “Out” (ผ่อนปรนสำหรับส่งออก/แสดงผล)
# -------------------------------------------------

class EmployeeOut(BaseModel):
    """
    ใช้สำหรับ response_model ใน endpoints ที่ 'อ่าน' ข้อมูล เพื่อกัน 500
    กรณีข้อมูลเก่ามี last_name ว่าง หรืออีเมลเป็นโดเมนพิเศษ (.local)
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id_number: Optional[str] = None
    first_name: str = ""         # ไม่บังคับ min_length
    last_name: str = ""          # ไม่บังคับ min_length
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    id_card_number: Optional[str] = None
    profile_picture_path: Optional[str] = None
    application_documents_paths: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    email: Optional[str] = None  # เลิกใช้ EmailStr เพื่อรองรับ .local
    phone_number: Optional[str] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    employee_status: Optional[models.EmployeeStatus] = None
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    role: Optional[str] = None

    # ถ้า endpoint ใด pre-load ความสัมพันธ์ไว้ ก็จะ map มาได้
    department: Optional[DepartmentInDB] = None
    position: Optional[PositionInDB] = None

# ----- Backward-compat names (สำหรับโค้ดเก่าที่ยังใช้ EmployeeInDB) -----
EmployeeRead = EmployeeOut
EmployeeInDB = EmployeeOut