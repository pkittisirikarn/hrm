from __future__ import annotations
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column, Integer, String, Enum as SQLEnum, DateTime, Text, Float, Boolean,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship

from database.connection import Base  # ใช้ Base ที่โปรเจคมีอยู่แล้ว

class FileKind(str, Enum):
    PHOTO = "photo"
    RESUME = "resume"      # เรซูเม่/แฟ้มสมัครงาน
    ATTACHMENT = "attachment"  # เอกสารประกอบอื่น ๆ

class CandidateStatus(str, Enum):
    BACKGROUND_CHECK = "background_check"        # อยู่ระหว่างตรวจสอบประวัติ
    WAITING_SCHEDULE = "waiting_schedule"        # รอนัดหมายสัมภาษณ์งาน
    SCHEDULED = "scheduled"                      # นัดหมายสัมภาษณ์
    PASSED = "passed"                            # ผ่านการสัมภาษณ์
    FAILED = "failed"                            # ไม่ผ่านการสัมภาษณ์
    PENDING_RESULT = "pending_result"            # รอแจ้งผล

STATUS_THAI = {
    CandidateStatus.BACKGROUND_CHECK: "อยู่ระหว่างตรวจสอบประวัติ",
    CandidateStatus.WAITING_SCHEDULE: "รอนัดหมายสัมภาษณ์งาน",
    CandidateStatus.SCHEDULED: "นัดหมายสัมภาษณ์",
    CandidateStatus.PASSED: "ผ่านการสัมภาษณ์",
    CandidateStatus.FAILED: "ไม่ผ่านการสัมภาษณ์",
    CandidateStatus.PENDING_RESULT: "รอแจ้งผล",
}

class Candidate(Base):
    __tablename__ = "candidates"
    id = Column(Integer, primary_key=True)

    # ใหม่: แยกชื่อ-นามสกุล + วุฒิ + รูปภาพ
    first_name = Column(String(120), nullable=False, index=True)
    last_name = Column(String(120), nullable=False, index=True)
    full_name = Column(String(200), nullable=False, index=True)  # เก็บรวมเพื่อค้นหาเร็ว
    education = Column(String(200), nullable=True)               # วุฒิการศึกษา
    photo_url = Column(Text, nullable=True)                      # พาธไฟล์รูป

    email = Column(String(200), nullable=True, index=True)
    phone = Column(String(50), nullable=True)
    position_applied = Column(String(200), nullable=True, index=True)
    department = Column(String(120), nullable=True, index=True)
    current_company = Column(String(200), nullable=True)
    years_experience = Column(Float, default=0.0)
    expected_salary = Column(Float, nullable=True)
    current_salary = Column(Float, nullable=True)
    source = Column(String(120), nullable=True, index=True)
    resume_url = Column(Text, nullable=True)  # (เก็บได้ แต่จะย้ายไปตารางไฟล์หลายรายการแทน)
    skills = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    status = Column(SQLEnum(CandidateStatus), nullable=False, default=CandidateStatus.WAITING_SCHEDULE, index=True)
    stage_updated_at = Column(DateTime, default=datetime.utcnow)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # ใหม่: ความสัมพันธ์ไฟล์แนบหลายไฟล์
    files = relationship("CandidateFile", back_populates="candidate", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")

Index("ix_candidates_quick", Candidate.full_name, Candidate.position_applied, Candidate.status)

class CandidateFile(Base):
    __tablename__ = "candidate_files"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    file_kind = Column(SQLEnum(FileKind), nullable=False, index=True)
    file_url = Column(Text, nullable=False)           # พาธสำหรับเสิร์ฟจากเว็บ (เช่น /static/uploads/..)
    original_name = Column(String(255), nullable=True)
    content_type = Column(String(120), nullable=True)
    size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    candidate = relationship("Candidate", back_populates="files")

class Interview(Base):
    __tablename__ = "candidate_interviews"

    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)

    mode = Column(String(50), nullable=True)  # online/onsite/phone
    location = Column(String(250), nullable=True)  # ที่อยู่/ลิงก์ประชุม
    interviewers = Column(Text, nullable=True)  # รายชื่อคอมม่า หรือเก็บเป็น JSON ทีหลัง
    result = Column(String(50), nullable=True)  # pass/fail/pending
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    candidate = relationship("Candidate", back_populates="interviews")