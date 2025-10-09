// static/js/time_tracking/leave_requests.js
document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = '/api/v1/time-tracking';
  const DATA_MGMT_API_BASE_URL = '/api/v1/data-management';

  // --- Elements ---
  const addLeaveRequestForm     = document.getElementById('addLeaveRequestForm');
  const addLeaveRequestMessage  = document.getElementById('addLeaveRequestMessage');
  const addEmployeeIdSelect     = document.getElementById('addEmployeeId');
  const addLeaveTypeIdSelect    = document.getElementById('addLeaveTypeId');
  const addStartDateInput       = document.getElementById('addStartDate');
  const addEndDateInput         = document.getElementById('addEndDate');
  const addReasonInput          = document.getElementById('addReason');

  const leaveRequestsTableBody  = document.getElementById('leaveRequestsTableBody');
  const leaveRequestsMessage    = document.getElementById('leaveRequestsMessage');

  const editLeaveRequestModal   = document.getElementById('editLeaveRequestModal');
  const closeEditModalButton    = document.getElementById('closeEditModalButton');
  const editLeaveRequestForm    = document.getElementById('editLeaveRequestForm');
  const editLeaveRequestMessage = document.getElementById('editLeaveRequestMessage');

  const editLeaveRequestIdInput = document.getElementById('editLeaveRequestId');
  const editEmployeeIdSelect    = document.getElementById('editEmployeeId');
  const editLeaveTypeIdSelect   = document.getElementById('editLeaveTypeId');
  const editStartDateInput      = document.getElementById('editStartDate');
  const editEndDateInput        = document.getElementById('editEndDate');
  const editReasonInput         = document.getElementById('editReason');
  const editStatusSelect        = document.getElementById('editStatus');

  // รายงานสิทธิ์ (Balance) ตอนยื่น
  const leaveBalanceBox = document.getElementById('leaveBalanceBox');
  const lbQuota = document.getElementById('lbQuota');
  const lbUsed  = document.getElementById('lbUsed');
  const lbAvail = document.getElementById('lbAvail');
  const lbNote  = document.getElementById('lbNote');

  // --- Helpers ---
  const thisYear = () => new Date().getFullYear();

  const showMessage = (el, msg, isError = false) => {
    if (!el) return;
    el.textContent = msg;
    el.className = `mt-4 text-sm font-medium ${isError ? 'text-red-600' : 'text-green-600'}`;
    setTimeout(() => { el.textContent = ''; }, 5000);
  };

  const formatDateTimeLocal = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); // แสดงตาม local
    return d.toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
  };

  async function refreshLeaveBalance() {
    if (!addEmployeeIdSelect.value || !addLeaveTypeIdSelect.value) {
      leaveBalanceBox?.classList.add('hidden');
      return;
    }
    try {
      const url = new URL(`${API_BASE_URL}/leave-requests/balance`, window.location.origin);
      url.searchParams.set('employee_id', addEmployeeIdSelect.value);
      url.searchParams.set('leave_type_id', addLeaveTypeIdSelect.value);
      url.searchParams.set('year', String(thisYear()));
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      lbQuota.textContent = data.quota?.toFixed ? data.quota.toFixed(2) : data.quota;
      lbUsed.textContent  = data.used_approved?.toFixed ? data.used_approved.toFixed(2) : data.used_approved;
      lbAvail.textContent = data.available?.toFixed ? data.available.toFixed(2) : data.available;
      lbNote.textContent  = data.affects_balance ? '' : '(ประเภทนี้ไม่หักยอด)';
      leaveBalanceBox.classList.remove('hidden');
    } catch (e) {
      console.error('balance failed', e);
      leaveBalanceBox.classList.add('hidden');
    }
  }

  // --- Dropdowns ---
  async function fetchDropdownData() {
    try {
      const [empRes, ltRes] = await Promise.all([
        fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
        fetch(`${API_BASE_URL}/leave-types/`)
      ]);
      if (!empRes.ok) throw new Error(`Failed to fetch employees: ${empRes.statusText}`);
      if (!ltRes.ok)  throw new Error(`Failed to fetch leave types: ${ltRes.statusText}`);

      const employees = await empRes.json();
      const leaveTypes = await ltRes.json();

      populateEmployeeDropdown(addEmployeeIdSelect, employees);
      populateEmployeeDropdown(editEmployeeIdSelect, employees);
      populateLeaveTypeDropdown(addLeaveTypeIdSelect, leaveTypes);
      populateLeaveTypeDropdown(editLeaveTypeIdSelect, leaveTypes);
    } catch (err) {
      console.error('Error fetching dropdown data:', err);
      showMessage(addLeaveRequestMessage, `ไม่สามารถโหลดข้อมูล: ${err.message}`, true);
    }
  }

  function populateEmployeeDropdown(select, employees) {
    select.innerHTML = '<option value="">-- เลือกพนักงาน --</option>';
    employees.forEach(e => {
      const opt = document.createElement('option');
      opt.value = e.id;
      opt.textContent = `${e.first_name} ${e.last_name}`;
      select.appendChild(opt);
    });
  }

  function populateLeaveTypeDropdown(select, leaveTypes) {
    select.innerHTML = '<option value="">-- เลือกประเภทการลา --</option>';
    leaveTypes.forEach(lt => {
      const opt = document.createElement('option');
      opt.value = lt.id;
      opt.textContent = lt.name;
      select.appendChild(opt);
    });
  }

  // --- List / Table ---
  async function fetchLeaveRequests() {
    leaveRequestsTableBody.innerHTML =
      `<tr><td colspan="8" class="text-center p-4">กำลังโหลด...</td></tr>`;
    try {
      const res = await fetch(`${API_BASE_URL}/leave-requests/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const list = await res.json();
      await renderLeaveRequestsTable(list);
    } catch (err) {
      leaveRequestsTableBody.innerHTML =
        `<tr><td colspan="8" class="text-center p-4 text-red-600">เกิดข้อผิดพลาดในการโหลดข้อมูล</td></tr>`;
      showMessage(leaveRequestsMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
    }
  }

  async function renderLeaveRequestsTable(leaveRequests) {
    leaveRequestsTableBody.innerHTML = '';
    if (!leaveRequests.length) {
      leaveRequestsTableBody.innerHTML =
        `<tr><td colspan="8" class="text-center p-4">ยังไม่มีข้อมูลคำขอลา</td></tr>`;
      return;
    }

    // map ชื่อพนักงาน/ประเภท
    const employeeMap = new Map();
    const leaveTypeMap = new Map();
    try {
      const [empRes, ltRes] = await Promise.all([
        fetch(`${DATA_MGMT_API_BASE_URL}/employees/`),
        fetch(`${API_BASE_URL}/leave-types/`)
      ]);
      const employees = await empRes.json();
      const leaveTypes = await ltRes.json();
      employees.forEach(emp => employeeMap.set(emp.id, `${emp.first_name} ${emp.last_name}`));
      leaveTypes.forEach(lt  => leaveTypeMap.set(lt.id, lt.name));
    } catch {
      showMessage(leaveRequestsMessage, 'ไม่สามารถโหลดชื่อพนักงาน/ประเภทการลาได้', true);
    }

    leaveRequests.forEach(req => {
      const row = leaveRequestsTableBody.insertRow();
      row.className = 'hover:bg-gray-50';

      const employeeName = employeeMap.get(req.employee_id) || `ID: ${req.employee_id}`;
      const leaveTypeName = leaveTypeMap.get(req.leave_type_id) || `ID: ${req.leave_type_id}`;
      const numDays = (typeof req.num_days === 'number') ? req.num_days.toFixed(2) : 'N/A';

      let statusClass = 'bg-yellow-100 text-yellow-800';
      if (req.status === 'Approved') statusClass = 'bg-green-100 text-green-800';
      else if (req.status === 'Rejected' || req.status === 'Cancelled') statusClass = 'bg-red-100 text-red-800';

      row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${req.id}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${employeeName}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${leaveTypeName}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
          ${new Date(req.start_date).toLocaleString('th-TH')} ถึง ${new Date(req.end_date).toLocaleString('th-TH')}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">${numDays}</td>
        <td class="px-6 py-4 whitespace-normal text-sm text-gray-700 max-w-xs overflow-hidden text-ellipsis">${req.reason || '-'}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
          <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
            ${req.status}
          </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
          <button data-id="${req.id}" class="edit-btn bg-yellow-500 hover:bg-yellow-600 text-white py-1 px-3 rounded-md mr-2">แก้ไข</button>
          <button data-id="${req.id}" class="delete-btn bg-red-600 hover:bg-red-700 text-white py-1 px-3 rounded-md">ลบ</button>
        </td>
      `;
    });

    attachTableButtonListeners();
  }

  function attachTableButtonListeners() {
    // edit
    document.querySelectorAll('.edit-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        try {
          const res = await fetch(`${API_BASE_URL}/leave-requests/${id}`);
          if (!res.ok) throw new Error('Failed to fetch leave request details');
          const req = await res.json();

          editLeaveRequestIdInput.value = req.id;
          editEmployeeIdSelect.value    = req.employee_id;
          editLeaveTypeIdSelect.value   = req.leave_type_id;
          editStartDateInput.value      = formatDateTimeLocal(req.start_date);
          editEndDateInput.value        = formatDateTimeLocal(req.end_date);
          editReasonInput.value         = req.reason || '';
          editStatusSelect.value        = req.status;

          editLeaveRequestModal.style.display = 'flex';
        } catch (err) {
          showMessage(leaveRequestsMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
        }
      });
    });

    // delete
    document.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.currentTarget.dataset.id;
        if (!confirm(`คุณแน่ใจหรือไม่ที่ต้องการลบคำขอลา ID: ${id} นี้?`)) return;
        try {
          const res = await fetch(`${API_BASE_URL}/leave-requests/${id}`, { method: 'DELETE' });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'เกิดข้อผิดพลาดในการลบ');
          }
          showMessage(leaveRequestsMessage, 'ลบคำขอลาเรียบร้อยแล้ว');
          fetchLeaveRequests();
        } catch (err) {
          showMessage(leaveRequestsMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
        }
      });
    });
  }

  // --- Create (with pre-check balance) ---
  addLeaveRequestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {
      employee_id: parseInt(addEmployeeIdSelect.value),
      leave_type_id: parseInt(addLeaveTypeIdSelect.value),
      start_date: addStartDateInput.value,
      end_date: addEndDateInput.value,
      reason: addReasonInput.value,
    };
    if (!data.employee_id || !data.leave_type_id || !data.start_date || !data.end_date || !data.reason) {
      showMessage(addLeaveRequestMessage, 'กรุณากรอกข้อมูลที่จำเป็นทั้งหมด', true);
      return;
    }

    // pre-check balance
    try {
      const y = thisYear();
      const url = new URL(`${API_BASE_URL}/leave-requests/balance`, window.location.origin);
      url.searchParams.set('employee_id', String(data.employee_id));
      url.searchParams.set('leave_type_id', String(data.leave_type_id));
      url.searchParams.set('year', String(y));
      const res = await fetch(url.toString());
      if (res.ok) {
        const bal = await res.json();
        // คำนวณจำนวนวันแบบคร่าว ๆ (8 ชม.)
        const s = new Date(data.start_date);
        const e2 = new Date(data.end_date);
        const mins = Math.max(0, Math.floor((e2 - s) / 60000));
        const reqDays = (mins === 0 ? 480 : mins) / 480.0;
        if (bal.affects_balance && bal.quota > 0 && bal.available < reqDays) {
          showMessage(addLeaveRequestMessage,
            `สิทธิ์ไม่พอ: ขอ ${reqDays.toFixed(2)} วัน เหลือ ${bal.available.toFixed(2)} วัน`, true);
          return;
        }
      }
    } catch {
      // ให้ backend ตรวจอีกรอบ
    }

    try {
      const res = await fetch(`${API_BASE_URL}/leave-requests/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'เกิดข้อผิดพลาดในการยื่นคำขอลา');
      }
      const created = await res.json();
      showMessage(addLeaveRequestMessage, `ยื่นคำขอลา ID: ${created.id} เรียบร้อยแล้ว`);
      addLeaveRequestForm.reset();
      refreshLeaveBalance();
      fetchLeaveRequests();
    } catch (err) {
      showMessage(addLeaveRequestMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
    }
  });

  // --- Edit submit ---
  editLeaveRequestForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = editLeaveRequestIdInput.value;
    const data = {
      employee_id: parseInt(editEmployeeIdSelect.value),
      leave_type_id: parseInt(editLeaveTypeIdSelect.value),
      start_date: editStartDateInput.value,
      end_date: editEndDateInput.value,
      reason: editReasonInput.value,
      status: editStatusSelect.value,
    };
    try {
      const res = await fetch(`${API_BASE_URL}/leave-requests/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'เกิดข้อผิดพลาดในการอัปเดต');
      }
      showMessage(leaveRequestsMessage, `อัปเดตคำขอลา ID: ${id} เรียบร้อยแล้ว`);
      editLeaveRequestModal.style.display = 'none';
      fetchLeaveRequests();
    } catch (err) {
      showMessage(editLeaveRequestMessage, `เกิดข้อผิดพลาด: ${err.message}`, true);
    }
  });

  // --- Close edit modal ---
  closeEditModalButton.addEventListener('click', () => {
    editLeaveRequestModal.style.display = 'none';
  });

  // --- Balance on change (create form) ---
  addEmployeeIdSelect.addEventListener('change', refreshLeaveBalance);
  addLeaveTypeIdSelect.addEventListener('change', refreshLeaveBalance);
  addStartDateInput.addEventListener('change', refreshLeaveBalance);
  addEndDateInput.addEventListener('change', refreshLeaveBalance);

  // --- Initial load ---
  fetchDropdownData();
  fetchLeaveRequests();
});
