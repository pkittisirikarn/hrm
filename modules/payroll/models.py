# modules/payroll/models.py
from __future__ import annotations

from datetime import date, datetime
from enum import Enum as PyEnum
import enum

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Text, Enum, Float, text
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

# ใช้ Base เดียวกับทั้งโปรเจกต์ (อย่าเรียก declarative_base() ซ้ำ)
from database.base import Base

# สำคัญ: import Employee เพื่อให้ mapper เห็นคลาสนี้ใน registry เดียวกัน
# (ถ้า Employee อยู่ที่อื่น ให้แก้ path import ให้ตรงโปรเจกต์ของคุณ)
from modules.data_management.models import Employee  # noqa: F401


# ----------------- Enums -----------------
class StatusEnum(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PayrollRunStatus(str, PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PaymentStatus(enum.Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ----------------- Scheme / Formula -----------------
class PayrollScheme(Base):
    __tablename__ = "payroll_schemes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    formulas = relationship("PayrollFormula", back_populates="scheme", cascade="all, delete-orphan")
    runs = relationship("PayrollRun", back_populates="scheme")


class PayrollFormula(Base):
    __tablename__ = "payroll_formulas"

    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(Integer, ForeignKey("payroll_schemes.id"), nullable=False)
    code = Column(String, nullable=False)
    label = Column(String, nullable=False)
    expression = Column(Text, nullable=False)
    sort_order = Column(Integer, default=100, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    scheme = relationship("PayrollScheme", back_populates="formulas")


# ----------------- Master types -----------------
class AllowanceType(Base):
    __tablename__ = "allowance_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_taxable = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    formula = Column(Text, nullable=True)
    formula_variable_name = Column(String, nullable=True)

    employee_allowances = relationship("EmployeeAllowance", back_populates="allowance_type")


class DeductionType(Base):
    __tablename__ = "deduction_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    formula = Column(Text, nullable=True)
    formula_variable_name = Column(String, nullable=True)

    employee_deductions = relationship("EmployeeDeduction", back_populates="deduction_type")


# ----------------- Employee config -----------------
class SalaryStructure(Base):
    __tablename__ = "salary_structures"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    base_salary = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False)

    # ป้องกันชนกับ backref/back_populates ที่อาจประกาศในโมดูล Employee:
    # ใช้ความสัมพันธ์ทางเดียวพอ ไม่ใส่ backref/back_populates
    employee = relationship("Employee")


class EmployeeAllowance(Base):
    __tablename__ = "employee_allowances"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    allowance_type_id = Column(Integer, ForeignKey("allowance_types.id"), nullable=False)
    amount = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.ACTIVE, nullable=False)

    # ฝั่ง Employee สมมุติมี property รองรับอยู่แล้ว
    employee = relationship("Employee")
    allowance_type = relationship("AllowanceType", back_populates="employee_allowances")


class EmployeeDeduction(Base):
    __tablename__ = "employee_deductions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    deduction_type_id = Column(Integer, ForeignKey("deduction_types.id"), nullable=False)
    amount = Column(Float, nullable=False)
    effective_date = Column(Date, nullable=False)
    status = Column(SAEnum(StatusEnum), default=StatusEnum.ACTIVE, nullable=False)

    employee = relationship("Employee")
    deduction_type = relationship("DeductionType", back_populates="employee_deductions")


# ----------------- Payroll run / items -----------------
class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id = Column(Integer, primary_key=True, index=True)
    scheme_id = Column(Integer, ForeignKey("payroll_schemes.id"), nullable=False)

    # ฟิลด์หลัก
    period_start = Column(Date, nullable=False)
    period_end   = Column(Date, nullable=False)

    status = Column(SAEnum(PayrollRunStatus), nullable=False, default=PayrollRunStatus.PENDING, server_default="PENDING")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ฟิลด์ legacy (ยังคงไว้ แต่ไม่จำเป็นต้องใช้)
    run_date          = Column(Date, nullable=True)
    pay_period_start  = Column(Date, nullable=True)
    pay_period_end    = Column(Date, nullable=True)

    # ป้องกัน NOT NULL
    total_amount_paid = Column(Float, nullable=False, default=0.0, server_default=text("0"))

    notes = Column(Text, nullable=True)

    # ความสัมพันธ์
    scheme = relationship("PayrollScheme", back_populates="runs")
    items = relationship("PayrollItem", back_populates="run", cascade="all, delete-orphan")
    payroll_entries = relationship("PayrollEntry", back_populates="payroll_run", cascade="all, delete-orphan")


class PayrollEntry(Base):
    __tablename__ = "payroll_entries"

    id = Column(Integer, primary_key=True, index=True)
    payroll_run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False)
    employee_id    = Column(Integer, ForeignKey("employees.id"), nullable=False)

    gross_salary   = Column(Float, nullable=False)
    net_salary     = Column(Float, nullable=False)

    calculated_allowances_json = Column(Text, nullable=True)
    calculated_deductions_json = Column(Text, nullable=True)

    payment_date   = Column(Date, nullable=True)
    payment_status = Column(SAEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False)

    payroll_run = relationship("PayrollRun", back_populates="payroll_entries")
    # ทำทางเดียวเพื่อเลี่ยงข้อกำหนดฝั่ง Employee
    employee    = relationship("Employee")


class PayrollItem(Base):
    __tablename__ = "payroll_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("payroll_runs.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    base_salary = Column(Float, default=0.0)
    hourly_rate = Column(Float, default=0.0)

    ot_hours = Column(Float, default=0.0)
    ot_pay   = Column(Float, default=0.0)

    leave_unpaid_hours = Column(Float, default=0.0)
    leave_deduction    = Column(Float, default=0.0)

    gross_pay = Column(Float, default=0.0)
    net_pay   = Column(Float, default=0.0)

    breakdown_json = Column(Text, nullable=True)

    run = relationship("PayrollRun", back_populates="items")
    # ทางเดียว เพื่อไม่ต้องไปแก้โมเดล Employee
    employee = relationship("Employee")
