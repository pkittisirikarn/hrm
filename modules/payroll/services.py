from __future__ import annotations

from typing import List, Optional
from datetime import datetime, date
import json
import ast, re

from fastapi import HTTPException
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session, joinedload

from modules.payroll import models, schemas
# ดึง metric จากฝั่ง time_tracking
from modules.time_tracking.services import get_attendance_metrics

# -------------------- Safe formula engine --------------------
_ALLOWED_FUNCS   = {"min": min, "max": max, "round": round, "abs": abs}
_ALLOWED_BINOPS  = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)

def _safe_eval_expr(expr: str, variables: dict[str, float]) -> float:
    """ประเมินนิพจน์เลขคณิตแบบปลอดภัย (+ - * / // () และ min/max/round/abs)
       รองรับ {Var} หรือ Var"""
    if not expr:
        return 0.0
    expr = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", r"\1", str(expr)).strip()

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError("const not allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, _ALLOWED_BINOPS):
            l, r = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Add):       return l + r
            if isinstance(node.op, ast.Sub):       return l - r
            if isinstance(node.op, ast.Mult):      return l * r
            if isinstance(node.op, ast.Div):       return l / r if r != 0 else 0.0
            if isinstance(node.op, ast.FloorDiv):  return l // r if r != 0 else 0.0
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, _ALLOWED_UNARYOPS):
            v = _eval(node.operand)
            return +v if isinstance(node.op, ast.UAdd) else -v
        if isinstance(node, ast.Name):
            return float(variables.get(node.id, 0.0) or 0.0)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCS:
            fn = _ALLOWED_FUNCS[node.func.id]
            args = [_eval(a) for a in node.args]
            return float(fn(*args))
        raise ValueError("disallowed")

    try:
        return float(_eval(ast.parse(expr, mode="eval")))
    except Exception:
        return 0.0

# -------------------- Variable builders --------------------
def _formula_variables_from_attendance(
    db: Session, employee_id: int, period_start: date, period_end: date, base_salary: float
) -> dict[str, float]:

    m = get_attendance_metrics(db, employee_id, period_start, period_end) or {}

    minute_rate = float(base_salary or 0) / 30.0 / 8.0 / 60.0
    hour_rate   = minute_rate * 60.0

    # รับค่า 3 ถังจาก metrics
    ot1  = float(m.get("ot1x_minutes", 0) or m.get("ot1_minutes", 0) or 0)
    ot15 = float(m.get("ot_weekday_minutes", 0) or m.get("ot15x_minutes", 0) or 0)
    ot30 = float(m.get("ot_holiday_minutes", 0) or m.get("ot3x_minutes", 0) or 0)

    return {
        "BasicSalary":  float(base_salary or 0.0),
        "BASIC_SALARY": float(base_salary or 0.0),

        "LateMinutes":       float(m.get("late_minutes", 0) or 0),
        "EarlyLeaveMinutes": float(m.get("early_leave_minutes", 0) or 0),
        "AbsenceDays":       float(m.get("absent_days", 0) or 0),
        "UnpaidLeaveDays":   float(m.get("unpaid_leave_days", 0) or 0),

        # aliases สั้น
        "Late":        float(m.get("late_minutes", 0) or 0),
        "L":           float(m.get("late_minutes", 0) or 0),
        "EarlyOut":    float(m.get("early_leave_minutes", 0) or 0),
        "E":           float(m.get("early_leave_minutes", 0) or 0),
        "Absence":     float(m.get("absent_days", 0) or 0),
        "A":           float(m.get("absent_days", 0) or 0),
        "UnpaidLeave": float(m.get("unpaid_leave_days", 0) or 0),
        "UL":          float(m.get("unpaid_leave_days", 0) or 0),

        # ---- OT variables ----
        "OTMinutes":    ot1 + ot15 + ot30,   # รวมทั้งหมด
        "OT1Minutes":   ot1,                 # alias
        "OT1xMinutes":  ot1,                 # ที่สูตร OTx1 ใช้อยู่
        "OT15Minutes":  ot15,                # ใช้กับ OTx15
        "OT30Minutes":  ot30,                # ใช้กับ OTx3
        "MinuteRate":   float(minute_rate),
        "HourRate":     float(hour_rate),
    }

