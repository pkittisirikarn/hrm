# modules/payroll/schemas.py
from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

from .models import PayrollRunStatus, PaymentStatus, StatusEnum


# =========================================================
# Allowance Types
# =========================================================
class AllowanceTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_taxable: bool = True
    is_active: bool = True
    formula: Optional[str] = None
    formula_variable_name: Optional[str] = None


class AllowanceTypeCreate(AllowanceTypeBase):
    pass


class AllowanceTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_taxable: Optional[bool] = None
    is_active: Optional[bool] = None
    formula: Optional[str] = None
    formula_variable_name: Optional[str] = None


class AllowanceTypeInDB(AllowanceTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# =========================================================
# Deduction Types
# =========================================================
class DeductionTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_mandatory: bool = False
    is_active: bool = True
    formula: Optional[str] = None
    formula_variable_name: Optional[str] = None


class DeductionTypeCreate(DeductionTypeBase):
    pass


class DeductionTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None
    is_active: Optional[bool] = None
    formula: Optional[str] = None
    formula_variable_name: Optional[str] = None


class DeductionTypeInDB(DeductionTypeBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# =========================================================
# Salary Structure
# =========================================================
class SalaryStructureBase(BaseModel):
    employee_id: int
    base_salary: float
    effective_date: date


class SalaryStructureCreate(SalaryStructureBase):
    pass


class SalaryStructureUpdate(BaseModel):
    employee_id: Optional[int] = None
    base_salary: Optional[float] = None
    effective_date: Optional[date] = None


class SalaryStructureInDB(SalaryStructureBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# =========================================================
# Employee Allowances / Deductions
# =========================================================
class EmployeeAllowanceBase(BaseModel):
    employee_id: int
    allowance_type_id: int
    amount: float
    effective_date: date
    status: StatusEnum = StatusEnum.ACTIVE


class EmployeeAllowanceCreate(EmployeeAllowanceBase):
    pass


class EmployeeAllowanceUpdate(BaseModel):
    employee_id: Optional[int] = None
    allowance_type_id: Optional[int] = None
    amount: Optional[float] = None
    effective_date: Optional[date] = None
    status: Optional[StatusEnum] = None


class EmployeeAllowanceInDB(EmployeeAllowanceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EmployeeDeductionBase(BaseModel):
    employee_id: int
    deduction_type_id: int
    amount: float
    effective_date: date
    status: StatusEnum = StatusEnum.ACTIVE


class EmployeeDeductionCreate(EmployeeDeductionBase):
    pass


class EmployeeDeductionUpdate(BaseModel):
    employee_id: Optional[int] = None
    deduction_type_id: Optional[int] = None
    amount: Optional[float] = None
    effective_date: Optional[date] = None
    status: Optional[StatusEnum] = None


class EmployeeDeductionInDB(EmployeeDeductionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# =========================================================
# Payroll Runs
# =========================================================
# หมายเหตุ: ใช้ alias + populate_by_name เพื่อรองรับทั้งชื่อใหม่/เก่า
# - ส่ง period_start/period_end ได้
# - หรือส่ง pay_period_start/pay_period_end ก็ได้
class PayrollRunCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    scheme_id: int = 1
    period_start: date = Field(..., alias="pay_period_start")
    period_end: date = Field(..., alias="pay_period_end")
    notes: Optional[str] = None


class PayrollRunUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    period_start: Optional[date] = Field(None, alias="pay_period_start")
    period_end: Optional[date] = Field(None, alias="pay_period_end")
    status: Optional[PayrollRunStatus] = None
    total_amount_paid: Optional[float] = None
    notes: Optional[str] = None


class PayrollRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scheme_id: int
    period_start: date
    period_end: date
    status: PayrollRunStatus
    created_at: datetime
    run_date: Optional[date] = None
    pay_period_start: Optional[date] = None
    pay_period_end: Optional[date] = None
    total_amount_paid: float
    notes: Optional[str] = None


# alias ให้เข้ากับชื่อที่ route ใช้อยู่เดิม
class PayrollRunInDB(PayrollRunRead):
    pass


# =========================================================
# Payroll Entries
# =========================================================
class PayrollEntryBase(BaseModel):
    payroll_run_id: int
    employee_id: int
    gross_salary: float
    net_salary: float
    calculated_allowances_json: Optional[str] = None
    calculated_deductions_json: Optional[str] = None
    payment_date: Optional[date] = None
    payment_status: PaymentStatus = PaymentStatus.PENDING


class PayrollEntryCreate(PayrollEntryBase):
    pass


class PayrollEntryUpdate(BaseModel):
    payroll_run_id: Optional[int] = None
    employee_id: Optional[int] = None
    gross_salary: Optional[float] = None
    net_salary: Optional[float] = None
    calculated_allowances_json: Optional[str] = None
    calculated_deductions_json: Optional[str] = None
    payment_date: Optional[date] = None
    payment_status: Optional[PaymentStatus] = None

class PayrollEntryInDB(PayrollEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int

class PayrollReportRow(BaseModel):
    employee_id: int
    employee_name: str
    payroll_run_id: int
    period_start: date
    period_end: date
    base_salary: float
    allowances_total: float
    deductions_total: float
    gross_salary: float
    net_salary: float
    payment_status: PaymentStatus
    payment_date: Optional[date] = None

class PayrollReport(BaseModel):
    month: str
    rows: List[PayrollReportRow]
    totals: dict