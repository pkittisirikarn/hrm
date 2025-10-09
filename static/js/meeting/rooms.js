(() => {
  const $ = (id) => document.getElementById(id);

  const form = $('roomForm');
  const fName = $('rmName');
  const fLocation = $('rmLocation');
  const fCapacity = $('rmCapacity');
  const fCoord = $('rmCoordinator');
  const fCoordEmail = $('rmCoordinatorEmail');
  const fActive = $('rmActive');
  const fImage = $('rmImage');
  const fPreview = $('rmPreview');
  const btnAdd = $('btnSubmit');
  const tbody = $('roomsTableBody');
  const msg = $('roomsMsg');

  // Edit modal
  const editModal = $('editModal');
  const eId = $('e_id');
  const eName = $('e_name');
  const eLocation = $('e_location');
  const eCapacity = $('e_capacity');
  const eCoord = $('e_coordinator');
  const eCoordEmail = $('e_coordinator_email');
  const eActive = $('e_active');
  const eNotes = $('e_notes');
  const eSave = $('e_save');
  const eClose = $('e_close');

  const API = {
    rooms: '/api/v1/meeting/rooms/',
    employees: '/api/v1/data-management/employees/',
    upload: (roomId) => `/api/v1/meeting/rooms/${roomId}/image`,
  };

  let employeeMap = {};

  function flash(text, ok = true) {
    if (!msg) return;
    msg.textContent = text || '';
    msg.className = ok ? 'text-green-600' : 'text-red-600';
    if (text) setTimeout(() => (msg.textContent = ''), 3000);
  }

  if (fImage && fPreview) {
    fImage.addEventListener('change', () => {
      const file = fImage.files && fImage.files[0];
      if (!file) {
        fPreview.classList.add('hidden');
        fPreview.src = '';
        return;
      }
      fPreview.src = URL.createObjectURL(file);
      fPreview.classList.remove('hidden');
    });
  }

  async function loadEmployees() {
    try {
      const res = await fetch(API.employees);
      const data = await res.json();
      employeeMap = {};
      const options =
        `<option value="">-- เลือกผู้ประสานงาน --</option>` +
        data
          .map((e) => {
            const name = `${e.first_name || ''} ${e.last_name || ''}`.trim() || e.email || `#${e.id}`;
            employeeMap[e.id] = name;
            return `<option value="${e.id}">${name}</option>`;
          })
          .join('');
      if (fCoord) fCoord.innerHTML = options;
      if (eCoord) eCoord.innerHTML = options;
    } catch (err) {
      console.error(err);
    }
  }

  async function loadRooms() {
    const res = await fetch(API.rooms);
    const rows = await res.json();
    renderTable(rows);
  }

  function renderTable(rows) {
    if (!tbody) return;
    tbody.innerHTML = rows
      .map((r) => {
        const coordText = r.coordinator_employee_id
          ? (employeeMap[r.coordinator_employee_id] || `#${r.coordinator_employee_id}`)
          : (r.coordinator_email || '-');

        return `
        <tr>
          <td class="px-3 py-2 border">${r.id}</td>
          <td class="px-3 py-2 border">${r.image_url ? `<img src="${r.image_url}" class="h-16 w-24 object-cover rounded">` : '-'}</td>
          <td class="px-3 py-2 border">${r.name || '-'}</td>
          <td class="px-3 py-2 border">${r.location || '-'}</td>
          <td class="px-3 py-2 border">${r.capacity ?? '-'}</td>
          <td class="px-3 py-2 border">${coordText}</td>
          <td class="px-3 py-2 border">${r.is_active ? 'ใช้งาน' : 'ปิด'}</td>
          <td class="px-3 py-2 border">
            <button class="bg-amber-500 hover:bg-amber-600 text-white px-3 py-1 rounded" data-act="edit" data-id="${r.id}">แก้ไข</button>
          </td>
          <td class="px-3 py-2 border">
            <button class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded" data-act="del" data-id="${r.id}">ลบ</button>
          </td>
        </tr>`;
      })
      .join('');

    tbody.querySelectorAll('button[data-act="del"]').forEach((btn) => btn.addEventListener('click', onDelete));
    tbody.querySelectorAll('button[data-act="edit"]').forEach((btn) => btn.addEventListener('click', onEditOpen));
  }

  async function onDelete(e) {
    const id = e.currentTarget.getAttribute('data-id');
    if (!confirm('ลบห้องนี้หรือไม่?')) return;
    const res = await fetch(API.rooms + id, { method: 'DELETE' });
    if (res.ok) {
      flash('ลบห้องสำเร็จ');
      await loadRooms();
    } else {
      const t = await res.text();
      flash('ลบไม่สำเร็จ: ' + t, false);
    }
  }

  function fillEditForm(room) {
    if (!editModal) return;
    eId.value = room.id;
    eName.value = room.name || '';
    eLocation.value = room.location || '';
    eCapacity.value = room.capacity ?? 4;
    eCoord.value = room.coordinator_employee_id || '';
    eCoordEmail.value = room.coordinator_email || '';
    eActive.checked = !!room.is_active;
    eNotes.value = room.notes || '';
  }

  async function onEditOpen(e) {
    if (!editModal) return;
    const id = e.currentTarget.getAttribute('data-id');
    const res = await fetch(API.rooms);
    const rows = await res.json();
    const room = rows.find((x) => String(x.id) === String(id));
    if (!room) return;
    fillEditForm(room);
    editModal.classList.remove('hidden');
    editModal.classList.add('flex');
  }

  function closeEdit() {
    if (editModal) {
      editModal.classList.add('hidden');
      editModal.classList.remove('flex');
    }
  }

  async function saveEdit() {
    const id = eId.value;
    const payload = {
      name: (eName.value || '').trim() || null,
      location: (eLocation.value || '').trim() || null,
      capacity: eCapacity.value ? Number(eCapacity.value) : null,
      coordinator_employee_id: eCoord.value ? Number(eCoord.value) : null,
      coordinator_email: (eCoordEmail.value || '').trim() || null,
      is_active: !!eActive.checked,
      notes: (eNotes.value || '').trim() || null,
    };
    const res = await fetch(API.rooms + id, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      flash('บันทึกการแก้ไขสำเร็จ');
      closeEdit();
      await loadRooms();
    } else {
      const t = await res.text();
      alert('บันทึกไม่สำเร็จ: ' + t);
    }
  }

  async function createRoom(ev) {
    if (ev) ev.preventDefault();
    if (!fName || !btnAdd) return;
    if (!fName.value.trim()) {
      flash('กรุณากรอกชื่อห้อง', false);
      return;
    }

    btnAdd.disabled = true;
    const before = btnAdd.textContent;
    btnAdd.textContent = 'กำลังบันทึก...';

    try {
      const payload = {
        name: fName.value.trim(),
        location: (fLocation?.value || '').trim() || null,
        capacity: fCapacity?.value ? Number(fCapacity.value) : 4,
        coordinator_employee_id: fCoord?.value ? Number(fCoord.value) : null,
        coordinator_email: (fCoordEmail?.value || '').trim() || null,
        is_active: !!(fActive && fActive.checked),
      };

      const res = await fetch(API.rooms, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text() || 'สร้างห้องไม่สำเร็จ');
      const room = await res.json();

      const file = fImage && fImage.files && fImage.files[0];
      if (file) {
        const fd = new FormData();
        fd.append('file', file);
        const up = await fetch(API.upload(room.id), { method: 'POST', body: fd });
        if (!up.ok) console.warn('อัพโหลดรูปไม่สำเร็จ', await up.text());
      }

      // clear form
      fName.value = '';
      if (fLocation) fLocation.value = '';
      if (fCapacity) fCapacity.value = '4';
      if (fCoord) fCoord.value = '';
      if (fCoordEmail) fCoordEmail.value = '';
      if (fActive) fActive.checked = true;
      if (fImage) fImage.value = '';
      if (fPreview) { fPreview.classList.add('hidden'); fPreview.src = ''; }

      flash(`เพิ่มห้อง #${room.id} สำเร็จ`);
      await loadRooms();
    } catch (err) {
      console.error(err);
      flash(String(err.message || err), false);
    } finally {
      btnAdd.disabled = false;
      btnAdd.textContent = before || 'บันทึก';
    }
  }

  // Bind
  if (btnAdd) btnAdd.addEventListener('click', createRoom);
  if (form) form.addEventListener('submit', createRoom);
  if (eClose) eClose.addEventListener('click', closeEdit);
  if (eSave) eSave.addEventListener('click', saveEdit);

  // Init
  loadEmployees().then(loadRooms);
})();