def _items_from_formula_types(
    db: Session,
    employee_id: int,
    period_start: date,
    period_end: date,
    base_salary: float,
) -> tuple[list[dict], list[dict]]:

    vars_map = _formula_variables_from_attendance(db, employee_id, period_start, period_end, base_salary)

    allow_types = db.query(models.AllowanceType).filter(models.AllowanceType.is_active == True).all()
    deduct_types = db.query(models.DeductionType).filter(models.DeductionType.is_active == True).all()

    def _uses_specific_ot(formula: str | None) -> bool:
        if not formula:
            return False
        f = str(formula)
        # ครอบคลุมทุก bucket
        return ("OT1xMinutes" in f) or ("OT15Minutes" in f) or ("OT30Minutes" in f)

    has_specific_ot = any(_uses_specific_ot(t.formula) for t in allow_types + deduct_types)

    eval_vars = dict(vars_map)
    if has_specific_ot:
        # ถ้าสูตรใด ๆ ใช้ bucket แยก ให้ปิดตัวรวมเพื่อไม่ให้คิดซ้ำ
        eval_vars["OTMinutes"] = 0.0

    formula_allow: list[dict] = []
    for t in allow_types:
        if not t.formula:
            continue
        amt = _money(_safe_eval_expr(t.formula, eval_vars))
        if amt != 0:
            formula_allow.append({"label": t.name, "name": t.name, "amount": amt})

    formula_deduct: list[dict] = []
    for t in deduct_types:
        if not t.formula:
            continue
        amt = _money(_safe_eval_expr(t.formula, eval_vars))
        if amt != 0:
            formula_deduct.append({"label": t.name, "name": t.name, "amount": amt})

    return formula_allow, formula_deduct

# -------------------- Helpers --------------------
def _money(x: float | int | None) -> float:
    try:
        return round(float(x or 0), 2)
    except Exception:
        return 0.0

def _per_minute_rate(base_salary: float) -> float:
    return (base_salary or 0) / 30.0 / 8.0 / 60.0

def _per_day_rate(base_salary: float) -> float:
    return (base_salary or 0) / 30.0

def _deductions_from_attendance(
    db: Session,
    employee_id: int,
    period_start: date,
    period_end: date,
    base_salary: float,
) -> list[dict]:
    """ตัวอย่างสร้างรายการหักจาก attendance (ไม่ได้ถูกเรียกแล้วเพราะใช้สูตรแทนได้)"""
    m = get_attendance_metrics(db, employee_id, period_start, period_end) or {}
    items: list[dict] = []

    late_amt  = round(_per_minute_rate(base_salary) * float(m.get("late_minutes", 0) or 0), 2)
    early_amt = round(_per_minute_rate(base_salary) * float(m.get("early_leave_minutes", 0) or 0), 2)
    abs_amt   = round(_per_day_rate(base_salary)     * float(m.get("absent_days", 0) or 0), 2)
    unpay_amt = round(_per_day_rate(base_salary)     * float(m.get("unpaid_leave_days", 0) or 0), 2)

    if late_amt > 0:
        items.append({"code": "LATE",         "label": "Late minutes",  "amount": late_amt})
    if early_amt > 0:
        items.append({"code": "EARLY_LEAVE",  "label": "Early leave",   "amount": early_amt})
    if abs_amt > 0:
        items.append({"code": "ABSENCE",      "label": "Absence",       "amount": abs_amt})
    if unpay_amt > 0:
        items.append({"code": "UNPAID_LEAVE", "label": "Unpaid Leave",  "amount": unpay_amt})

    return items

# -------------------- Scheme / CRUD (เหมือนเดิม) --------------------
def ensure_default_scheme_and_formulas(db: Session) -> models.PayrollScheme:
    scheme = db.execute(
        select(models.PayrollScheme).where(models.PayrollScheme.name == "Default")
    ).scalar_one_or_none()

    if not scheme:
        scheme = models.PayrollScheme(
            name="Default",
            description="Default payroll scheme",
            is_active=True,
        )
        db.add(scheme)
        db.flush()

        f1 = models.PayrollFormula(
            scheme_id=scheme.id,
            code="NET",
            label="Net Pay",
            expression="BASE + OTPAY - LEAVE_DEDUCT",
            sort_order=100,
            is_active=True,
        )
        db.add(f1)
        db.commit()
    return scheme

