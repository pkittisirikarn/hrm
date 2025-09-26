# modules/payroll/routes.py
from __future__ import annotations

from typing import List, Optional, Tuple
from datetime import date, datetime
from calendar import monthrange
import os, json, shutil, csv, io

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from database.connection import get_db
from modules.payroll import models, schemas, services
from modules.data_management import models as dm_models
from modules.payroll.models import PayrollEntry
from modules.data_management.models import Employee
from modules.payroll.schemas import PayrollEntryInDB

import pdfkit
from pathlib import Path

router = APIRouter(prefix="/api/v1/payroll", tags=["payroll"])

ui_router = APIRouter()
api_router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ---------- UI ROUTES ----------
@ui_router.get("/allowance-types", response_class=HTMLResponse)
async def read_allowance_types_ui(request: Request):
    return templates.TemplateResponse("payroll/allowance_types.html", {"request": request})


@ui_router.get("/deduction-types", response_class=HTMLResponse)
async def read_deduction_types_ui(request: Request):
    return templates.TemplateResponse("payroll/deduction_types.html", {"request": request})


@ui_router.get("/salary-structures", response_class=HTMLResponse)
async def read_salary_structures_ui(request: Request):
    return templates.TemplateResponse("payroll/salary_structures.html", {"request": request})


@ui_router.get("/employee-allowances", response_class=HTMLResponse)
async def read_employee_allowances_ui(request: Request):
    return templates.TemplateResponse("payroll/employee_allowances.html", {"request": request})


@ui_router.get("/employee-deductions", response_class=HTMLResponse)
async def read_employee_deductions_ui(request: Request):
    return templates.TemplateResponse("payroll/employee_deductions.html", {"request": request})


@ui_router.get("/payroll-runs", response_class=HTMLResponse)
async def read_payroll_runs_ui(request: Request):
    return templates.TemplateResponse("payroll/payroll_runs.html", {"request": request})


@ui_router.get("/payroll-entries", response_class=HTMLResponse)
async def read_payroll_entries_ui(request: Request):
    return templates.TemplateResponse("payroll/payroll_entries.html", {"request": request})


# ---------- API ROUTES : Allowance Types ----------
@api_router.post("/allowance-types/", response_model=schemas.AllowanceTypeInDB, status_code=status.HTTP_201_CREATED)
def create_allowance_type_route(allowance_type: schemas.AllowanceTypeCreate, db: Session = Depends(get_db)):
    return services.create_allowance_type(db=db, allowance_type=allowance_type)


@api_router.get("/allowance-types/", response_model=List[schemas.AllowanceTypeInDB])
def read_allowance_types_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_allowance_types(db=db, skip=skip, limit=limit)


