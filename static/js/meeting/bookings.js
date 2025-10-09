// static/js/meeting/bookings.js
document.addEventListener('DOMContentLoaded', () => {
  const API_MEETING = '/api/v1/meeting';
  const API_DM = '/api/v1/data-management';

  // form fields
  const roomSel    = document.getElementById('roomSelect');
  const titleInp   = document.getElementById('subjectInput');          // subject
  const orgEmail   = document.getElementById('requesterEmailInput');   // requester_email
  const contactInp = document.getElementById('contactInput');          // ผู้ติดต่อ (อาจไม่มี)
  const attSel     = document.getElementById('attendeesSelect');
  const startInp   = document.getElementById('startInput');
  const endInp     = document.getElementById('endInput');
  const notesInp   = document.getElementById('notesInput');
  const statusSel  = document.getElementById('statusSelect');          // PENDING/APPROVED/REJECTED

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
    if (roomSel) {
      roomSel.innerHTML = `<option value="">-- เลือกห้อง --</option>` +
        rooms.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
    }
  }

  async function loadEmployees() {
    const emps = await getJSON(`${API_DM}/employees/`);
    if (attSel) {
      attSel.innerHTML = emps.map(e => {
        const label = `${e.first_name ?? ''} ${e.last_name ?? ''}${e.employee_id_number ? ' ('+e.employee_id_number+')' : ''}`.trim();
        return `<option value="${e.id}">${label}</option>`;
      }).join('');
    }
  }

  async function loadBookings() {
    const rows = await getJSON(`${API_MEETING}/bookings/`);
    renderTable(rows);
  }

  function renderTable(rows) {
    if (!tbody) return;
    tbody.innerHTML = (rows || []).map(b => {
      // แสดงชื่อผู้เข้าร่วม ถ้าไม่มีก็ fallback เป็นอีเมล
      const attendeeLabels = (b.attendees || [])
        .map(a => (a.attendee_name && a.attendee_name.trim()) || a.attendee_email)
        .filter(Boolean);

      const attendeeCount = (b.attendees || []).length;

      const statusText = (typeof b.status === 'string')
        ? b.status
        : (b.status?.name || 'PENDING');

      return `
        <tr class="border-b">
          <td class="px-3 py-2">${b.id}</td>
          <td class="px-3 py-2">${b.room?.name ?? b.room_id}</td>
          <td class="px-3 py-2">${b.subject}</td>
          <td class="px-3 py-2">${b.contact_person || '-'}</td>
          <td class="px-3 py-2">
            ${new Date(b.start_time).toLocaleString()} - ${new Date(b.end_time).toLocaleString()}
          </td>
          <td class="px-3 py-2">${attendeeLabels.length ? attendeeLabels.join(', ') : '-'}</td>
          <td class="px-3 py-2 text-center">${attendeeCount}</td>
          <td class="px-3 py-2 font-semibold">${statusText}</td>
          <td class="px-3 py-2">
            <div class="flex flex-wrap gap-2">
              <button class="bg-emerald-600 hover:bg-emerald-700 text-white px-2 py-1 rounded" data-status="${b.id}|APPROVED">อนุมัติ</button>
              <button class="bg-amber-600 hover:bg-amber-700 text-white px-2 py-1 rounded" data-status="${b.id}|PENDING">รออนุมัติ</button>
              <button class="bg-rose-600 hover:bg-rose-700 text-white px-2 py-1 rounded" data-status="${b.id}|REJECTED">ปฏิเสธ</button>
              <button class="bg-gray-600 hover:bg-gray-700 text-white px-2 py-1 rounded" data-cancel="${b.id}">ยกเลิก</button>
              <button class="bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded" data-del="${b.id}">ลบ</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }

  function getSelectedEmployeeIds() {
    if (!attSel) return [];
    return Array.from(attSel.selectedOptions)
      .map(o => parseInt(o.value, 10))
      .filter(Number.isFinite);
  }

  async function setStatus(bookingId, status) {
    // Backend ตอนนี้รองรับแบบ query param
    const r = await fetch(
      `${API_MEETING}/bookings/${bookingId}/status?status=${encodeURIComponent(status)}`,
      { method: 'POST' }
    );
    if (!r.ok) throw new Error(await formatApiErrorForAlert(r));
    return r.json();
  }

  if (btnBook) {
    btnBook.addEventListener('click', async () => {
      try {
        const payload = {
          room_id: roomSel ? parseInt(roomSel.value, 10) : null,
          subject: (titleInp?.value || '').trim(),
          requester_email: (orgEmail?.value || '').trim(),
          contact_person: (contactInp?.value || '').trim() || null,
          start_time: startInp?.value ? `${startInp.value}:00` : null,
          end_time:   endInp?.value   ? `${endInp.value}:00`   : null,
          notes: (notesInp?.value || '').trim() || null,
          attendee_employee_ids: getSelectedEmployeeIds(),
          status: (statusSel?.value || 'PENDING')   // <-- ส่งเป็น "สตริง"
        };

        if (!payload.room_id || !payload.subject || !payload.requester_email || !payload.start_time || !payload.end_time) {
          alert('กรุณากรอกข้อมูลที่จำเป็นให้ครบ');
          return;
        }

        await postJSON(`${API_MEETING}/bookings/`, payload);
        await loadBookings();

        // reset
        if (titleInp)  titleInp.value = '';
        if (notesInp)  notesInp.value = '';
        if (startInp)  startInp.value = '';
        if (endInp)    endInp.value = '';
        if (attSel)    attSel.selectedIndex = -1;
        if (statusSel) statusSel.value = 'PENDING';
        if (contactInp) contactInp.value = '';
      } catch (e) {
        alert(`ผิดพลาด: ${e.message}`);
      }
    });
  }

  // delegation: เปลี่ยนสถานะ / ยกเลิก / ลบ
  if (tbody) {
    tbody.addEventListener('click', async (e) => {
      const btn = e.target.closest('button');
      if (!btn) return;

      const actionStatus = btn.dataset.status; // "<id>|APPROVED" etc.
      const cancelId = btn.dataset.cancel;
      const delId = btn.dataset.del;

      try {
        if (actionStatus) {
          const [id, status] = actionStatus.split('|');
          await setStatus(id, status);
          await loadBookings();
          return;
        }
        if (cancelId) {
          const r = await fetch(`${API_MEETING}/bookings/${cancelId}/cancel`, { method: 'POST' });
          if (!r.ok) throw new Error(await formatApiErrorForAlert(r));
          await loadBookings();
          return;
        }
        if (delId) {
          if (!confirm('ต้องการลบรายการนี้หรือไม่?')) return;
          const rDel = await fetch(`${API_MEETING}/bookings/${delId}`, { method: 'DELETE' });
          if (!rDel.ok && rDel.status !== 204) throw new Error(await formatApiErrorForAlert(rDel));
          await loadBookings();
        }
      } catch (err) {
        alert(`ผิดพลาด: ${err.message}`);
      }
    });
  }

  // init
  Promise.all([loadRooms(), loadEmployees(), loadBookings()]).catch(console.error);
});
