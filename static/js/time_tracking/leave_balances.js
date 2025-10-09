document.addEventListener('DOMContentLoaded', () => {
  const API = '/api/v1/time-tracking';
  const DM  = '/api/v1/data-management';

  const elEmp = document.getElementById('lbEmployee');
  const elYear= document.getElementById('lbYear');
  const btnLoad = document.getElementById('lbLoad');
  const btnSeed = document.getElementById('lbSeed');
  const tbody = document.getElementById('lbBody');
  const msg = document.getElementById('lbMsg');

  const showMsg = (t, ok=false) => { msg.textContent=t; msg.className=`mt-3 text-sm ${ok?'text-green-600':'text-red-600'}`; setTimeout(()=>msg.textContent='',3000); };

  async function loadEmployees(){
    const r = await fetch(`${DM}/employees/`);
    const rows = await r.json();
    elEmp.innerHTML = `<option value="">-- ทั้งหมด --</option>` + rows.map(e=>`<option value="${e.id}">${e.id} - ${e.first_name} ${e.last_name}</option>`).join('');
  }

  async function loadBalances(){
    tbody.innerHTML = `<tr><td colspan="7" class="text-center p-4">กำลังโหลด...</td></tr>`;
    const params = new URLSearchParams();
    if (elEmp.value) params.set('employee_id', elEmp.value);
    if (elYear.value) params.set('year', elYear.value);
    const r = await fetch(`${API}/leave-balances/?${params.toString()}`);
    if(!r.ok){ showMsg(`โหลดผิดพลาด: ${r.status}`, false); tbody.innerHTML=''; return; }
    const rows = await r.json();
    if(!rows.length){ tbody.innerHTML = `<tr><td colspan="7" class="text-center p-4">ไม่มีข้อมูล</td></tr>`; return; }
    tbody.innerHTML = rows.map(x=>`
      <tr>
        <td class="px-4 py-2">${x.employee_id}</td>
        <td class="px-4 py-2">${x.leave_type_name ?? x.leave_type_id}</td>
        <td class="px-4 py-2 text-right"><input data-id="${x.id}" data-f="opening_quota" class="w-24 border rounded px-1 text-right" type="number" step="0.5" value="${x.opening_quota ?? 0}"></td>
        <td class="px-4 py-2 text-right"><input data-id="${x.id}" data-f="accrued" class="w-24 border rounded px-1 text-right" type="number" step="0.5" value="${x.accrued ?? 0}"></td>
        <td class="px-4 py-2 text-right">${(x.used ?? 0).toFixed(2)}</td>
        <td class="px-4 py-2 text-right">${(x.remaining ?? 0).toFixed(2)}</td>
        <td class="px-4 py-2 text-center"><button data-id="${x.id}" class="lbSave bg-blue-600 text-white px-2 py-1 rounded">บันทึก</button></td>
      </tr>
    `).join('');
    document.querySelectorAll('.lbSave').forEach(btn=>{
      btn.addEventListener('click', async ()=>{
        const id = btn.dataset.id;
        const rowInputs = tbody.querySelectorAll(`input[data-id="${id}"]`);
        const payload = {};
        rowInputs.forEach(i => payload[i.dataset.f] = parseFloat(i.value||0));
        const qs = new URLSearchParams();
        if ('opening_quota' in payload) qs.set('opening_quota', payload.opening_quota);
        if ('accrued' in payload)      qs.set('accrued', payload.accrued);
        const r = await fetch(`${API}/leave-balances/${id}?${qs.toString()}`, { method:'PUT' });
        if(!r.ok){ showMsg('บันทึกไม่สำเร็จ', false); return; }
        showMsg('บันทึกแล้ว', true);
        loadBalances();
      });
    });
  }

  btnLoad.addEventListener('click', loadBalances);
  btnSeed.addEventListener('click', async ()=>{
    if(!elYear.value){ showMsg('กรุณาใส่ปี', false); return; }
    const r = await fetch(`${API}/leave-balances/seed?year=${elYear.value}`, { method:'POST' });
    if(!r.ok){ showMsg('Seed ไม่สำเร็จ', false); return; }
    showMsg('Seed สำเร็จ', true);
    loadBalances();
  });

  loadEmployees().then(loadBalances);
});
