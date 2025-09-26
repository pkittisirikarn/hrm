document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = '/api/v1/time-tracking';

  // Elements
  const openBtn = document.getElementById('openRebuildAttendanceModal');
  const modal = document.getElementById('rebuildAttendanceModal');
  const cancelBtn = document.getElementById('cancelRebuildAttendance');
  const confirmBtn = document.getElementById('confirmRebuildAttendance');
  const msgInline = document.getElementById('attendanceToolsMessage');
  const msgModal = document.getElementById('rebuildModalMsg');

  const startInput = document.getElementById('attStartDate');
  const endInput = document.getElementById('attEndDate');
  const empInput = document.getElementById('attEmployeeId');

  // Helpers
  const show = el => el.classList.remove('hidden');
  const hide = el => el.classList.add('hidden');
  const setMsg = (el, text, isError = false) => {
    el.textContent = text || '';
    el.className = 'text-sm ' + (isError ? 'text-red-600' : 'text-gray-600');
  };
  const toDateStr = v => (v || '').trim();
  const toIntOrNull = v => {
    if (v === '' || v === null || v === undefined) return null;
    const n = Number(v);
    return Number.isFinite(n) ? parseInt(n, 10) : null;
  };

  // Open/close modal
  if (openBtn) {
    openBtn.addEventListener('click', () => {
      // default: today
      const today = new Date();
      const iso = today.toISOString().slice(0, 10);
      if (!startInput.value) startInput.value = iso;
      if (!endInput.value) endInput.value = iso;

      setMsg(msgModal, '');
      show(modal);
    });
  }
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => hide(modal));
  }

  // API call: /attendance/rebuild
  async function rebuildAttendance({ start, end, employee_id }) {
    const p = new URLSearchParams();
    p.set('start', start);
    p.set('end', end);
    if (employee_id !== null && employee_id !== undefined) {
      p.set('employee_id', String(employee_id));
    }

    const resp = await fetch(`${API_BASE_URL}/attendance/rebuild?${p.toString()}`, {
      method: 'POST'
    });

    // รองรับทั้ง 200/201/204 เป็น success
    if (!resp.ok) {
      let detail = `HTTP ${resp.status}`;
      try {
        const ct = resp.headers.get('content-type') || '';
        if (ct.includes('application/json')) {
          const j = await resp.json();
          if (j && j.detail) detail = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
        } else {
          const t = await resp.text();
          if (t) detail = t.slice(0, 300);
        }
      } catch (e) { /* ignore */ }
      throw new Error(detail);
    }

    try {
      // เผื่อ API คืนข้อความสรุปมา
      const j = await resp.json();
      return j;
    } catch {
      return { ok: true };
    }
  }

  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      setMsg(msgModal, 'กำลังทำงาน...', false);
      confirmBtn.disabled = true;

      const start = toDateStr(startInput.value);
      const end = toDateStr(endInput.value);
      const employee_id = toIntOrNull(empInput.value);

      if (!start || !end) {
        setMsg(msgModal, 'กรุณาระบุช่วงวันที่ให้ครบ', true);
        confirmBtn.disabled = false;
        return;
      }

      try {
        const res = await rebuildAttendance({ start, end, employee_id });
        setMsg(msgInline, 'Rebuild เสร็จแล้ว', false);
        hide(modal);
        // ถ้าหน้าปัจจุบันมีตารางรายงาน ให้เรียกโหลดใหม่ได้ เช่น:
        // if (typeof reloadReport === 'function') reloadReport();
      } catch (err) {
        setMsg(msgModal, `ผิดพลาด: ${err.message}`, true);
      } finally {
        confirmBtn.disabled = false;
      }
    });
  }
});
