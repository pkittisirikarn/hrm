// static/js/time_tracking/working_schedules.js
document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = '/api/v1/time-tracking';

  // ---------- Helpers ----------
  function showMessage(el, msg, isError = false) {
    if (!el) return;
    el.textContent = msg;
    el.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
    clearTimeout(el._t);
    el._t = setTimeout(() => {
      el.textContent = '';
      el.className = 'mt-4 text-sm font-medium';
    }, 5000);
  }

  async function formatApiErrorDetail(response) {
    let msg = `HTTP ${response.status}`;
    const ct = response.headers.get('content-type') || '';
    try {
      if (ct.includes('application/json')) {
        const j = await response.json();
        if (j?.detail) {
          if (typeof j.detail === 'string') msg = j.detail;
          else if (Array.isArray(j.detail)) {
            msg = j.detail.map(e => {
              const loc = e?.loc?.join('.') ?? '';
              return `${loc}: ${e?.msg ?? ''}`;
            }).join('\n');
          } else msg = JSON.stringify(j.detail);
        } else msg = JSON.stringify(j);
      } else {
        const t = await response.text();
        if (t) msg = t;
      }
    } catch { /* ignore */ }
    return msg;
  }

  const dashIfNull = v => (v === null || v === undefined || v === '' ? '-' : v);
  const toIntOrNull = v => {
    if (v === undefined || v === null) return null;
    const s = String(v).trim();
    if (!s.length) return null;
    const n = Number(s);
    return Number.isFinite(n) ? parseInt(n, 10) : null;
  };
  const asTimeOrNull = v => {
    if (v === undefined || v === null) return null;
    const s = String(v).trim();
    return s.length ? s : null;
  };

  const translateDayOfWeek = (val) => {
    const k = String(val || '').toLowerCase();
    if (k.startsWith('mon')) return 'จันทร์';
    if (k.startsWith('tue')) return 'อังคาร';
    if (k.startsWith('wed')) return 'พุธ';
    if (k.startsWith('thu')) return 'พฤหัสบดี';
    if (k.startsWith('fri')) return 'ศุกร์';
    if (k.startsWith('sat')) return 'เสาร์';
    if (k.startsWith('sun')) return 'อาทิตย์';
    // รองรับ enum name เช่น "WEDNESDAY"
    if (['monday','tuesday','wednesday','thursday','friday','saturday','sunday'].includes(k)) {
      return translateDayOfWeek(k);
    }
    return val ?? '-';
  };

  // ---------- Elements ----------
  // Add form
  const addForm = document.getElementById('addWorkingScheduleForm');
  const addMsg = document.getElementById('addWorkingScheduleMessage');
  const addEmployeeId = document.getElementById('addEmployeeId');
  const addName = document.getElementById('addName');
  const addDayOfWeek = document.getElementById('addDayOfWeek');
  const addIsWorkingDay = document.getElementById('addIsWorkingDay');
  const addStartTime = document.getElementById('addStartTime');
  const addEndTime = document.getElementById('addEndTime');
  const addBreakStartTime = document.getElementById('addBreakStartTime');
  const addBreakEndTime = document.getElementById('addBreakEndTime');
  const addIsActive = document.getElementById('addIsActive');
  const addIsDefault = document.getElementById('addIsDefault');

  const addLateGraceMin = document.getElementById('addLateGraceMin');
  const addEarlyLeaveGraceMin = document.getElementById('addEarlyLeaveGraceMin');
  const addAbsenceAfterMin = document.getElementById('addAbsenceAfterMin');
  const addStandardDailyMinutes = document.getElementById('addStandardDailyMinutes');
  const addBreakMinutesOverride = document.getElementById('addBreakMinutesOverride');

  // Table
  const tbody = document.getElementById('workingSchedulesTableBody');
  const tableMsg = document.getElementById('workingSchedulesMessage');

  // Edit modal
  const modal = document.getElementById('editWorkingScheduleModal');
  const closeEditModalButton = document.getElementById('closeEditModalButton');
  const editForm = document.getElementById('editWorkingScheduleForm');
  const editMsg = document.getElementById('editWorkingScheduleMessage');

  const editId = document.getElementById('editWorkingScheduleId');
  const editEmployeeId = document.getElementById('editEmployeeId');
  const editName = document.getElementById('editName');
  const editDayOfWeek = document.getElementById('editDayOfWeek');
  const editIsWorkingDay = document.getElementById('editIsWorkingDay');
  const editStartTime = document.getElementById('editStartTime');
  const editEndTime = document.getElementById('editEndTime');
  const editBreakStartTime = document.getElementById('editBreakStartTime');
  const editBreakEndTime = document.getElementById('editBreakEndTime');
  const editIsActive = document.getElementById('editIsActive');
  const editIsDefault = document.getElementById('editIsDefault');

  const editLateGraceMin = document.getElementById('editLateGraceMin');
  const editEarlyLeaveGraceMin = document.getElementById('editEarlyLeaveGraceMin');
  const editAbsenceAfterMin = document.getElementById('editAbsenceAfterMin');
  const editStandardDailyMinutes = document.getElementById('editStandardDailyMinutes');
  const editBreakMinutesOverride = document.getElementById('editBreakMinutesOverride');

  // ---------- Fetch & render ----------
  async function fetchWorkingSchedules() {
    if (tbody) {
      tbody.innerHTML = `<tr>
        <td colspan="15" class="px-6 py-4 text-center text-sm text-gray-500">กำลังโหลดข้อมูล...</td>
      </tr>`;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/working-schedules/`);
      if (!res.ok) throw new Error(await formatApiErrorDetail(res));
      const rows = await res.json();
      render(rows);
    } catch (e) {
      if (tbody) {
        tbody.innerHTML = `<tr>
          <td colspan="15" class="px-6 py-4 text-center text-sm text-red-600">โหลดข้อมูลล้มเหลว: ${e.message}</td>
        </tr>`;
      }
      showMessage(tableMsg, e.message, true);
    }
  }

  function render(items) {
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!Array.isArray(items) || !items.length) {
      tbody.innerHTML = `<tr>
        <td colspan="15" class="px-6 py-4 text-center text-sm text-gray-500">ยังไม่มีข้อมูลตารางเวลาทำงาน</td>
      </tr>`;
      return;
    }

    for (const s of items) {
      const hours = `${dashIfNull(s.start_time)} - ${dashIfNull(s.end_time)}`;

      const brk = (s.break_minutes_override ?? null) !== null
        ? `${s.break_minutes_override} นาที (override)`
        : `${dashIfNull(s.break_start_time)} - ${dashIfNull(s.break_end_time)}`;

      const policy = `${dashIfNull(s.late_grace_min)} / ${dashIfNull(s.early_leave_grace_min)} / ${dashIfNull(s.absence_after_min)}`;

      const tr = document.createElement('tr');
      tr.className = 'hover:bg-gray-50';
      tr.innerHTML = `
        <td class="px-6 py-3 text-sm">${s.id}</td>
        <td class="px-6 py-3 text-sm">${dashIfNull(s.employee_id)}</td>
        <td class="px-6 py-3 text-sm">${s.name}</td>
        <td class="px-6 py-3 text-sm">${translateDayOfWeek(s.day_of_week)}</td>
        <td class="px-6 py-3 text-sm">${s.is_working_day ? 'ใช่' : 'ไม่ใช่'}</td>
        <td class="px-6 py-3 text-sm">${hours}</td>
        <td class="px-6 py-3 text-sm">${brk}</td>
        <td class="px-6 py-3 text-sm">${policy}</td>
        <td class="px-6 py-3 text-sm">${dashIfNull(s.standard_daily_minutes)}</td>
        <td class="px-6 py-3 text-sm">${s.is_active ? 'Active' : '—'}/${s.is_default ? 'Default' : '—'}</td>
        <td class="px-6 py-3 text-sm text-right">
          <button class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded mr-2" data-id="${s.id}">แก้ไข</button>
          <button class="del-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded" data-id="${s.id}">ลบ</button>
        </td>
      `;
      tbody.appendChild(tr);
    }

    // bind events only to newly created buttons under tbody
    tbody.querySelectorAll('.edit-btn').forEach(btn => {
      btn.onclick = () => openEdit(btn.dataset.id);
    });
    tbody.querySelectorAll('.del-btn').forEach(btn => {
      btn.onclick = () => delRow(btn.dataset.id);
    });
  }

  async function openEdit(id) {
    try {
      const res = await fetch(`${API_BASE_URL}/working-schedules/${id}`);
      if (!res.ok) throw new Error(await formatApiErrorDetail(res));
      const s = await res.json();

      if (editId) editId.value = s.id;
      if (editEmployeeId) editEmployeeId.value = s.employee_id ?? '';
      if (editName) editName.value = s.name ?? '';
      if (editDayOfWeek) editDayOfWeek.value = s.day_of_week;
      if (editIsWorkingDay) editIsWorkingDay.checked = !!s.is_working_day;
      if (editStartTime) editStartTime.value = s.start_time || '';
      if (editEndTime) editEndTime.value = s.end_time || '';
      if (editBreakStartTime) editBreakStartTime.value = s.break_start_time || '';
      if (editBreakEndTime) editBreakEndTime.value = s.break_end_time || '';
      if (editIsActive) editIsActive.checked = !!s.is_active;
      if (editIsDefault) editIsDefault.checked = !!s.is_default;

      if (editLateGraceMin) editLateGraceMin.value = s.late_grace_min ?? '';
      if (editEarlyLeaveGraceMin) editEarlyLeaveGraceMin.value = s.early_leave_grace_min ?? '';
      if (editAbsenceAfterMin) editAbsenceAfterMin.value = s.absence_after_min ?? '';
      if (editStandardDailyMinutes) editStandardDailyMinutes.value = s.standard_daily_minutes ?? '';
      if (editBreakMinutesOverride) editBreakMinutesOverride.value = s.break_minutes_override ?? '';

      // show modal
      if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        modal.style.display = ''; // let Tailwind classes handle it
      }
    } catch (e) {
      showMessage(tableMsg, `โหลดข้อมูลแก้ไขล้มเหลว: ${e.message}`, true);
    }
  }

  async function delRow(id) {
    if (!confirm(`ลบตารางงาน #${id}?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/working-schedules/${id}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) throw new Error(await formatApiErrorDetail(res));
      showMessage(tableMsg, 'ลบสำเร็จ');
      fetchWorkingSchedules();
    } catch (e) {
      showMessage(tableMsg, e.message, true);
    }
  }

  // ---------- Submit add ----------
  if (addForm) {
    addForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      showMessage(addMsg, 'กำลังบันทึก...', false);

      const payload = {
        employee_id: toIntOrNull(addEmployeeId?.value),
        name: (addName?.value || '').trim(),
        day_of_week: addDayOfWeek?.value,
        is_working_day: !!addIsWorkingDay?.checked,
        start_time: asTimeOrNull(addStartTime?.value),
        end_time: asTimeOrNull(addEndTime?.value),
        break_start_time: asTimeOrNull(addBreakStartTime?.value),
        break_end_time: asTimeOrNull(addBreakEndTime?.value),
        is_active: !!addIsActive?.checked,
        is_default: !!addIsDefault?.checked,
        late_grace_min: toIntOrNull(addLateGraceMin?.value),
        early_leave_grace_min: toIntOrNull(addEarlyLeaveGraceMin?.value),
        absence_after_min: toIntOrNull(addAbsenceAfterMin?.value),
        standard_daily_minutes: toIntOrNull(addStandardDailyMinutes?.value),
        break_minutes_override: toIntOrNull(addBreakMinutesOverride?.value),
      };

      if (!payload.name || !payload.day_of_week) {
        showMessage(addMsg, 'กรุณากรอกชื่อและวันในสัปดาห์', true);
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/working-schedules/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await formatApiErrorDetail(res));

        showMessage(addMsg, 'เพิ่มสำเร็จ');
        addForm.reset();
        fetchWorkingSchedules();
      } catch (e) {
        showMessage(addMsg, e.message, true);
      }
    });
  }

  // ---------- Submit edit ----------
  if (editForm) {
    editForm.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      showMessage(editMsg, 'กำลังบันทึก...', false);

      const id = editId?.value;
      const payload = {
        employee_id: toIntOrNull(editEmployeeId?.value),
        name: (editName?.value || '').trim(),
        day_of_week: editDayOfWeek?.value,
        is_working_day: !!editIsWorkingDay?.checked,
        start_time: asTimeOrNull(editStartTime?.value),
        end_time: asTimeOrNull(editEndTime?.value),
        break_start_time: asTimeOrNull(editBreakStartTime?.value),
        break_end_time: asTimeOrNull(editBreakEndTime?.value),
        is_active: !!editIsActive?.checked,
        is_default: !!editIsDefault?.checked,
        late_grace_min: toIntOrNull(editLateGraceMin?.value),
        early_leave_grace_min: toIntOrNull(editEarlyLeaveGraceMin?.value),
        absence_after_min: toIntOrNull(editAbsenceAfterMin?.value),
        standard_daily_minutes: toIntOrNull(editStandardDailyMinutes?.value),
        break_minutes_override: toIntOrNull(editBreakMinutesOverride?.value),
      };

      if (!id) {
        showMessage(editMsg, 'ไม่พบ ID ตารางงาน', true);
        return;
      }
      if (!payload.name || !payload.day_of_week) {
        showMessage(editMsg, 'กรุณากรอกชื่อและวันในสัปดาห์', true);
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/working-schedules/${id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(await formatApiErrorDetail(res));

        showMessage(tableMsg, 'อัปเดตสำเร็จ');
        // close modal
        if (modal) {
          modal.classList.add('hidden');
          modal.classList.remove('flex');
        }
        editMsg.textContent = '';
        fetchWorkingSchedules();
      } catch (e) {
        showMessage(editMsg, e.message, true);
      }
    });
  }

  // ---------- Close modal ----------
  if (closeEditModalButton) {
    closeEditModalButton.addEventListener('click', () => {
      if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      }
      if (editMsg) editMsg.textContent = '';
    });
  }
  // ปิดด้วย Esc
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
      if (editMsg) editMsg.textContent = '';
    }
  });

  // ---------- init ----------
  fetchWorkingSchedules();
});
