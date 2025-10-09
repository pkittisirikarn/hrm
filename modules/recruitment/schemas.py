from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from .models import CandidateStatus

class InterviewBase(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    mode: Optional[str] = None
    location: Optional[str] = None
    interviewers: Optional[str] = None
    result: Optional[str] = None
    notes: Optional[str] = None

class InterviewCreate(InterviewBase):
    candidate_id: int

class InterviewUpdate(InterviewBase):
    pass

class InterviewOut(InterviewBase):
    id: int
    candidate_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CandidateFileOut(BaseModel):
    id: int
    file_kind: str
    file_url: str
    original_name: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CandidateBase(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    position_applied: Optional[str] = None
    department: Optional[str] = None
    education: Optional[str] = None
    years_experience: Optional[float] = 0.0
    expected_salary: Optional[float] = None
    source: Optional[str] = None
    resume_url: Optional[str] = None
    skills: Optional[str] = None
    notes: Optional[str] = None
    status: CandidateStatus = Field(default=CandidateStatus.WAITING_SCHEDULE)

class CandidateCreate(CandidateBase):
    pass

class CandidateUpdate(CandidateBase):
    pass

class CandidateOut(BaseModel):
    id: int
    # ✅ เพิ่มฟิลด์ที่หน้าแก้ไขต้องใช้
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: str

    email: Optional[str] = None
    phone: Optional[str] = None
    position_applied: Optional[str] = None
    department: Optional[str] = None
    education: Optional[str] = None
    years_experience: Optional[float] = None
    expected_salary: Optional[float] = None
    source: Optional[str] = None
    skills: Optional[str] = None
    resume_url: Optional[str] = None

    # ✅ รูปผู้สมัคร (ไว้โชว์ใน list + preload ในฟอร์ม)
    photo_url: Optional[str] = None

    notes: Optional[str] = None
    status: CandidateStatus
    stage_updated_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class StatsOverview(BaseModel):
    total: int
    by_status: dict
    by_source: dict
    last_30d: List[dict]  # [{"date":"2025-10-01","count":3}, ...]