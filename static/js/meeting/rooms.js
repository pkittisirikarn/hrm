document.addEventListener('DOMContentLoaded', () => {
  const API = '/api/v1/meeting/rooms';
  const $ = s => document.querySelector(s);
  const tb = $('#roomsTableBody');
  const msg = $('#roomsMessage');

  const show = (el, text, ok=false) => { el.textContent = text; el.className = `text-sm ${ok?'text-green-600':'text-red-600'}`; setTimeout(()=>{el.textContent=''}, 4000); };

  async function fetchRooms(){
    tb.innerHTML = `<tr><td colspan="7" class="text-center p-4">กำลังโหลด...</td></tr>`;
    const r = await fetch(`${API}/`); if(!r.ok){ tb.innerHTML=''; show(msg, 'โหลดข้อมูลห้องไม่สำเร็จ'); return; }
    const rows = await r.json();
    tb.innerHTML = rows.map(x=>`
      <tr>
        <td class="border px-3 py-2">${x.id}</td>
        <td class="border px-3 py-2">${x.name}</td>
        <td class="border px-3 py-2">${x.location||'-'}</td>
        <td class="border px-3 py-2">${x.capacity}</td>
        <td class="border px-3 py-2">${x.equipment||'-'}</td>
        <td class="border px-3 py-2">${x.is_active?'ใช้งาน':'ปิด'}</td>
        <td class="border px-3 py-2">
          <button class="bg-red-600 text-white px-2 py-1 rounded" data-del="${x.id}">ลบ</button>
        </td>
      </tr>`).join('');
  }

  $('#addRoomForm').addEventListener('submit', async (e)=>{
    e.preventDefault();
    const payload = {
      name: $('#name').value.trim(),
      location: $('#location').value.trim() || null,
      capacity: parseInt($('#capacity').value||'4',10),
      equipment: $('#equipment').value.trim() || null,
      is_active: $('#isActive').checked
    };
    const r = await fetch(`${API}/`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
    if(!r.ok){ const t = await r.text(); show(msg, `เพิ่มห้องไม่สำเร็จ: ${t}`); return; }
    show(msg, 'เพิ่มห้องสำเร็จ', true);
    e.target.reset();
    fetchRooms();
  });

  document.body.addEventListener('click', async (ev)=>{
    const id = ev.target.getAttribute?.('data-del');
    if(!id) return;
    if(!confirm('ยืนยันการลบห้องนี้?')) return;
    const r = await fetch(`${API}/${id}`, { method:'DELETE' });
    if(!r.ok){ show(msg, 'ลบไม่สำเร็จ'); return; }
    show(msg, 'ลบสำเร็จ', true); fetchRooms();
  });

  fetchRooms();
});
