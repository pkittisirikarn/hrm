from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from core.templates import templates
# from starlette.templating import Jinja2Templates

from database.connection import get_db
from .models import Candidate, CandidateFile, CandidateStatus, STATUS_THAI
from .schemas import CandidateOut, CandidateFileOut
from .services import save_upload, ALLOWED_IMAGE, ALLOWED_PDF  # ต้องมีไฟล์ services ตามที่เคยให้

api = APIRouter(prefix="/api/v1/recruitment", tags=["recruitment"])
pages = APIRouter()
# templates = Jinja2Templates(directory="templates")

# ---------- PAGES ----------
@pages.get("/recruitment/dashboard")
def recruitment_dashboard(request: Request):
    return templates.TemplateResponse("recruitment/dashboard.html", {"request": request})

@pages.get("/recruitment/candidates")
def recruitment_candidates_page(request: Request):
    return templates.TemplateResponse("recruitment/candidates.html", {"request": request, "status_th": STATUS_THAI})

@pages.get("/recruitment/candidate/new")
def recruitment_candidate_new(request: Request):
    return templates.TemplateResponse("recruitment/candidate_form.html", {"request": request, "candidate_id": None, "status_th": STATUS_THAI})

@pages.get("/recruitment/candidate/edit")
def recruitment_candidate_edit(request: Request, id: int = Query(...)):
    return templates.TemplateResponse("recruitment/candidate_form.html", {"request": request, "candidate_id": id, "status_th": STATUS_THAI})

# ---------- API: Candidates ----------
@api.get("/candidates/", response_model=List[CandidateOut])
def list_candidates(
    q: Optional[str] = None,
    status: Optional[CandidateStatus] = None,
    source: Optional[str] = None,
    dept: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Candidate).filter(Candidate.is_active == True)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Candidate.full_name.ilike(like)) |
            (Candidate.email.ilike(like)) |
            (Candidate.position_applied.ilike(like))
        )
    if status:
        query = query.filter(Candidate.status == status)
    if source:
        query = query.filter(Candidate.source == source)
    if dept:
        query = query.filter(Candidate.department == dept)
    return query.order_by(Candidate.created_at.desc()).offset(skip).limit(limit).all()

