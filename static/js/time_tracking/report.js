// static/js/time_tracking/report.js
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('searchForm');
  const tbody = document.getElementById('reportTableBody');
  const msg = document.getElementById('reportMessage');
  const clearBtn = document.getElementById('clearSearchBtn');
  const submitBtn = form ? form.querySelector('button[type="submit"]') : null;

  // ถ้าเปิดไฟล์นี้จากหน้าอื่นที่ไม่มีฟอร์มนี้ ให้จบการทำงานเงียบๆ
  if (!form || !tbody) {
    console.warn('[report] form or tbody not found — script idle');
    return;
  }

  const API_URL = '/api/v1/time-tracking/report/data';

  const loadingRow = () => `<tr><td colspan="6" class="text-center py-6">กำลังโหลดข้อมูล...</td></tr>`;
  const emptyRow   = () => `<tr><td colspan="6" class="text-center py-6">ไม่พบข้อมูล</td></tr>`;

  const fmtDT = (s) => {
    if (!s) return '-';
    const d = new Date(s);
    if (isNaN(d)) return s;
    return d.toLocaleDateString('th-TH') + ' ' + d.toLocaleTimeString('th-TH', { hour12: false });
  };

  // เก็บค่าพารามิเตอร์แบบไม่พังถ้า field ไม่มี
  function collectParams() {
    const fd = new FormData(form); // ไม่อ่าน .value ตรงๆ เพื่อกัน null
    const employee = (fd.get('employee_id_number') || '').toString().trim();
    const dateFrom = (fd.get('date_from') || '').toString().trim();
    const dateTo   = (fd.get('date_to')   || '').toString().trim();

    const p = {};
    if (employee) p.employee_id_number = employee;
    if (dateFrom || dateTo) {
      p.date_from = dateFrom || dateTo;
      p.date_to   = dateTo   || dateFrom;
    }
    return p;
  }

  // รองรับทั้ง [] และ {items: []}
  const normalizeItems = (payload) =>
    Array.isArray(payload) ? payload : (payload && Array.isArray(payload.items) ? payload.items : []);

  async function fetchReport(params) {
    const url = new URL(API_URL, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && String(v).trim() !== '') {
        url.searchParams.set(k, v);
      }
    });
    console.log('[report] GET', url.toString());
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  function renderRows(items) {
    if (!items.length) {
      tbody.innerHTML = emptyRow();
      if (msg) msg.textContent = 'ไม่พบข้อมูล';
      return;
    }
    tbody.innerHTML = items.map((r) => `
      <tr>
        <td class="px-6 py-3 whitespace-nowrap">${r.id ?? ''}</td>
        <td class="px-6 py-3 whitespace-nowrap">${r.employee?.employee_id_number ?? ''}</td>
        <td class="px-6 py-3 whitespace-nowrap">
          ${r.employee?.full_name ?? [r.employee?.first_name, r.employee?.last_name].filter(Boolean).join(' ') ?? ''}
        </td>
        <td class="px-6 py-3 whitespace-nowrap">${fmtDT(r.check_in_time)}</td>
        <td class="px-6 py-3 whitespace-nowrap">${fmtDT(r.check_out_time)}</td>
        <td class="px-6 py-3 whitespace-nowrap">${r.status ?? r.status_text ?? 'Approved'}</td>
      </tr>
    `).join('');
    if (msg) msg.textContent = `พบ ${items.length} รายการ`;
  }

  async function run(e) {
    if (e) e.preventDefault();
    tbody.innerHTML = loadingRow();
    if (msg) msg.textContent = '';
    try {
      const data = await fetchReport(collectParams());
      const items = normalizeItems(data);
      renderRows(items);
    } catch (err) {
      console.error('[report] load failed:', err);
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-6 text-red-600">โหลดข้อมูลล้มเหลว</td></tr>`;
      if (msg) msg.textContent = 'เกิดข้อผิดพลาดในการโหลดข้อมูล';
    }
  }

  // bind event แบบสองชั้นกันพลาด
  form.addEventListener('submit', run);
  if (submitBtn) submitBtn.addEventListener('click', run);
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      form.reset();
      tbody.innerHTML = emptyRow();
      if (msg) msg.textContent = '';
    });
  }

  // โหลดข้อมูลครั้งแรก
  run();
});
