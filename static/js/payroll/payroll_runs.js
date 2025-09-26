// static/js/payroll/payroll_runs.js
document.addEventListener('DOMContentLoaded', () => {
  console.log('payroll_runs.js loaded');

  const API_BASE_URL = '/api/v1/payroll';
  const DEFAULT_SCHEME_ID = 1;

  // ---------- helpers ----------
  function showMessage(el, msg, isErr = false) {
    if (!el) return;
    el.textContent = msg;
    el.className = `mt-4 text-sm font-medium ${isErr ? 'text-red-600' : 'text-green-600'}`;
    setTimeout(() => { el.textContent = ''; el.className = 'mt-4 text-sm font-medium'; }, 5000);
  }

  function toISODate(s) {
    if (!s) return null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s; // YYYY-MM-DD
    const m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/); // MM/DD/YYYY
    if (m) {
      const [, mm, dd, yyyy] = m;
      return `${yyyy}-${mm.padStart(2, '0')}-${dd.padStart(2, '0')}`;
    }
    return s;
  }

  function fmt(d) {
    if (!d) return '';
    const t = new Date(d);
    return isNaN(t.getTime()) ? '' : t.toISOString().split('T')[0];
  }

  async function safeJson(resp) {
    const clone = resp.clone();
    try { return await clone.json(); }
    catch {
      try { return { detail: await clone.text() }; }
      catch { return { detail: `HTTP ${resp.status}` }; }
    }
  }

  // ---------- elements ----------
  const addPayrollRunForm       = document.getElementById('addPayrollRunForm');
  const addPayrollRunMessage    = document.getElementById('addPayrollRunMessage');
  const addPayPeriodStartInput  = document.getElementById('addPayPeriodStart');
  const addPayPeriodEndInput    = document.getElementById('addPayPeriodEnd');

  const payrollRunsTableBody    = document.getElementById('payrollRunsTableBody');
  const payrollRunsMessage      = document.getElementById('payrollRunsMessage');

  // ---------- list runs ----------
  async function fetchPayrollRuns() {
    if (payrollRunsTableBody) {
      payrollRunsTableBody.innerHTML = `
        <tr><td colspan="7" class="px-6 py-4 text-center text-sm text-gray-500">กำลังโหลดข้อมูล...</td></tr>`;
    }
    try {
      const resp = await fetch(`${API_BASE_URL}/payroll-runs/`);
      if (!resp.ok) {
        const e = await safeJson(resp);
        throw new Error(e.detail || `HTTP ${resp.status}`);
      }
      const runs = await resp.json();
      renderRuns(runs);
    } catch (err) {
      if (payrollRunsTableBody) {
        payrollRunsTableBody.innerHTML = `
          <tr><td colspan="7" class="px-6 py-4 text-center text-sm text-red-600">
            เกิดข้อผิดพลาดในการโหลดรอบการจ่ายเงินเดือน: ${err.message}
          </td></tr>`;
      }
      showMessage(payrollRunsMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
    }
  }

  function renderRuns(runs) {
    if (!payrollRunsTableBody) return;
    payrollRunsTableBody.innerHTML = '';
    if (!runs.length) {
      payrollRunsTableBody.innerHTML = `
        <tr><td colspan="7" class="px-6 py-4 text-center text-sm text-gray-500">
          ยังไม่มีข้อมูลรอบการจ่ายเงินเดือน
        </td></tr>`;
      return;
    }

    runs.forEach(run => {
      const start   = run.period_start || run.pay_period_start;
      const end     = run.period_end   || run.pay_period_end;
      const created = run.created_at   || run.run_date;

      let badge = 'bg-yellow-100 text-yellow-800'; // PENDING
      if (run.status === 'COMPLETED')      badge = 'bg-green-100 text-green-800';
      else if (run.status === 'PROCESSING') badge = 'bg-blue-100 text-blue-800';
      else if (run.status === 'FAILED')     badge = 'bg-red-100 text-red-800';

      const tr = document.createElement('tr');
      tr.className = 'hover:bg-gray-50';
      tr.innerHTML = `
        <td class="px-6 py-4 text-sm font-medium text-gray-900">${run.id}</td>
        <td class="px-6 py-4 text-sm text-gray-700">${fmt(created)}</td>
        <td class="px-6 py-4 text-sm text-gray-700">${fmt(start)} ถึง ${fmt(end)}</td>
        <td class="px-6 py-4 text-sm text-gray-700">
          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${badge}">
            ${run.status}
          </span>
        </td>
        <td class="px-6 py-4 text-sm text-gray-700">${Number(run.total_amount_paid || 0).toFixed(2)}</td>
        <td class="px-6 py-4 text-sm text-gray-700">${run.notes || '-'}</td>
        <td class="px-6 py-4 text-center text-sm font-medium">
          <button data-id="${run.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md">
            ลบ
          </button>
        </td>`;
      payrollRunsTableBody.appendChild(tr);
    });

    // delete
    document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', async (ev) => {
        const id = ev.currentTarget.dataset.id;
        if (!confirm(`ลบรอบการจ่ายเงินเดือน ID: ${id}?`)) return;
        try {
          const resp = await fetch(`${API_BASE_URL}/payroll-runs/${id}`, { method: 'DELETE' });
          if (!resp.ok) {
            const e = await safeJson(resp);
            throw new Error(e.detail || 'ลบไม่สำเร็จ');
          }
          showMessage(payrollRunsMessage, 'ลบรอบการจ่ายเงินเดือนเรียบร้อยแล้ว');
          fetchPayrollRuns();
        } catch (err) {
          showMessage(payrollRunsMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
        }
      });
    });
  }

  // ---------- create run ----------
  document.addEventListener('submit', async (e) => {
    if (e.target !== addPayrollRunForm) return;
    e.preventDefault();
    e.stopImmediatePropagation();

    const start = toISODate(addPayPeriodStartInput?.value);
    const end   = toISODate(addPayPeriodEndInput?.value);

    if (!start || !end) {
      showMessage(addPayrollRunMessage, 'กรุณากรอกช่วงวันที่จ่าย (เริ่ม/สิ้นสุด)', true);
      return;
    }
    if (start > end) {
      showMessage(addPayrollRunMessage, 'ช่วงวันที่ไม่ถูกต้อง: วันเริ่ม > วันสิ้นสุด', true);
      return;
    }

    const payload = {
      scheme_id: DEFAULT_SCHEME_ID,
      period_start: start,
      period_end: end
      // status ไม่ส่ง ให้ backend default = PENDING
    };

    try {
      const resp = await fetch(`${API_BASE_URL}/payroll-runs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const e = await safeJson(resp);
        if (Array.isArray(e.detail)) {
          const msg = e.detail.map(x => `${x.loc?.join('.')}: ${x.msg}`).join('\n');
          throw new Error(`ข้อมูลไม่ถูกต้อง:\n${msg}`);
        }
        throw new Error(e.detail || `HTTP ${resp.status}`);
      }

      const newRun = await resp.json();
      showMessage(addPayrollRunMessage, `สร้างรอบการจ่ายเงินเดือน ID: ${newRun.id} เรียบร้อยแล้ว`);
      addPayrollRunForm.reset();
      fetchPayrollRuns();
    } catch (err) {
      showMessage(addPayrollRunMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
    }
    return false;
  }, true);

  // กัน default action เผื่อฟอร์มมี action เดิม
  if (addPayrollRunForm) {
    addPayrollRunForm.setAttribute('action', '#');
    addPayrollRunForm.setAttribute('novalidate', 'novalidate');
  }

  // init
  fetchPayrollRuns();
});
