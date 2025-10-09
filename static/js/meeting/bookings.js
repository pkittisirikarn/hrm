document.addEventListener('DOMContentLoaded', () => {
  const API_MEETING = '/api/v1/meeting';
  const API_DM = '/api/v1/data-management';

  const roomSel = document.getElementById('roomSelect');
  const titleInp  = document.getElementById('subjectInput');        // << ใช้ตัวแปรนี้
  const orgEmail  = document.getElementById('requesterEmailInput');  // << และตัวแปรนี้
  const attSel  = document.getElementById('attendeesSelect');
  const startInp= document.getElementById('startInput');
  const endInp  = document.getElementById('endInput');
  const notesInp= document.getElementById('notesInput');

  const btnBook = document.getElementById('btnBook');
  const tbody   = document.getElementById('bookingsTableBody');

  const getJSON = async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  };

  async function formatApiErrorForAlert(response) {
    let msg = `เกิดข้อผิดพลาด (HTTP ${response.status})`;
    const ct = response.headers.get('content-type') || '';
    try {
      if (ct.includes('application/json')) {
        const data = await response.json();
        if (Array.isArray(data.detail)) {
          msg = data.detail.map(e => {
            const loc = Array.isArray(e.loc) ? e.loc.join('.') : e.loc;
            return `• ${loc}: ${e.msg}`;
          }).join('\n');
        } else if (data && data.detail) {
          msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        } else {
          msg = JSON.stringify(data).slice(0, 500);
        }
      } else {
        msg = (await response.text()).slice(0, 500);
      }
    } catch {}
    return msg;
  }

  const postJSON = async (url, payload) => {
    const r = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    if (!r.ok) throw new Error(await formatApiErrorForAlert(r));
    return r.json();
  };

  async function loadRooms() {
    const rooms = await getJSON(`${API_MEETING}/rooms/`);
    roomSel.innerHTML = `<option value="">-- เลือกห้อง --</option>` +
      rooms.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
  }

  async function loadEmployees() {
    const emps = await getJSON(`${API_DM}/employees/`);
    attSel.innerHTML = emps.map(e => {
      const label = `${e.first_name} ${e.last_name}${e.employee_id_number ? ' ('+e.employee_id_number+')' : ''}`;
      return `<option value="${e.id}">${label}</option>`;
    }).join('');
  }

  async function loadBookings() {
    const rows = await getJSON(`${API_MEETING}/bookings/`);
    renderTable(rows);
  }

  function renderTable(rows) {
    tbody.innerHTML = (rows || []).map(b => {
      // ดึงอีเมลผู้เข้าร่วมจากความสัมพันธ์ (ถ้ามี)
      const attendeeEmails = (b.attendees || [])
        .map(a => a.attendee_email)
        .filter(Boolean);

      return `
        <tr class="border-b">
          <td class="px-3 py-2">${b.id}</td>
          <td class="px-3 py-2">${b.room?.name ?? b.room_id}</td>
          <td class="px-3 py-2">${b.subject}</td>
          <td class="px-3 py-2">${new Date(b.start_time).toLocaleString()} - ${new Date(b.end_time).toLocaleString()}</td>
          <td class="px-3 py-2">${attendeeEmails.length ? attendeeEmails.join(', ') : '-'}</td>
          <td class="px-3 py-2">${b.status}</td>
          <td class="px-3 py-2">
            <button class="bg-amber-600 text-white px-2 py-1 rounded" data-cancel="${b.id}">ยกเลิก</button>
            <button class="bg-red-600 text-white px-2 py-1 rounded" data-del="${b.id}">ลบ</button>
          </td>
        </tr>
      `;
    }).join('');
  }

  function getSelectedEmployeeIds() {
    return Array.from(attSel.selectedOptions)
      .map(o => parseInt(o.value, 10))
      .filter(Number.isFinite);
  }

  btnBook.addEventListener('click', async () => {
    try {
      const payload = {
        room_id: parseInt(roomSel.value, 10),
        subject: (titleInp.value || '').trim(),           // << ใช้ชื่อให้ตรง schema
        requester_email: (orgEmail.value || '').trim(),   // << ใช้ชื่อให้ตรง schema
        start_time: startInp.value ? `${startInp.value}:00` : null,
        end_time: endInp.value ? `${endInp.value}:00` : null,
        notes: (notesInp.value || '').trim() || null,
        attendee_employee_ids: getSelectedEmployeeIds(),
      };
      if (!payload.room_id || !payload.subject || !payload.requester_email || !payload.start_time || !payload.end_time) {
        alert('กรุณากรอกข้อมูลที่จำเป็นให้ครบ');
        return;
      }
      await postJSON(`${API_MEETING}/bookings/`, payload);
      await loadBookings();
      titleInp.value = ''; notesInp.value = '';
      startInp.value = ''; endInp.value = '';
      attSel.selectedIndex = -1;
    } catch (e) {
      alert(`ผิดพลาด: ${e.message}`);
    }
  });

  // delegation สำหรับปุ่มยกเลิก/ลบ
  tbody.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;

    const cancelId = btn.dataset.cancel;
    const delId = btn.dataset.del;

    try {
      if (cancelId) {
        const r = await fetch(`/api/v1/meeting/bookings/${cancelId}/cancel`, { method: 'POST' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        await loadBookings();
      }
      if (delId) {
        if (!confirm('ต้องการลบรายการนี้หรือไม่?')) return;
        const r = await fetch(`/api/v1/meeting/bookings/${delId}`, { method: 'DELETE' });
        if (!r.ok && r.status !== 204) throw new Error(`HTTP ${r.status}`);
        await loadBookings();
      }
    } catch (err) {
      alert(`ผิดพลาด: ${err.message}`);
    }
  });

  // init
  Promise.all([loadRooms(), loadEmployees(), loadBookings()]).catch(console.error);
});
