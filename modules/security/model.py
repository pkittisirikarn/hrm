from __future__ import annotations
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint

# Base ของโปรเจกต์ (ลอง 2 path เผื่อ)
try:
    from database.base import Base
except ImportError:
    from database.connection import Base

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class AppModule(str, Enum):
    DASHBOARD = "dashboard"
    EMPLOYEES = "employees"
    RECRUITMENT = "recruitment"
    PAYROLL = "payroll"
    MEETING = "meeting"
    TIME_TRACKING = "time_tracking"
    PERSONAL_PROFILE = "personal_profile"

class ModulePermission(Base):
    __tablename__ = "module_permissions"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    module = Column(SQLEnum(AppModule), nullable=False)
    can_view = Column(Boolean, default=True, nullable=False)
    can_edit = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("employee_id", "module", name="uq_perm_employee_module"),)