# --- Allowance Types CRUD ---
def create_allowance_type(db: Session, allowance_type: schemas.AllowanceTypeCreate):
    obj = models.AllowanceType(**allowance_type.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_allowance_types(db: Session, skip=0, limit=100):
    return db.query(models.AllowanceType).offset(skip).limit(limit).all()
def get_allowance_type(db: Session, allowance_type_id: int):
    return db.query(models.AllowanceType).filter(models.AllowanceType.id == allowance_type_id).first()
def update_allowance_type(db: Session, allowance_type_id: int, allowance_type: schemas.AllowanceTypeUpdate):
    obj = get_allowance_type(db, allowance_type_id); 
    if not obj: return None
    for k,v in allowance_type.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_allowance_type(db: Session, allowance_type_id: int):
    obj = get_allowance_type(db, allowance_type_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return True

# --- Deduction Types CRUD ---
def create_deduction_type(db: Session, deduction_type: schemas.DeductionTypeCreate):
    obj = models.DeductionType(**deduction_type.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_deduction_types(db: Session, skip=0, limit=100):
    return db.query(models.DeductionType).offset(skip).limit(limit).all()
def get_deduction_type(db: Session, deduction_type_id: int):
    return db.query(models.DeductionType).filter(models.DeductionType.id == deduction_type_id).first()
def update_deduction_type(db: Session, deduction_type_id: int, deduction_type: schemas.DeductionTypeUpdate):
    obj = get_deduction_type(db, deduction_type_id); 
    if not obj: return None
    for k,v in deduction_type.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_deduction_type(db: Session, deduction_type_id: int):
    obj = get_deduction_type(db, deduction_type_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return True

# --- Salary Structure CRUD ---
def create_salary_structure(db: Session, salary_structure: schemas.SalaryStructureCreate):
    obj = models.SalaryStructure(**salary_structure.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_salary_structures(db: Session, skip=0, limit=100):
    return db.query(models.SalaryStructure).offset(skip).limit(limit).all()
def get_salary_structure(db: Session, salary_structure_id: int):
    return db.query(models.SalaryStructure).filter(models.SalaryStructure.id == salary_structure_id).first()
def update_salary_structure(db: Session, salary_structure_id: int, salary_structure: schemas.SalaryStructureUpdate):
    obj = get_salary_structure(db, salary_structure_id); 
    if not obj: return None
    for k,v in salary_structure.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_salary_structure(db: Session, salary_structure_id: int):
    obj = get_salary_structure(db, salary_structure_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return True

# --- Employee Allowance CRUD ---
def create_employee_allowance(db: Session, employee_allowance: schemas.EmployeeAllowanceCreate):
    obj = models.EmployeeAllowance(**employee_allowance.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_employee_allowances(db: Session, skip=0, limit=100):
    return db.query(models.EmployeeAllowance).offset(skip).limit(limit).all()
def get_employee_allowance(db: Session, employee_allowance_id: int):
    return db.query(models.EmployeeAllowance).filter(models.EmployeeAllowance.id == employee_allowance_id).first()
def update_employee_allowance(db: Session, employee_allowance_id: int, employee_allowance: schemas.EmployeeAllowanceUpdate):
    obj = get_employee_allowance(db, employee_allowance_id); 
    if not obj: return None
    for k,v in employee_allowance.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_employee_allowance(db: Session, employee_allowance_id: int):
    obj = get_employee_allowance(db, employee_allowance_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return True

# --- Employee Deduction CRUD ---
def create_employee_deduction(db: Session, employee_deduction: schemas.EmployeeDeductionCreate):
    obj = models.EmployeeDeduction(**employee_deduction.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj
def get_employee_deductions(db: Session, skip=0, limit=100):
    return db.query(models.EmployeeDeduction).offset(skip).limit(limit).all()
def get_employee_deduction(db: Session, employee_deduction_id: int):
    return db.query(models.EmployeeDeduction).filter(models.EmployeeDeduction.id == employee_deduction_id).first()
def update_employee_deduction(db: Session, employee_deduction_id: int, employee_deduction: schemas.EmployeeDeductionUpdate):
    obj = get_employee_deduction(db, employee_deduction_id); 
    if not obj: return None
    for k,v in employee_deduction.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj
def delete_employee_deduction(db: Session, employee_deduction_id: int):
    obj = get_employee_deduction(db, employee_deduction_id); 
    if not obj: return None
    db.delete(obj); db.commit(); return True

# --- Payroll Run CRUD ---
def create_payroll_run_record(db: Session, payroll_run: schemas.PayrollRunCreate) -> models.PayrollRun:
    new_run = models.PayrollRun(
        scheme_id=payroll_run.scheme_id or 1,
        period_start=payroll_run.period_start,
        period_end=payroll_run.period_end,
        pay_period_start=payroll_run.period_start,
        pay_period_end=payroll_run.period_end,
        run_date=payroll_run.period_end,
        status=models.PayrollRunStatus.PENDING,
        created_at=datetime.utcnow(),
        total_amount_paid=0.0,
        notes=payroll_run.notes,
    )
    db.add(new_run); db.commit(); db.refresh(new_run); return new_run

def get_payroll_runs(db: Session, skip: int = 0, limit: int = 100, status: Optional[models.PayrollRunStatus] = None) -> List[models.PayrollRun]:
    stmt = select(models.PayrollRun)
    if status: stmt = stmt.where(models.PayrollRun.status == status)
    stmt = stmt.order_by(models.PayrollRun.created_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()

def get_payroll_run(db: Session, payroll_run_id: int) -> Optional[models.PayrollRun]:
    return db.get(models.PayrollRun, payroll_run_id)

def update_payroll_run(db: Session, payroll_run_id: int, payroll_run: schemas.PayrollRunUpdate) -> Optional[models.PayrollRun]:
    obj = db.get(models.PayrollRun, payroll_run_id)
    if not obj: return None
    data = payroll_run.model_dump(exclude_unset=True, by_alias=True)
    if "pay_period_start" in data and "period_start" not in data:
        data["period_start"] = data.pop("pay_period_start")
    if "pay_period_end" in data and "period_end" not in data:
        data["period_end"] = data.pop("pay_period_end")
    for k,v in data.items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

def delete_payroll_run(db: Session, run_id: int) -> bool:
    obj = db.get(models.PayrollRun, run_id)
    if not obj: return False
    db.delete(obj); db.commit(); return True

# --- Payroll Entry CRUD & Query ---
def create_payroll_entry(db: Session, payroll_entry: schemas.PayrollEntryCreate):
    obj = models.PayrollEntry(**payroll_entry.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

def get_payroll_entries(
    db: Session, skip: int = 0, limit: int = 100,
    payroll_run_id: int | None = None, employee_id: int | None = None,
    q: str | None = None, start_date: date | None = None, end_date: date | None = None,
    payment_status: str | None = None,
):
    qset = db.query(models.PayrollEntry).join(models.PayrollEntry.employee).join(models.PayrollEntry.payroll_run)

    if payroll_run_id: qset = qset.filter(models.PayrollEntry.payroll_run_id == payroll_run_id)
    if employee_id:   qset = qset.filter(models.PayrollEntry.employee_id == employee_id)

    if q:
        like = f"%{q.strip()}%"
        qset = qset.filter(
            or_(
                getattr(models, "Employee", None) and hasattr(models.Employee, "name") and models.Employee.name.ilike(like) or False,
                getattr(models, "Employee", None) and hasattr(models.Employee, "first_name") and models.Employee.first_name.ilike(like) or False,
                getattr(models, "Employee", None) and hasattr(models.Employee, "last_name") and models.Employee.last_name.ilike(like) or False,
                getattr(models, "Employee", None) and hasattr(models.Employee, "employee_code") and models.Employee.employee_code.ilike(like) or False,
            )
        )
    if payment_status:
        qset = qset.filter(models.PayrollEntry.payment_status == payment_status.upper())

    if start_date or end_date:
        pd_col = getattr(models.PayrollEntry, "payment_date", None)
        if pd_col is not None:
            if start_date: qset = qset.filter(pd_col >= start_date)
            if end_date:   qset = qset.filter(pd_col <= end_date)
        else:
            if start_date and end_date:
                qset = qset.filter(and_(models.PayrollRun.period_start <= end_date, models.PayrollRun.period_end >= start_date))
            elif start_date:
                qset = qset.filter(models.PayrollRun.period_end >= start_date)
            elif end_date:
                qset = qset.filter(models.PayrollRun.period_start <= end_date)

    return qset.order_by(models.PayrollEntry.id.desc()).offset(skip).limit(limit).all()

def get_payroll_entry(db: Session, payroll_entry_id: int):
    return db.query(models.PayrollEntry).filter(models.PayrollEntry.id == payroll_entry_id).first()

def update_payroll_entry(db: Session, payroll_entry_id: int, payroll_entry: schemas.PayrollEntryUpdate):
    obj = get_payroll_entry(db, payroll_entry_id)
    if not obj: return None
    for k,v in payroll_entry.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    db.commit(); db.refresh(obj); return obj

def delete_payroll_entry(db: Session, payroll_entry_id: int):
    obj = get_payroll_entry(db, payroll_entry_id)
    if not obj: return None
    db.delete(obj); db.commit(); return True

# -------------------- Calculate/Save payroll entry --------------------
def _recalculate_run_total_amount(db: Session, run_id: int) -> None:
    total = (db.query(func.coalesce(func.sum(models.PayrollEntry.net_salary), 0.0))
               .filter(models.PayrollEntry.payroll_run_id == run_id).scalar() or 0.0)
    run = db.get(models.PayrollRun, run_id)
    if run:
        run.total_amount_paid = float(total)
        db.commit()

def _coalesce_period(run: models.PayrollRun) -> tuple[date, date]:
    ps = run.period_start or run.pay_period_start
    pe = run.period_end   or run.pay_period_end
    if not ps or not pe:
        base = run.run_date or date.today()
        return base, base
    return ps, pe

def calculate_and_save_payroll_entry(
    db: Session, run_id: int, employee_id: int
) -> models.PayrollEntry | None:

    run = db.get(models.PayrollRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="ไม่พบรอบการจ่ายเงินเดือน")

    period_start, period_end = _coalesce_period(run)

    # Base salary
    ss = (
        db.query(models.SalaryStructure)
          .filter(models.SalaryStructure.employee_id == employee_id,
                  models.SalaryStructure.effective_date <= period_end)
          .order_by(models.SalaryStructure.effective_date.desc()).first()
    ) or (
        db.query(models.SalaryStructure)
          .filter(models.SalaryStructure.employee_id == employee_id)
          .order_by(models.SalaryStructure.effective_date.desc()).first()
    )
    base_salary = _money(ss.base_salary if ss else 0.0)

    # Fixed allowances
    allow_rows = (
        db.query(models.EmployeeAllowance, models.AllowanceType.name)
          .join(models.AllowanceType, models.AllowanceType.id == models.EmployeeAllowance.allowance_type_id)
          .filter(
              models.EmployeeAllowance.employee_id == employee_id,
              models.EmployeeAllowance.status == models.StatusEnum.ACTIVE,
              models.EmployeeAllowance.effective_date >= period_start,
              models.EmployeeAllowance.effective_date <= period_end,
          ).all()
    )
    allowances = [{"label": name, "name": name, "amount": _money(ea.amount)} for ea, name in allow_rows]

    # Fixed deductions
    ded_rows = (
        db.query(models.EmployeeDeduction, models.DeductionType.name)
          .join(models.DeductionType, models.DeductionType.id == models.EmployeeDeduction.deduction_type_id)
          .filter(
              models.EmployeeDeduction.employee_id == employee_id,
              models.EmployeeDeduction.status == models.StatusEnum.ACTIVE,
              models.EmployeeDeduction.effective_date >= period_start,
              models.EmployeeDeduction.effective_date <= period_end,
          ).all()
    )
    deductions = [{"label": name, "name": name, "amount": _money(ed.amount)} for ed, name in ded_rows]

    # Add items from formula types (OT/late/early/leave ก็เขียนเป็นสูตรได้ที่นี่)
    form_allow, form_deduct = _items_from_formula_types(
        db=db, employee_id=employee_id, period_start=period_start, period_end=period_end, base_salary=base_salary
    )
    allowances.extend(form_allow)
    deductions.extend(form_deduct)

    # Totals
    total_allowances = _money(sum(a["amount"] for a in allowances))
    total_deductions = _money(sum(d["amount"] for d in deductions))

    gross = _money(base_salary + total_allowances)
    net   = _money(gross - total_deductions)

    # Upsert
    entry = (db.query(models.PayrollEntry)
               .filter(models.PayrollEntry.payroll_run_id == run_id,
                       models.PayrollEntry.employee_id == employee_id)
               .first())

    payload_allow  = json.dumps(allowances, ensure_ascii=False)
    payload_deduct = json.dumps(deductions, ensure_ascii=False)

    if entry is None:
        entry = models.PayrollEntry(
            payroll_run_id=run_id, employee_id=employee_id,
            gross_salary=gross, net_salary=net,
            calculated_allowances_json=payload_allow,
            calculated_deductions_json=payload_deduct,
            payment_status=models.PaymentStatus.PENDING,
        )
        db.add(entry)
    else:
        entry.gross_salary = gross
        entry.net_salary = net
        entry.calculated_allowances_json = payload_allow
        entry.calculated_deductions_json = payload_deduct

    db.commit(); db.refresh(entry)
    _recalculate_run_total_amount(db, run_id)
    return entry

# -------------------- Payslip context --------------------
def build_payslip_context(db: Session, entry_id: int) -> dict | None:
    entry = (
        db.query(models.PayrollEntry)
          .options(joinedload(models.PayrollEntry.employee),
                   joinedload(models.PayrollEntry.payroll_run))
          .filter(models.PayrollEntry.id == entry_id).first()
    )
    if not entry: return None

    emp = entry.employee
    run = entry.payroll_run

    def _parse(js):
        if not js: return []
        try:
            data = json.loads(js); norm = []
            if isinstance(data, dict):
                for k,v in data.items(): norm.append({"label": str(k), "amount": _money(v)})
            elif isinstance(data, list):
                for it in data:
                    if isinstance(it, dict):
                        norm.append({"label": it.get("label") or it.get("name") or "-", "amount": _money(it.get("amount"))})
            return norm
        except Exception:
            return []

    allowances = _parse(entry.calculated_allowances_json)
    deductions = _parse(entry.calculated_deductions_json)

    total_allow = _money(sum((it.get("amount") or 0) for it in allowances))
    total_deduct = _money(sum((it.get("amount") or 0) for it in deductions))

    gross = entry.gross_salary if entry.gross_salary is not None else _money(total_allow)
    net   = entry.net_salary   if entry.net_salary   is not None else _money(gross - total_deduct)

    employee_fullname = None; employee_code = None; department_name = None; position_name = None
    if emp is not None:
        fn = getattr(emp, "first_name", None) or getattr(emp, "firstname", None) or getattr(emp, "name", None)
        ln = getattr(emp, "last_name", None) or getattr(emp, "lastname", None)
        employee_fullname = " ".join([p for p in [fn, ln] if p]) or fn or "-"
        employee_code = getattr(emp, "employee_code", None) or getattr(emp, "code", None)
        dept = getattr(emp, "department", None); pos = getattr(emp, "position", None)
        department_name = getattr(dept, "name", None) if dept else None
        position_name   = getattr(pos, "name", None) if pos else None

    return {
        "company_name": "บริษัทของคุณ",
        "run_id": run.id if run else None,
        "entry_id": entry.id,
        "period_start": getattr(run, "period_start", None) or getattr(run, "pay_period_start", None) or "-",
        "period_end":   getattr(run, "period_end",   None) or getattr(run, "pay_period_end",   None) or "-",
        "payment_date": entry.payment_date,
        "employee_fullname": employee_fullname,
        "employee_code": employee_code,
        "department_name": department_name,
        "position_name": position_name,
        "allowances": allowances,
        "deductions": deductions,
        "total_allowances": total_allow,
        "total_deductions": total_deduct,
        "gross_salary": gross,
        "net_salary": net,
    }