@api_router.get("/allowance-types/{allowance_type_id}", response_model=schemas.AllowanceTypeInDB)
def read_allowance_type_route(allowance_type_id: int, db: Session = Depends(get_db)):
    obj = services.get_allowance_type(db=db, allowance_type_id=allowance_type_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบประเภทค่าตอบแทน")
    return obj


@api_router.put("/allowance-types/{allowance_type_id}", response_model=schemas.AllowanceTypeInDB)
def update_allowance_type_route(allowance_type_id: int, allowance_type: schemas.AllowanceTypeUpdate, db: Session = Depends(get_db)):
    obj = services.update_allowance_type(db=db, allowance_type_id=allowance_type_id, allowance_type=allowance_type)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบประเภทค่าตอบแทนที่ต้องการอัปเดต")
    return obj


@api_router.delete("/allowance-types/{allowance_type_id}", status_code=status.HTTP_200_OK)
def delete_allowance_type_route(allowance_type_id: int, db: Session = Depends(get_db)):
    ok = services.delete_allowance_type(db=db, allowance_type_id=allowance_type_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบประเภทค่าตอบแทนที่ต้องการลบ")
    return {"message": "ประเภทค่าตอบแทนถูกลบแล้ว"}


# ---------- API ROUTES : Deduction Types ----------
@api_router.post("/deduction-types/", response_model=schemas.DeductionTypeInDB, status_code=status.HTTP_201_CREATED)
def create_deduction_type_route(deduction_type: schemas.DeductionTypeCreate, db: Session = Depends(get_db)):
    return services.create_deduction_type(db=db, deduction_type=deduction_type)


@api_router.get("/deduction-types/", response_model=List[schemas.DeductionTypeInDB])
def read_deduction_types_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_deduction_types(db=db, skip=skip, limit=limit)


@api_router.get("/deduction-types/{deduction_type_id}", response_model=schemas.DeductionTypeInDB)
def read_deduction_type_route(deduction_type_id: int, db: Session = Depends(get_db)):
    obj = services.get_deduction_type(db=db, deduction_type_id=deduction_type_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบประเภทการหักเงิน")
    return obj


@api_router.put("/deduction-types/{deduction_type_id}", response_model=schemas.DeductionTypeInDB)
def update_deduction_type_route(deduction_type_id: int, deduction_type: schemas.DeductionTypeUpdate, db: Session = Depends(get_db)):
    obj = services.update_deduction_type(db=db, deduction_type_id=deduction_type_id, deduction_type=deduction_type)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบประเภทการหักเงินที่ต้องการอัปเดต")
    return obj


@api_router.delete("/deduction-types/{deduction_type_id}", status_code=status.HTTP_200_OK)
def delete_deduction_type_route(deduction_type_id: int, db: Session = Depends(get_db)):
    ok = services.delete_deduction_type(db=db, deduction_type_id=deduction_type_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบประเภทการหักเงินที่ต้องการลบ")
    return {"message": "ประเภทการหักเงินถูกลบแล้ว"}


# ---------- API ROUTES : Salary Structures ----------
@api_router.post("/salary-structures/", response_model=schemas.SalaryStructureInDB, status_code=status.HTTP_201_CREATED)
def create_salary_structure_route(salary_structure: schemas.SalaryStructureCreate, db: Session = Depends(get_db)):
    return services.create_salary_structure(db=db, salary_structure=salary_structure)


@api_router.get("/salary-structures/", response_model=List[schemas.SalaryStructureInDB])
def read_salary_structures_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_salary_structures(db=db, skip=skip, limit=limit)


@api_router.get("/salary-structures/{salary_structure_id}", response_model=schemas.SalaryStructureInDB)
def read_salary_structure_route(salary_structure_id: int, db: Session = Depends(get_db)):
    obj = services.get_salary_structure(db=db, salary_structure_id=salary_structure_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบโครงสร้างเงินเดือน")
    return obj


@api_router.put("/salary-structures/{salary_structure_id}", response_model=schemas.SalaryStructureInDB)
def update_salary_structure_route(salary_structure_id: int, salary_structure: schemas.SalaryStructureUpdate, db: Session = Depends(get_db)):
    obj = services.update_salary_structure(db=db, salary_structure_id=salary_structure_id, salary_structure=salary_structure)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบโครงสร้างเงินเดือนที่ต้องการอัปเดต")
    return obj


@api_router.delete("/salary-structures/{salary_structure_id}", status_code=status.HTTP_200_OK)
def delete_salary_structure_route(salary_structure_id: int, db: Session = Depends(get_db)):
    ok = services.delete_salary_structure(db=db, salary_structure_id=salary_structure_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบโครงสร้างเงินเดือนที่ต้องการลบ")
    return {"message": "โครงสร้างเงินเดือนถูกลบแล้ว"}

# ---------- API ROUTES : Employee Allowances ----------
@api_router.get("/employee-allowances/", response_model=List[schemas.EmployeeAllowanceInDB])
def list_employee_allowances(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_employee_allowances(db, skip=skip, limit=limit)

@api_router.post("/employee-allowances/", response_model=schemas.EmployeeAllowanceInDB, status_code=status.HTTP_201_CREATED)
def create_employee_allowance_route(payload: schemas.EmployeeAllowanceCreate, db: Session = Depends(get_db)):
    return services.create_employee_allowance(db, payload)

@api_router.get("/employee-allowances/{ea_id}", response_model=schemas.EmployeeAllowanceInDB)
def get_employee_allowance_route(ea_id: int, db: Session = Depends(get_db)):
    obj = services.get_employee_allowance(db, ea_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบเงินเพิ่มพนักงาน")
    return obj

@api_router.put("/employee-allowances/{ea_id}", response_model=schemas.EmployeeAllowanceInDB)
def update_employee_allowance_route(ea_id: int, payload: schemas.EmployeeAllowanceUpdate, db: Session = Depends(get_db)):
    obj = services.get_employee_allowance(db, ea_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบเงินเพิ่มพนักงานที่ต้องการอัปเดต")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@api_router.delete("/employee-allowances/{ea_id}", status_code=status.HTTP_200_OK)
def delete_employee_allowance_route(ea_id: int, db: Session = Depends(get_db)):
    ok = services.delete_employee_allowance(db, ea_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ไม่พบเงินเพิ่มพนักงานที่ต้องการลบ")
    return {"message": "ลบเงินเพิ่มพนักงานแล้ว"}

# ---------- API ROUTES : Employee Deductions ----------
@api_router.get("/employee-deductions/", response_model=List[schemas.EmployeeDeductionInDB])
def list_employee_deductions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return services.get_employee_deductions(db, skip=skip, limit=limit)

@api_router.post("/employee-deductions/", response_model=schemas.EmployeeDeductionInDB, status_code=status.HTTP_201_CREATED)
def create_employee_deduction_route(payload: schemas.EmployeeDeductionCreate, db: Session = Depends(get_db)):
    return services.create_employee_deduction(db, payload)

@api_router.get("/employee-deductions/{ed_id}", response_model=schemas.EmployeeDeductionInDB)
def get_employee_deduction_route(ed_id: int, db: Session = Depends(get_db)):
    obj = services.get_employee_deduction(db, ed_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกรายการหักพนักงาน")
    return obj

@api_router.put("/employee-deductions/{ed_id}", response_model=schemas.EmployeeDeductionInDB)
def update_employee_deduction_route(ed_id: int, payload: schemas.EmployeeDeductionUpdate, db: Session = Depends(get_db)):
    obj = services.get_employee_deduction(db, ed_id)
    if not obj:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกรายการหักพนักงานที่ต้องการอัปเดต")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@api_router.delete("/employee-deductions/{ed_id}", status_code=status.HTTP_200_OK)
def delete_employee_deduction_route(ed_id: int, db: Session = Depends(get_db)):
    ok = services.delete_employee_deduction(db, ed_id)
    if not ok:
        raise HTTPException(status_code=404, detail="ไม่พบบันทึกรายการหักพนักงานที่ต้องการลบ")
    return {"message": "ลบรายการหักพนักงานแล้ว"}

# ---------- Helpers ----------
def _find_wkhtmltopdf() -> str | None:
    candidates = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        shutil.which("wkhtmltopdf"),
    ]
    for p in candidates:
        if p and Path(p).exists():
            return p
    return None


def _parse_items_to_map(json_str: str | None) -> dict[str, float]:
    """
    รองรับทั้ง:
    - list[{"label"/"name"/"code", "amount"}]
    - dict{"label": amount}
    คืน dict[label] = float(amount)
    """
    if not json_str:
        return {}
    try:
        data = json.loads(json_str)
    except Exception:
        return {}

    result: dict[str, float] = {}
    if isinstance(data, list):
        for it in data:
            try:
                label = (it.get("label") or it.get("name") or it.get("code") or "-").strip()
                amt = float(it.get("amount", 0) or 0)
                result[label] = result.get(label, 0.0) + amt
            except Exception:
                pass
    elif isinstance(data, dict):
        for k, v in data.items():
            try:
                label = str(k).strip()
                amt = float(v or 0)
                result[label] = result.get(label, 0.0) + amt
            except Exception:
                pass
    return result


def _find_base_salary(db: Session, employee_id: int, period_end: date) -> Optional[float]:
    s = (
        db.query(models.SalaryStructure)
        .filter(
            models.SalaryStructure.employee_id == employee_id,
            models.SalaryStructure.effective_date <= period_end
        )
        .order_by(desc(models.SalaryStructure.effective_date))
        .first()
    )
    return float(s.base_salary) if s else None


def _compute_period(month: Optional[str], start_date: Optional[date], end_date: Optional[date]) -> Tuple[date, date, str]:
    if month:
        y, m = map(int, month.split("-"))
        first = date(y, m, 1)
        last = date(y, m, monthrange(y, m)[1])
        return first, last, month
    if start_date and end_date:
        return start_date, end_date, f"{start_date}..{end_date}"
    raise HTTPException(status_code=400, detail="ต้องระบุ month=YYYY-MM หรือ start_date & end_date")


# ---------- API ROUTES : Payroll Runs (CRUD record) ----------
@api_router.post("/payroll-runs/", response_model=schemas.PayrollRunRead, status_code=status.HTTP_201_CREATED)
def create_payroll_run_record(payroll_run: schemas.PayrollRunCreate, db: Session = Depends(get_db)):
    return services.create_payroll_run_record(db=db, payroll_run=payroll_run)


@api_router.get("/payroll-runs/", response_model=List[schemas.PayrollRunRead])
def list_payroll_runs(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, description="PENDING/PROCESSING/COMPLETED/FAILED"),
):
    enum_status: Optional[models.PayrollRunStatus] = None
    if status:
        key = status.strip().upper()
        try:
            enum_status = models.PayrollRunStatus[key]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")

    return services.get_payroll_runs(db=db, skip=skip, limit=limit, status=enum_status)


@api_router.get("/payroll-runs/{payroll_run_id}", response_model=schemas.PayrollRunRead)
def read_payroll_run(payroll_run_id: int, db: Session = Depends(get_db)):
    obj = services.get_payroll_run(db=db, payroll_run_id=payroll_run_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรอบการจ่ายเงินเดือน")
    return obj


@api_router.put("/payroll-runs/{payroll_run_id}", response_model=schemas.PayrollRunRead)
def update_payroll_run(payroll_run_id: int, payroll_run: schemas.PayrollRunUpdate, db: Session = Depends(get_db)):
    obj = services.update_payroll_run(db=db, payroll_run_id=payroll_run_id, payroll_run=payroll_run)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรอบการจ่ายเงินเดือนที่ต้องการอัปเดต")
    return obj


@api_router.delete("/payroll-runs/{payroll_run_id}", status_code=status.HTTP_200_OK)
def delete_payroll_run(payroll_run_id: int, db: Session = Depends(get_db)):
    ok = services.delete_payroll_run(db=db, run_id=payroll_run_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรอบการจ่ายเงินเดือนที่ต้องการลบ")
    return {"message": "รอบการจ่ายเงินเดือนถูกลบแล้ว"}


# ---------- API ROUTES : Payroll Entries ----------
@api_router.post("/payroll-entries/", response_model=schemas.PayrollEntryInDB, status_code=status.HTTP_201_CREATED)
def create_payroll_entry_route(payroll_entry: schemas.PayrollEntryCreate, db: Session = Depends(get_db)):
    return services.create_payroll_entry(db=db, payroll_entry=payroll_entry)


@api_router.get("/payroll-entries/", response_model=List[schemas.PayrollEntryInDB])
def list_payroll_entries(
    skip: int = 0,
    limit: int = 100,
    payroll_run_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    q: Optional[str] = Query(None, description="ค้นหาชื่อ/รหัสพนักงาน"),
    start_date: Optional[date] = Query(None, description="YYYY-MM-DD (เริ่ม)"),
    end_date: Optional[date] = Query(None, description="YYYY-MM-DD (สิ้นสุด)"),
    payment_status: Optional[str] = Query(None, description="PENDING/PAID/FAILED"),
    db: Session = Depends(get_db),
):
    return services.get_payroll_entries(
        db=db,
        skip=skip,
        limit=limit,
        payroll_run_id=payroll_run_id,
        employee_id=employee_id,
        q=q,
        start_date=start_date,
        end_date=end_date,
        payment_status=payment_status,
    )


@api_router.get("/payroll-entries/report")  # ลบ response_model เพื่อรองรับคีย์ไดนามิก
def payroll_entries_report(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    only_paid: bool = False,
    db: Session = Depends(get_db),
):
    p_start, p_end, label = _compute_period(month, start_date, end_date)

    q = (
        db.query(models.PayrollEntry, dm_models.Employee, models.PayrollRun)
        .join(dm_models.Employee, dm_models.Employee.id == models.PayrollEntry.employee_id)
        .join(models.PayrollRun, models.PayrollRun.id == models.PayrollEntry.payroll_run_id)
        .filter(
            models.PayrollRun.period_start >= p_start,
            models.PayrollRun.period_end   <= p_end,
        )
    )
    if only_paid:
        q = q.filter(models.PayrollEntry.payment_status == models.PaymentStatus.PAID)

    rows = []
    totals = {
        "base_salary": 0.0,
        "allowances_total": 0.0,
        "deductions_total": 0.0,
        "gross_salary": 0.0,
        "net_salary": 0.0,
    }

    allowance_keys: set[str] = set()
    deduction_keys: set[str] = set()
    allowance_totals_by_type: dict[str, float] = {}
    deduction_totals_by_type: dict[str, float] = {}

    for entry, emp, run in q.all():
        allow_map = _parse_items_to_map(entry.calculated_allowances_json)
        deduct_map = _parse_items_to_map(entry.calculated_deductions_json)

        allowance_keys.update(allow_map.keys())
        deduction_keys.update(deduct_map.keys())

        for k, v in allow_map.items():
            allowance_totals_by_type[k] = allowance_totals_by_type.get(k, 0.0) + float(v or 0)
        for k, v in deduct_map.items():
            deduction_totals_by_type[k] = deduction_totals_by_type.get(k, 0.0) + float(v or 0)

        allow_total = round(sum(allow_map.values()), 2)
        deduct_total = round(sum(deduct_map.values()), 2)

        base_from_struct = _find_base_salary(db, entry.employee_id, run.period_end)
        base_salary = base_from_struct if base_from_struct is not None else float(entry.gross_salary or 0) - allow_total

        gross = float(entry.gross_salary or (base_salary + allow_total))
        net = float(entry.net_salary or (base_salary + allow_total - deduct_total))

        row = {
            "employee_id": emp.id,
            "employee_name": f"{emp.first_name} {emp.last_name}",
            "payroll_run_id": run.id,
            "period_start": run.period_start,
            "period_end": run.period_end,
            "allowances": {k: round(float(v or 0), 2) for k, v in allow_map.items()},
            "deductions": {k: round(float(v or 0), 2) for k, v in deduct_map.items()},
            "base_salary": round(base_salary, 2),
            "allowances_total": allow_total,
            "deductions_total": deduct_total,
            "gross_salary": round(gross, 2),
            "net_salary": round(net, 2),
            "payment_status": entry.payment_status,
            "payment_date": entry.payment_date,
        }
        rows.append(row)

        totals["base_salary"]       += row["base_salary"]
        totals["allowances_total"]  += row["allowances_total"]
        totals["deductions_total"]  += row["deductions_total"]
        totals["gross_salary"]      += row["gross_salary"]
        totals["net_salary"]        += row["net_salary"]

    for k in list(totals.keys()):
        totals[k] = round(totals[k], 2)

    return {
        "period": {"label": label, "start": p_start, "end": p_end},
        "allowance_keys": sorted(allowance_keys),
        "deduction_keys": sorted(deduction_keys),
        "rows": rows,
        "totals": totals,
        "allowance_totals_by_type": {k: round(v, 2) for k, v in allowance_totals_by_type.items()},
        "deduction_totals_by_type": {k: round(v, 2) for k, v in deduction_totals_by_type.items()},
    }


@api_router.get("/payroll-entries/report.csv")
def payroll_entries_report_csv(
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    only_paid: bool = False,
    db: Session = Depends(get_db),
):
    data = payroll_entries_report(month=month, start_date=start_date, end_date=end_date, only_paid=only_paid, db=db)

    rows = data["rows"]
    allowance_keys: list[str] = data.get("allowance_keys", [])
    deduction_keys: list[str] = data.get("deduction_keys", [])

    buf = io.StringIO()
    writer = csv.writer(buf)

    base_headers = [
        "employee_id","employee_name","payroll_run_id","period_start","period_end",
        "base_salary",
    ]
    allow_headers = [f"Allowance: {k}" for k in allowance_keys] + ["allowances_total"]
    deduct_headers= [f"Deduction: {k}" for k in deduction_keys] + ["deductions_total"]
    tail_headers  = ["gross_salary","net_salary","payment_status","payment_date"]

    writer.writerow(base_headers + allow_headers + deduct_headers + tail_headers)

    for r in rows:
        base_part = [
            r["employee_id"], r["employee_name"], r["payroll_run_id"],
            r["period_start"], r["period_end"],
            r["base_salary"],
        ]
        allow_map = r.get("allowances") or {}
        deduct_map= r.get("deductions") or {}

        allow_part = [allow_map.get(k, 0.0) for k in allowance_keys] + [r["allowances_total"]]
        deduct_part= [deduct_map.get(k, 0.0) for k in deduction_keys] + [r["deductions_total"]]
        tail_part  = [r["gross_salary"], r["net_salary"], r["payment_status"], r["payment_date"]]

        writer.writerow(base_part + allow_part + deduct_part + tail_part)

    totals = data.get("totals", {})
    allow_totals_by_type = data.get("allowance_totals_by_type", {})
    deduct_totals_by_type= data.get("deduction_totals_by_type", {})

    totals_base_part  = ["TOTAL", "", "", "", "", totals.get("base_salary", 0.0)]
    totals_allow_part = [allow_totals_by_type.get(k, 0.0) for k in allowance_keys] + [totals.get("allowances_total", 0.0)]
    totals_deduct_part= [deduct_totals_by_type.get(k, 0.0) for k in deduction_keys] + [totals.get("deductions_total", 0.0)]
    totals_tail_part  = [totals.get("gross_salary", 0.0), totals.get("net_salary", 0.0), "", ""]

    writer.writerow(totals_base_part + totals_allow_part + totals_deduct_part + totals_tail_part)

    content = buf.getvalue().encode("utf-8-sig")
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="payroll-report-{data["period"]["label"]}.csv"'}
    )


# ====== คำนวณ payroll: ใช้เส้นทางที่ชัดเจน + คงเส้นทางเดิมที่ถูกต้อง ======
# เส้นทางเดิม (ถูกต้อง: employee ก่อน run) — หน้าเว็บคุณเรียกอันนี้อยู่
@api_router.post("/payroll-entries/calculate/{employee_id:int}/{payroll_run_id:int}",
    response_model=schemas.PayrollEntryInDB,
    status_code=status.HTTP_201_CREATED
)
def calculate_entry_by_employee_then_run_legacy(
    employee_id: int,
    payroll_run_id: int,
    db: Session = Depends(get_db)
):
    return calculate_and_save_payroll_entry_route(
        payroll_run_id=payroll_run_id,
        employee_id=employee_id,
        db=db
    )

# เส้นทางใหม่แบบชัดเจน (เลือกใช้ได้)
@api_router.post("/payroll-entries/calculate/by-employee/{employee_id}/run/{payroll_run_id}",
    response_model=schemas.PayrollEntryInDB,
    status_code=status.HTTP_201_CREATED
)
def calculate_entry_by_employee_then_run(
    employee_id: int,
    payroll_run_id: int,
    db: Session = Depends(get_db)
):
    return calculate_and_save_payroll_entry_route(
        payroll_run_id=payroll_run_id,
        employee_id=employee_id,
        db=db
    )

@api_router.post("/payroll-entries/calculate/by-run/{payroll_run_id}/employee/{employee_id}",
    response_model=schemas.PayrollEntryInDB,
    status_code=status.HTTP_201_CREATED
)
def calculate_entry_by_run_then_employee(
    payroll_run_id: int,
    employee_id: int,
    db: Session = Depends(get_db)
):
    return calculate_and_save_payroll_entry_route(
        payroll_run_id=payroll_run_id,
        employee_id=employee_id,
        db=db
    )


@api_router.get("/payroll-entries/search", response_model=List[PayrollEntryInDB])
def search_payroll_entries(
    q: Optional[str] = Query(None, description="ค้นหาด้วยชื่อหรือรหัสพนักงาน"),
    db: Session = Depends(get_db)
):
    if not q:
        raise HTTPException(status_code=400, detail="กรุณาระบุคำค้นหา q")

    results = (
        db.query(PayrollEntry)
        .join(Employee)
        .filter(
            or_(
                Employee.first_name.ilike(f"%{q}%"),
                Employee.last_name.ilike(f"%{q}%"),
                Employee.employee_code.ilike(f"%{q}%"),
            )
        )
        .all()
    )
    return results
# ====== จบส่วน calculate & search ======


@api_router.get("/payroll-entries/{payroll_entry_id}", response_model=schemas.PayrollEntryInDB)
def read_payroll_entry_route(payroll_entry_id: int, db: Session = Depends(get_db)):
    obj = services.get_payroll_entry(db=db, payroll_entry_id=payroll_entry_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการจ่ายเงินเดือน")
    return obj


@api_router.put("/payroll-entries/{payroll_entry_id}", response_model=schemas.PayrollEntryInDB)
def update_payroll_entry_route(payroll_entry_id: int, payroll_entry: schemas.PayrollEntryUpdate, db: Session = Depends(get_db)):
    obj = services.update_payroll_entry(db=db, payroll_entry_id=payroll_entry_id, payroll_entry=payroll_entry)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการจ่ายเงินเดือนที่ต้องการอัปเดต")
    return obj


@api_router.delete("/payroll-entries/{payroll_entry_id}", status_code=status.HTTP_200_OK)
def delete_payroll_entry_route(payroll_entry_id: int, db: Session = Depends(get_db)):
    ok = services.delete_payroll_entry(db=db, payroll_entry_id=payroll_entry_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการจ่ายเงินเดือนที่ต้องการลบ")
    return {"message": "รายการจ่ายเงินเดือนถูกลบแล้ว"}


def calculate_payroll_entry(employee_id: int, payroll_run_id: int, db: Session = Depends(get_db)):
    return services.calculate_and_create_payroll_entry(db=db, employee_id=employee_id, run_id=payroll_run_id)


def calculate_and_save_payroll_entry_route(
    payroll_run_id: int,
    employee_id: int,
    db: Session = Depends(get_db),
):
    try:
        return services.calculate_and_save_payroll_entry(
            db=db,
            run_id=payroll_run_id,
            employee_id=employee_id,
        )
    except ValueError as e:
        msg = str(e)
        if msg == "RUN_NOT_FOUND":
            raise HTTPException(status_code=404, detail="ไม่พบรอบการจ่ายเงินเดือนที่เลือก")
        if msg == "NO_SALARY_STRUCTURE":
            raise HTTPException(status_code=400, detail="ไม่พบโครงสร้างเงินเดือนของพนักงานในช่วงเวลานี้")
        raise HTTPException(status_code=400, detail=msg)
    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"คำนวณ/บันทึกไม่สำเร็จ: {ex}")


# -------- Payslip Preview (HTML) --------
@ui_router.get("/payslip/{entry_id}", response_class=HTMLResponse)
def payslip_preview(entry_id: int, request: Request, db: Session = Depends(get_db)):
    ctx = services.build_payslip_context(db, entry_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจ่ายเงินเดือน")
    return templates.TemplateResponse("payroll/payslip.html", {"request": request, **ctx})


WKHTMLTOPDF_PATH = os.getenv(
    "WKHTMLTOPDF_PATH",
    r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
)


# -------- Payslip PDF Download --------
@api_router.get("/payroll-entries/{entry_id}/payslip.pdf")
def payslip_pdf(entry_id: int, db: Session = Depends(get_db)):
    ctx = services.build_payslip_context(db, entry_id)
    ctx["is_pdf"] = True
    html = templates.get_template("payroll/payslip.html").render(ctx)
    if not ctx:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจ่ายเงินเดือน")

    config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
    options = {
        "encoding": "utf-8",
        "page-size": "A5",
        "margin-top": "10mm",
        "margin-bottom": "10mm",
        "margin-left": "10mm",
        "margin-right": "10mm",
    }
    pdf_bytes = pdfkit.from_string(html, False, configuration=config, options=options)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="payslip-{entry_id}.pdf"'}
    )


# ---------- Helper: build payslip context ----------
def _build_payslip_context(db: Session, entry_id: int) -> dict:
    entry = db.query(models.PayrollEntry).get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="ไม่พบรายการจ่ายเงินเดือน")

    run = db.query(models.PayrollRun).get(entry.payroll_run_id)
    employee = db.query(dm_models.Employee).get(entry.employee_id)

    allowances, deductions = [], []
    try:
        if entry.calculated_allowances_json:
            for a in (json.loads(entry.calculated_allowances_json) or []):
                allowances.append({
                    "name": a.get("name") or a.get("label") or a.get("code") or "-",
                    "amount": float(a.get("amount", 0)),
                })
    except Exception:
        pass
    try:
        if entry.calculated_deductions_json:
            for d in (json.loads(entry.calculated_deductions_json) or []):
                deductions.append({
                    "name": d.get("name") or d.get("label") or d.get("code") or "-",
                    "amount": float(d.get("amount", 0)),
                })
    except Exception:
        pass

    company = {"name": "บริษัทของคุณ", "logo_url": None}
    notes = run.notes if run and getattr(run, "notes", None) else None

    return {
        "company": company,
        "run": run,
        "entry": entry,
        "employee": employee,
        "allowances": allowances,
        "deductions": deductions,
        "notes": notes,
    }


# รวม API routes เข้ากับ router หลัก
router.include_router(api_router)

# รวม UI routes เช่น /payroll-entries เข้ากับ router หลัก
router.include_router(ui_router)
