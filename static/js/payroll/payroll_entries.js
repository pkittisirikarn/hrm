// payroll_entries.js  (clean & unified + summary preview with BASE SALARY)
// - BASE = /api/v1/payroll
// - ค้นหา/กรอง: GET /api/v1/payroll/payroll-entries/?q&start_date&end_date&employee_id&payroll_run_id
// - ไม่มีการเรียก /api/v1/payroll-entries/search
// - โมดัล “แก้ไข/ดูรายละเอียด” แสดง เงินเพิ่ม/รายการหัก + สรุปรวม
// - ✅ เงินเดือนฐาน อิงจาก Salary Structure (ล่าสุดที่มีผล <= period_end ของรอบจ่าย)

document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = '/api/v1/payroll';
  const DATA_MGMT_API_BASE_URL = '/api/v1/data-management';

  // Elements for Calculate/Add Payroll Entry
  const calculatePayrollEntryForm = document.getElementById('calculatePayrollEntryForm');
  const calculatePayrollEntryMessage = document.getElementById('calculatePayrollEntryMessage');
  const calcEmployeeIdSelect = document.getElementById('calcEmployeeId');
  const calcPayrollRunIdSelect = document.getElementById('calcPayrollRunId');

  // Elements for Listing Payroll Entries
  const payrollEntriesTableBody = document.getElementById('payrollEntriesTableBody');
  const payrollEntriesMessage = document.getElementById('payrollEntriesMessage');

  // Elements for Editing Payroll Entry Modal
  const editPayrollEntryModal = document.getElementById('editPayrollEntryModal');
  const closeEditModalButton = document.getElementById('closeEditModalButton');
  const editPayrollEntryForm = document.getElementById('editPayrollEntryForm');
  const editPayrollEntryMessage = document.getElementById('editPayrollEntryMessage');

  // Edit Form Fields
  const editPayrollEntryIdInput = document.getElementById('editPayrollEntryId');
  const editPayrollRunNameInput = document.getElementById('editPayrollRunName');
  const editEmployeeNameInput   = document.getElementById('editEmployeeName');
  const editGrossSalaryInput    = document.getElementById('editGrossSalary');
  const editNetSalaryInput      = document.getElementById('editNetSalary');
  const editCalculatedAllowancesDiv = document.getElementById('editCalculatedAllowances');
  const editCalculatedDeductionsDiv = document.getElementById('editCalculatedDeductions');
  const editPaymentDateInput    = document.getElementById('editPaymentDate');
  const editPaymentStatusSelect = document.getElementById('editPaymentStatus');

  // Search controls (ถ้ามีในหน้า)
  const searchForm         = document.getElementById('payrollSearchForm');
  const searchKeywordInput = document.getElementById('searchEmployeeKeyword');
  const searchStartInput   = document.getElementById('searchStartDate');
  const searchEndInput     = document.getElementById('searchEndDate');
  const clearSearchBtn     = document.getElementById('clearPayrollSearch');

  // (optional) advanced filters toolbar (ถ้ามี elements เหล่านี้ในหน้า)
  const $peEmployee = document.getElementById('pe-employee');
  const $peRun      = document.getElementById('pe-run');

  // --- Helpers ---
  const fmtBaht = (n) => Number(n || 0).toLocaleString('th-TH', { style: 'currency', currency: 'THB' });

  function showMessage(el, message, isError = false) {
    if (!el) return;
    el.textContent = message;
    el.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
    setTimeout(() => { el.textContent=''; el.className='mt-4 text-sm font-medium'; }, 5000);
  }
  function formatDateToInput(v) {
    if (!v) return '';
    const d = new Date(v);
    if (Number.isNaN(d.getTime())) return '';
    return d.toISOString().split('T')[0];
  }
  function runPeriodLabel(run) {
    const start = run.period_start || run.pay_period_start;
    const end   = run.period_end   || run.pay_period_end;
    return `${formatDateToInput(start)} - ${formatDateToInput(end)}`;
  }
  async function safeJson(resp) {
    try { return await resp.json(); }
    catch { return { detail: await resp.text() }; }
  }

  // ตารางรายละเอียดเงินเพิ่ม/หัก + คืนยอดรวม
  function renderMoneyList(containerDiv, raw, title) {
    containerDiv.innerHTML = `<h4 class="font-semibold mb-2">รายละเอียด${title}</h4>`;

    let data = raw;
    try {
      if (typeof raw === 'string') data = JSON.parse(raw || '[]');
    } catch {/* ignore */}

    // แปลงเป็น array {label, amount}
    let items = [];
    if (Array.isArray(data)) {
      items = data.map(it => ({
        label: it.label || it.name || it.code || '-',
        amount: Number(it.amount || 0),
      }));
    } else if (data && typeof data === 'object') {
      items = Object.keys(data).map(k => ({
        label: k,
        amount: Number(data[k] || 0),
      }));
    }

    if (!items.length) {
      containerDiv.insertAdjacentHTML(
        'beforeend',
        `<p class="text-sm text-gray-500">ยังไม่มีรายละเอียด${title}</p>`
      );
      return 0;
    }

    const rows = items.map(it => `
      <tr class="border-b last:border-b-0">
        <td class="px-3 py-1 text-sm">${it.label}</td>
        <td class="px-3 py-1 text-right text-sm">${it.amount.toLocaleString(undefined,{minimumFractionDigits:2})}</td>
      </tr>
    `).join('');

    const total = items.reduce((s, it) => s + (isFinite(it.amount) ? it.amount : 0), 0);

    containerDiv.insertAdjacentHTML('beforeend', `
      <div class="rounded-md border border-gray-200 overflow-hidden">
        <table class="min-w-full">
          <thead>
            <tr class="bg-gray-50">
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600">รายการ</th>
              <th class="px-3 py-2 text-right text-xs font-medium text-gray-600">จำนวน</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
          <tfoot>
            <tr class="bg-gray-50">
              <td class="px-3 py-2 text-right text-sm font-semibold">รวม</td>
              <td class="px-3 py-2 text-right text-sm font-semibold">
                ${total.toLocaleString(undefined,{minimumFractionDigits:2})}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    `);

    return total;
  }

  // ===== ✅ ดึงฐานเงินเดือนจาก Salary Structure ตามรอบจ่าย =====
  let SALARY_STRUCTS_CACHE = null; // โหลดครั้งแรกแล้ว cache ไว้
  async function getBaseSalaryFor(employeeId, runObj) {
    try {
      // โหลดโครงสร้างเงินเดือนทั้งหมด (ครั้งแรก)
      if (!SALARY_STRUCTS_CACHE) {
        const resp = await fetch(`${API_BASE_URL}/salary-structures/?limit=1000`);
        if (!resp.ok) return null;
        SALARY_STRUCTS_CACHE = await resp.json();
      }

      const periodEndStr = runObj?.period_end || runObj?.pay_period_end || null;
      const periodEnd = periodEndStr ? new Date(periodEndStr) : null;

      // เลือกของ employee เดียวกัน และมีผล <= period_end (ล่าสุดที่สุด)
      let best = null;
      for (const s of SALARY_STRUCTS_CACHE) {
        if (s.employee_id !== Number(employeeId)) continue;
        const eff = new Date(s.effective_date);
        if (Number.isNaN(eff.getTime())) continue;
        if (periodEnd && eff > periodEnd) continue; // ยังไม่ถึงรอบนี้
        if (!best || new Date(best.effective_date) < eff) best = s;
      }
      return best ? Number(best.base_salary || 0) : null;
    } catch {
      return null;
    }
  }

  // --- Dropdowns ---
  async function fetchDropdownData() {
    try {
      const [empResponse, payrollRunResponse] = await Promise.all([
        fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
        fetch(`${API_BASE_URL}/payroll-runs/`)
      ]);

      if (!empResponse.ok) throw new Error(`HTTP error! status: ${empResponse.status} for employees`);
      if (!payrollRunResponse.ok) {
        const e = await safeJson(payrollRunResponse);
        throw new Error(e.detail || `HTTP error! status: ${payrollRunResponse.status} for payroll runs`);
      }

      const employees = await empResponse.json();
      const payrollRuns = await payrollRunResponse.json();

      populateEmployeeDropdown(calcEmployeeIdSelect, employees);
      populatePayrollRunDropdown(calcPayrollRunIdSelect, payrollRuns);

      if ($peEmployee) populateEmployeeDropdown($peEmployee, employees);
      if ($peRun)      populatePayrollRunDropdown($peRun, payrollRuns);
    } catch (error) {
      console.error('Error fetching dropdown data:', error);
      showMessage(calculatePayrollEntryMessage, `ไม่สามารถโหลดข้อมูลพนักงาน/รอบ Payroll: ${error.message}`, true);
      showMessage(payrollEntriesMessage, `ไม่สามารถโหลดข้อมูลพนักงาน/รอบ Payroll: ${error.message}`, true);
    }
  }
  function populateEmployeeDropdown(select, employees, selectedId=null) {
    if (!select) return;
    select.innerHTML = '<option value="">-- เลือกพนักงาน --</option>';
    employees.forEach(e=>{
      const opt=document.createElement('option');
      opt.value=e.id;
      opt.textContent=`${e.first_name} ${e.last_name}`;
      if (selectedId && e.id===selectedId) opt.selected=true;
      select.appendChild(opt);
    });
  }
  function populatePayrollRunDropdown(select, runs, selectedId=null) {
    if (!select) return;
    select.innerHTML = '<option value="">-- เลือกรอบการจ่ายเงินเดือน --</option>';
    runs.forEach(run=>{
      const opt=document.createElement('option');
      opt.value=run.id;
      opt.textContent=`ID: ${run.id} (${runPeriodLabel(run)})`;
      if (selectedId && run.id===selectedId) opt.selected=true;
      select.appendChild(opt);
    });
  }

  // --- Entries table ---
  function buildEntriesURL() {
    const params = new URLSearchParams();

    const q = (searchKeywordInput?.value || '').trim();
    const s = searchStartInput?.value || '';
    const e = searchEndInput?.value   || '';
    if (q) params.set('q', q);
    if (s) params.set('start_date', s);
    if (e) params.set('end_date', e);

    if ($peEmployee?.value) params.set('employee_id', $peEmployee.value);
    if ($peRun?.value)      params.set('payroll_run_id', $peRun.value);

    const qs = params.toString();
    return `${API_BASE_URL}/payroll-entries/${qs ? `?${qs}` : ''}`;
  }

  async function fetchPayrollEntries() {
    payrollEntriesTableBody.innerHTML = `
      <tr><td colspan="8" class="px-6 py-4 text-center text-sm text-gray-500">กำลังโหลดข้อมูล...</td></tr>`;
    try {
      const url = buildEntriesURL();
      const resp = await fetch(url, { headers: { 'Accept': 'application/json' } });
      if (!resp.ok) {
        const e = await safeJson(resp);
        throw new Error(e.detail || `HTTP error! status: ${resp.status}`);
      }
      const entries = await resp.json();
      renderPayrollEntriesTable(entries);
    } catch (error) {
      console.error('Error fetching payroll entries:', error);
      payrollEntriesTableBody.innerHTML = `
        <tr><td colspan="8" class="px-6 py-4 text-center text-sm text-red-600">
          เกิดข้อผิดพลาดในการโหลดรายการเงินเดือน: ${error.message}
        </td></tr>`;
      showMessage(payrollEntriesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
    }
  }

  async function renderPayrollEntriesTable(entries) {
    payrollEntriesTableBody.innerHTML='';
    if (!entries.length) {
      payrollEntriesTableBody.innerHTML = `
        <tr><td colspan="8" class="px-6 py-4 text-center text-sm text-gray-500">ยังไม่มีข้อมูลรายการเงินเดือน</td></tr>`;
      return;
    }

    // แผนที่ชื่อ + แผนที่ run object
    const employeeMap = new Map();
    const payrollRunNameMap = new Map();
    const payrollRunObjMap  = new Map();

    try {
      const [empRes, runRes] = await Promise.all([
        fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
        fetch(`${API_BASE_URL}/payroll-runs/`)
      ]);
      const emps = empRes.ok ? await empRes.json() : [];
      const runs = runRes.ok ? await runRes.json() : [];
      emps.forEach(emp=> employeeMap.set(emp.id, `${emp.first_name} ${emp.last_name}`));
      runs.forEach(run=>{
        payrollRunNameMap.set(run.id, `ID: ${run.id} (${runPeriodLabel(run)})`);
        payrollRunObjMap.set(run.id, run);
      });
    } catch (e) {
      console.warn('Prefetch map failed', e);
    }

    entries.forEach(entry=>{
      const row = payrollEntriesTableBody.insertRow();
      row.className='hover:bg-gray-50';

      const employeeName   = employeeMap.get(entry.employee_id) || `ID: ${entry.employee_id} (ไม่พบข้อมูล)`;
      const payrollRunName = payrollRunNameMap.get(entry.payroll_run_id) || `ID: ${entry.payroll_run_id} (ไม่พบข้อมูล)`;

      let statusClass = 'bg-yellow-100 text-yellow-800';
      if (entry.payment_status === 'Paid') statusClass='bg-green-100 text-green-800';
      else if (entry.payment_status === 'Failed') statusClass='bg-red-100 text-red-800';

      row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${entry.id}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${payrollRunName}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeName}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${Number(entry.gross_salary||0).toFixed(2)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${Number(entry.net_salary||0).toFixed(2)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
            ${entry.payment_status}
          </span>
        </td>
        <td class="px-6 py-4 text-sm text-center">
          <a href="/api/v1/payroll/payroll-entries/${entry.id}/payslip.pdf"
             class="inline-block bg-emerald-600 hover:bg-emerald-700 text-white py-1 px-3 rounded-md">
            สลิป PDF
          </a>
          <a href="/payroll/payslip/${entry.id}"
             class="inline-block bg-gray-600 hover:bg-gray-700 text-white py-1 px-3 rounded-md ml-2" target="_blank">
            ดูตัวอย่าง
          </a>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
          <button data-id="${entry.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2">
            แก้ไข/ดูรายละเอียด
          </button>
          <button data-id="${entry.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md">
            ลบ
          </button>
        </td>
      `;
    });

    // --- Edit modal binding ---
    document.querySelectorAll('.edit-btn').forEach(btn=>{
      btn.addEventListener('click', async (ev)=>{
        const id = ev.target.dataset.id;
        try {
          const resp = await fetch(`${API_BASE_URL}/payroll-entries/${id}`);
          if (!resp.ok) {
            const e = await safeJson(resp);
            throw new Error(e.detail || `HTTP ${resp.status}`);
          }
          const entry = await resp.json();

          editPayrollEntryIdInput.value = entry.id;
          editPayrollRunNameInput.value = payrollRunNameMap.get(entry.payroll_run_id) || `ID: ${entry.payroll_run_id} (ไม่พบข้อมูล)`;
          editEmployeeNameInput.value   = employeeMap.get(entry.employee_id) || `ID: ${entry.employee_id} (ไม่พบข้อมูล)`;
          editGrossSalaryInput.value    = entry.gross_salary;
          editNetSalaryInput.value      = entry.net_salary;
          editPaymentDateInput.value    = formatDateToInput(entry.payment_date);
          editPaymentStatusSelect.value = entry.payment_status;

          const allowsSrc  = entry.calculated_allowances_json  ?? entry.calculated_allowances  ?? [];
          const deductsSrc = entry.calculated_deductions_json  ?? entry.calculated_deductions  ?? [];

          // วาดรายการ + สรุปยอด (เงินเพิ่ม/หัก)
          const allowTotal  = renderMoneyList(editCalculatedAllowancesDiv, allowsSrc,  'เงินเพิ่ม');
          const deductTotal = renderMoneyList(editCalculatedDeductionsDiv, deductsSrc, 'รายการหัก');

          // ✅ ใช้ฐานจาก Salary Structure (ล่าสุดที่มีผล <= period_end ของรอบนี้)
          const runObj = payrollRunObjMap.get(entry.payroll_run_id) || null;
          const baseFromStructure = await getBaseSalaryFor(entry.employee_id, runObj);
          const base = Number.isFinite(baseFromStructure) ? baseFromStructure : Number(entry.gross_salary||0);

          const grossPreview = base + allowTotal;
          const netPreview   = base + allowTotal - deductTotal;

          let summary = document.getElementById('editSummary');
          if (!summary) {
            summary = document.createElement('div');
            summary.id = 'editSummary';
            summary.className = 'mt-3 mb-4 flex flex-wrap gap-2';
            editCalculatedAllowancesDiv.parentNode.insertBefore(summary, editCalculatedAllowancesDiv);
          }
          summary.innerHTML = `
            <span class="px-2 py-1 text-xs rounded-full bg-gray-100">
              เงินเดือนฐาน (โครงสร้าง): <b>${fmtBaht(base)}</b>
            </span>
            <span class="px-2 py-1 text-xs rounded-full bg-emerald-100">
              รวมเงินเพิ่ม: <b>${fmtBaht(allowTotal)}</b>
            </span>
            <span class="px-2 py-1 text-xs rounded-full bg-rose-100">
              รวมรายการหัก: <b>${fmtBaht(deductTotal)}</b>
            </span>
            <span class="px-2 py-1 text-xs rounded-full bg-sky-100">
              รวมก่อนหัก: <b>${fmtBaht(grossPreview)}</b>
            </span>
            <span class="px-2 py-1 text-xs rounded-full bg-indigo-100">
              พรีวิวเงินสุทธิ: <b>${fmtBaht(netPreview)}</b>
            </span>
          `;

          editPayrollEntryModal.style.display='flex';
        } catch (error) {
          console.error(error);
          showMessage(payrollEntriesMessage, `โหลดรายการเพื่อแก้ไขล้มเหลว: ${error.message}`, true);
        }
      });
    });

    // --- Delete binding ---
    document.querySelectorAll('.delete-btn').forEach(btn=>{
      btn.addEventListener('click', async (ev)=>{
        const id = ev.target.dataset.id;
        if (!confirm(`ลบรายการเงินเดือน ID: ${id}?`)) return;
        try {
          const resp = await fetch(`${API_BASE_URL}/payroll-entries/${id}`, {method:'DELETE'});
          if (!resp.ok) {
            const e = await safeJson(resp);
            throw new Error(e.detail || 'ลบไม่สำเร็จ');
          }
          showMessage(payrollEntriesMessage, 'ลบรายการเงินเดือนเรียบร้อยแล้ว');
          fetchPayrollEntries();
        } catch (error) {
          showMessage(payrollEntriesMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
        }
      });
    });
  }

  // Calculate one entry
  calculatePayrollEntryForm?.addEventListener('submit', async (ev)=>{
    ev.preventDefault();
    const employeeId  = calcEmployeeIdSelect.value;
    const payrollRunId= calcPayrollRunIdSelect.value;
    if (!employeeId || !payrollRunId) {
      showMessage(calculatePayrollEntryMessage, 'กรุณาเลือกพนักงานและรอบการจ่ายเงินเดือน', true);
      return;
    }
    try {
            const resp = await fetch(`${API_BASE_URL}/payroll-entries/calculate/by-employee/${employeeId}/run/${payrollRunId}`, {
            method: 'POST',
            headers: { 'Content-Type':'application/json' }
        });

      if (!resp.ok) {
        const e = await safeJson(resp);
        if (Array.isArray(e.detail)) {
          const msg = e.detail.map(x => `${(x.loc||[]).join('.')}: ${x.msg}`).join('\n');
          throw new Error(`ข้อมูลไม่ถูกต้อง:\n${msg}`);
        }
        throw new Error(e.detail || 'คำนวณไม่สำเร็จ');
      }
      const newEntry = await resp.json();
      showMessage(calculatePayrollEntryMessage, `บันทึกรายการเงินเดือน ID: ${newEntry.id} เรียบร้อยแล้ว`);
      fetchPayrollEntries();
    } catch (error) {
      showMessage(calculatePayrollEntryMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
    }
  });

  // Edit submit
  editPayrollEntryForm?.addEventListener('submit', async (ev)=>{
    ev.preventDefault();
    const id    = editPayrollEntryIdInput.value;
    const gross = parseFloat(editGrossSalaryInput.value);
    const net   = parseFloat(editNetSalaryInput.value);
    const date  = editPaymentDateInput.value || null;
    const status= editPaymentStatusSelect.value;

    if (!Number.isFinite(gross) || !Number.isFinite(net) || !status) {
      showMessage(editPayrollEntryMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
      return;
    }
    const data = { gross_salary: gross, net_salary: net, payment_date: date, payment_status: status };
    Object.keys(data).forEach(k => (data[k]===''||data[k]==null) && delete data[k]);

    try {
      const resp = await fetch(`${API_BASE_URL}/payroll-entries/${id}`, {
        method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)
      });
      if (!resp.ok) {
        const e = await safeJson(resp);
        if (Array.isArray(e.detail)) {
          const msg = e.detail.map(x => `${(x.loc||[]).join('.')}: ${x.msg}`).join('\n');
          throw new Error(`ข้อมูลไม่ถูกต้อง:\n${msg}`);
        }
        throw new Error(e.detail || 'อัปเดตไม่สำเร็จ');
      }
      const updated = await resp.json();
      showMessage(payrollEntriesMessage, `อัปเดตรายการเงินเดือน ID: ${updated.id} เรียบร้อยแล้ว`);
      editPayrollEntryModal.style.display='none';
      fetchPayrollEntries();
    } catch (error) {
      showMessage(editPayrollEntryMessage, `เกิดข้อผิดพลาด: ${error.message}`, true);
    }
  });

  closeEditModalButton?.addEventListener('click', ()=>{
    editPayrollEntryModal.style.display='none';
    editPayrollEntryMessage.textContent='';
    editPaymentDateInput.value='';
  });

  // Search: submit + clear
  searchForm?.addEventListener('submit', (e) => {
    e.preventDefault();
    fetchPayrollEntries();
  });
  clearSearchBtn?.addEventListener('click', (e) => {
    e.preventDefault();
    if (searchKeywordInput) searchKeywordInput.value = '';
    if (searchStartInput)   searchStartInput.value   = '';
    if (searchEndInput)     searchEndInput.value     = '';
    if ($peEmployee) $peEmployee.value = '';
    if ($peRun)      $peRun.value      = '';
    fetchPayrollEntries();
  });

  // advanced selects auto reload (ถ้ามี)
  $peEmployee?.addEventListener('change', fetchPayrollEntries);
  $peRun?.addEventListener('change', fetchPayrollEntries);

  // Initial
  fetchDropdownData();
  fetchPayrollEntries();
});

// ===== Monthly Report Buttons =====
const reportMonthInput = document.getElementById('reportMonth');
const btnViewReport    = document.getElementById('btnViewReport');
const btnCsvReport     = document.getElementById('btnCsvReport');
const reportBox        = document.getElementById('reportBox');

btnViewReport?.addEventListener('click', async () => {
  const m = reportMonthInput?.value; // "YYYY-MM"
  if (!m) { alert('กรุณาเลือกเดือน'); return; }
  try {
    const res = await fetch(`/api/v1/payroll/payroll-entries/report?month=${m}`);
    if (!res.ok) throw new Error('โหลดรายงานไม่สำเร็จ');
    const data = await res.json();
    reportBox.classList.remove('hidden');
    reportBox.innerHTML = `
      <div class="font-semibold mb-2">รายงานเดือน: ${data.month}</div>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-2 mb-2">
        <div>รวมฐาน: <b>${Number(data.totals.base_salary||0).toLocaleString()}</b></div>
        <div>รวมเงินเพิ่ม: <b>${Number(data.totals.allowances_total||0).toLocaleString()}</b></div>
        <div>รวมรายการหัก: <b>${Number(data.totals.deductions_total||0).toLocaleString()}</b></div>
        <div>รวมก่อนหัก: <b>${Number(data.totals.gross_salary||0).toLocaleString()}</b></div>
        <div>รวมสุทธิ: <b>${Number(data.totals.net_salary||0).toLocaleString()}</b></div>
      </div>
      <details class="mt-2">
        <summary class="cursor-pointer text-sky-700">ดูรายละเอียดรายพนักงาน</summary>
        <div class="mt-2 overflow-auto">
          <table class="min-w-full text-xs">
            <thead><tr class="bg-gray-100">
              <th class="px-2 py-1 text-left">พนักงาน</th>
              <th class="px-2 py-1">Run</th>
              <th class="px-2 py-1">ช่วง</th>
              <th class="px-2 py-1 text-right">ฐาน</th>
              <th class="px-2 py-1 text-right">เพิ่ม</th>
              <th class="px-2 py-1 text-right">หัก</th>
              <th class="px-2 py-1 text-right">ก่อนหัก</th>
              <th class="px-2 py-1 text-right">สุทธิ</th>
              <th class="px-2 py-1">สถานะ</th>
            </tr></thead>
            <tbody>
              ${data.rows.map(r => `
                <tr class="border-b">
                  <td class="px-2 py-1">${r.employee_name} (#${r.employee_id})</td>
                  <td class="px-2 py-1 text-center">${r.payroll_run_id}</td>
                  <td class="px-2 py-1">${r.period_start} ~ ${r.period_end}</td>
                  <td class="px-2 py-1 text-right">${Number(r.base_salary).toLocaleString()}</td>
                  <td class="px-2 py-1 text-right">${Number(r.allowances_total).toLocaleString()}</td>
                  <td class="px-2 py-1 text-right">${Number(r.deductions_total).toLocaleString()}</td>
                  <td class="px-2 py-1 text-right">${Number(r.gross_salary).toLocaleString()}</td>
                  <td class="px-2 py-1 text-right">${Number(r.net_salary).toLocaleString()}</td>
                  <td class="px-2 py-1 text-center">${r.payment_status}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </details>
    `;
  } catch (e) {
    alert(e.message || e);
  }
});

btnCsvReport?.addEventListener('click', () => {
  const m = reportMonthInput?.value;
  if (!m) { alert('กรุณาเลือกเดือน'); return; }
  // โหลดเป็นไฟล์ CSV ตรงๆ
  window.location.href = `/api/v1/payroll/payroll-entries/report.csv?month=${m}`;
});