# ---------- (คง GET /candidates/{id} ไว้เหมือนเดิม) ----------
@api.get("/candidates/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    obj = db.get(Candidate, candidate_id)
    if not obj or not obj.is_active:
        raise HTTPException(404, "Candidate not found")
    return obj

# ---------- ✅ อัปเดตผู้สมัคร + แนบไฟล์เพิ่ม (multipart) ----------
@api.put("/candidates/{candidate_id}/update-with-files", response_model=CandidateOut)
async def update_candidate_with_files(
    candidate_id: int,
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    position_applied: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    years_experience: Optional[float] = Form(None),
    expected_salary: Optional[float] = Form(None),
    status: Optional[CandidateStatus] = Form(None),
    notes: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    skills: Optional[str] = Form(None),
    resume_url: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    attachments: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    obj = db.get(Candidate, candidate_id)
    if not obj or not obj.is_active:
        raise HTTPException(404, "Candidate not found")

    # อัปเดตค่าที่ส่งมาเท่านั้น
    def set_if(value, attr):
        if value is not None:
            setattr(obj, attr, value)

    set_if(first_name, "first_name")
    set_if(last_name, "last_name")
    # full_name ให้ sync อัตโนมัติเมื่อชื่อ/นามสกุลเปลี่ยน
    if first_name is not None or last_name is not None:
        fn = first_name if first_name is not None else (obj.first_name or "")
        ln = last_name if last_name is not None else (obj.last_name or "")
        obj.full_name = f"{(fn or '').strip()} {(ln or '').strip()}".strip()

    set_if(email, "email")
    set_if(phone, "phone")
    set_if(position_applied, "position_applied")
    set_if(department, "department")
    set_if(education, "education")
    set_if(years_experience, "years_experience")
    set_if(expected_salary, "expected_salary")
    set_if(status, "status")
    set_if(notes, "notes")
    set_if(source, "source")
    set_if(skills, "skills")
    set_if(resume_url, "resume_url")

    # อัปโหลดรูปใหม่ (ถ้าส่งมา) — ยังไม่ลบไฟล์เก่า (ทำได้ภายหลัง)
    if photo is not None and (photo.filename or '').strip():
        web_path, _ = save_upload(photo, str(obj.id), ALLOWED_IMAGE)
        obj.photo_url = web_path

    # แนบไฟล์ PDF เพิ่ม
    if attachments:
        for f in attachments:
            if not (f and (f.filename or '').strip()):
                continue
            web_path, size = save_upload(f, str(obj.id), ALLOWED_PDF)
            db.add(CandidateFile(
                candidate_id=obj.id,
                file_kind="resume",
                file_url=web_path,
                original_name=f.filename,
                content_type=f.content_type,
                size=size,
            ))

    obj.updated_at = datetime.utcnow()
    db.commit(); db.refresh(obj)
    return obj

@api.delete("/candidates/{candidate_id}")
def soft_delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    obj = db.get(Candidate, candidate_id)
    if not obj or not obj.is_active:
        raise HTTPException(404, "Candidate not found")
    obj.is_active = False
    obj.deleted_at = datetime.utcnow()
    db.commit()
    return {"ok": True}

# สร้างผู้สมัคร (multipart + อัปโหลดไฟล์)
@api.post("/candidates/create-with-files", response_model=CandidateOut)
async def create_candidate_with_files(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    position_applied: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    education: Optional[str] = Form(None),
    years_experience: Optional[float] = Form(0.0),
    expected_salary: Optional[float] = Form(None),
    status: CandidateStatus = Form(CandidateStatus.WAITING_SCHEDULE),
    notes: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    attachments: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
):
    obj = Candidate(
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        full_name=f"{first_name.strip()} {last_name.strip()}",
        email=email, phone=phone,
        position_applied=position_applied, department=department,
        education=education, years_experience=years_experience,
        expected_salary=expected_salary, status=status, notes=notes,
    )
    db.add(obj); db.commit(); db.refresh(obj)

    # อัปโหลดไฟล์
    subdir = str(obj.id)
    if photo is not None and (photo.filename or '').strip():
        web_path, size = save_upload(photo, subdir, ALLOWED_IMAGE)
        obj.photo_url = web_path

    if attachments:
        for f in attachments:
            if not (f and (f.filename or '').strip()):
                continue
            web_path, size = save_upload(f, subdir, ALLOWED_PDF)
            db.add(CandidateFile(
                candidate_id=obj.id,
                file_kind="resume",
                file_url=web_path,
                original_name=f.filename,
                content_type=f.content_type,
                size=size,
            ))

    obj.updated_at = datetime.utcnow()
    db.commit(); db.refresh(obj)
    return obj

# ไฟล์แนบของผู้สมัคร
@api.get("/candidates/{candidate_id}/files", response_model=List[CandidateFileOut])
def list_candidate_files(candidate_id: int, db: Session = Depends(get_db)):
    return (
        db.query(CandidateFile)
        .filter(CandidateFile.candidate_id == candidate_id)
        .order_by(CandidateFile.created_at.desc())
        .all()
    )

# ---------- API: Stats (SQLite-compatible) ----------
@api.get("/stats/overview")
def stats_overview(db: Session = Depends(get_db)):
    total = (
        db.query(func.count(Candidate.id))
        .filter(Candidate.is_active == True)
        .scalar()
        or 0
    )

    # by_status
    rows = (
        db.query(Candidate.status, func.count(Candidate.id))
        .filter(Candidate.is_active == True)
        .group_by(Candidate.status)
        .all()
    )
    by_status = {s.value: c for s, c in rows}

    # by_source (ยังคงไว้ เผื่อใช้กราฟอื่น)
    rows2 = (
        db.query(
            func.coalesce(func.nullif(func.trim(Candidate.source), ""), "ไม่ระบุ").label("src"),
            func.count(Candidate.id),
        )
        .filter(Candidate.is_active == True)
        .group_by("src")
        .all()
    )
    by_source = {label: cnt for label, cnt in rows2}

    # ✅ by_position (ตำแหน่งที่สมัคร)
    rows_pos = (
        db.query(
            func.coalesce(func.nullif(func.trim(Candidate.position_applied), ""), "ไม่ระบุ").label("pos"),
            func.count(Candidate.id),
        )
        .filter(Candidate.is_active == True)
        .group_by("pos")
        .all()
    )
    by_position = {label: cnt for label, cnt in rows_pos}

    # 30 วันล่าสุด (รองรับ SQLite)
    since = datetime.utcnow() - timedelta(days=30)
    dialect = (db.get_bind().dialect.name if db.get_bind() else "sqlite").lower()
    date_expr = func.strftime("%Y-%m-%d", Candidate.created_at) if dialect == "sqlite" else func.date_trunc("day", Candidate.created_at)

    rows3 = (
        db.query(date_expr.label("d"), func.count(Candidate.id))
        .filter(Candidate.is_active == True, Candidate.created_at >= since)
        .group_by("d")
        .order_by("d")
        .all()
    )
    last_30d = [{"date": d, "count": c} for d, c in rows3]

    return {
        "total": total,
        "by_status": by_status,
        "by_source": by_source,
        "by_position": by_position,  # 👈 เพิ่มฟิลด์นี้
        "last_30d": last_30d,
    }