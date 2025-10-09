# modules/data_management/models.py
from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database.base import Base
import enum

class EmployeeStatus(enum.Enum):
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    ON_LEAVE = "On Leave"
    TERMINATED = "Terminated"

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    employees = relationship("Employee", back_populates="department")

class Position(Base):
    __tablename__ = "positions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    employees = relationship("Employee", back_populates="position")

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id_number = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, index=True, nullable=False)
    last_name = Column(String, index=True, nullable=False)
    date_of_birth = Column(Date, nullable=False)
    address = Column(Text, nullable=False)
    id_card_number = Column(String, unique=True, nullable=True)
    profile_picture_path = Column(String, nullable=True)
    application_documents_paths = Column(Text, nullable=True)
    bank_account_number = Column(String, nullable=True)
    bank_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)
    hire_date = Column(Date, nullable=False)
    termination_date = Column(Date, nullable=True)
    employee_status = Column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)

    # relations
    department = relationship("Department", back_populates="employees")
    position = relationship("Position", back_populates="employees")

    # time-tracking relations
    time_entries = relationship("TimeEntry", back_populates="employee")
    leave_requests = relationship("LeaveRequest", back_populates="employee")
    ot_requests = relationship("OvertimeRequest", back_populates="employee")

    # payroll relations
    salary_structure = relationship("SalaryStructure", back_populates="employee", uselist=False)
    employee_allowances = relationship("EmployeeAllowance", back_populates="employee")
    employee_deductions = relationship("EmployeeDeduction", back_populates="employee")
    payroll_entries = relationship("PayrollEntry", back_populates="employee")
