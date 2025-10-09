const rowsEl = document.getElementById('rows');
const f = {
  q: document.getElementById('f-q'),
  status: document.getElementById('f-status'),
  source: document.getElementById('f-source'),
  dept: document.getElementById('f-dept'),
};

async function load() {
  const url = new URL('/api/v1/recruitment/candidates/', window.location.origin);
  if (f.q.value) url.searchParams.set('q', f.q.value);
  if (f.status.value) url.searchParams.set('status', f.status.value);
  if (f.source.value) url.searchParams.set('source', f.source.value);
  if (f.dept.value) url.searchParams.set('dept', f.dept.value);
  const r = await fetch(url.toString());
  const data = await r.json();

  rowsEl.innerHTML = '';
  data.forEach(item => {
    const tr = document.createElement('tr');
    tr.className = 'border-b hover:bg-gray-50';

    const statusTH = window.STATUS_THAI?.[item.status] || item.status;

    tr.innerHTML = `
      <td class="py-2 pr-2">
        <div class="font-medium">${item.full_name}</div>
        <div class="text-xs text-gray-500">${item.email || ''} ${item.phone ? '• ' + item.phone : ''}</div>
      </td>
      <td class="py-2 pr-2">${item.position_applied || ''}</td>
      <td class="py-2 pr-2">${item.department || ''}</td>
      <td class="py-2 pr-2">${statusTH}</td>
      <td class="py-2 pr-2 text-xs text-gray-500">${new Date(item.stage_updated_at).toLocaleString()}</td>
      <td class="py-2 pr-2 whitespace-nowrap flex gap-2">
        <a class="text-blue-600 hover:underline" href="/recruitment/candidate/edit?id=${item.id}">แก้ไข</a>
        <button class="text-red-600 hover:underline" data-id="${item.id}">ลบ</button>
      </td>`;

    tr.querySelector('button[data-id]')?.addEventListener('click', async (ev) => {
      const id = ev.target.getAttribute('data-id');
      if (!confirm('ลบผู้สมัครนี้?')) return;
      const r = await fetch(`/api/v1/recruitment/candidates/${id}`, { method: 'DELETE' });
      if (r.ok) load(); else alert('ลบไม่สำเร็จ');
    });

    rowsEl.appendChild(tr);
  });
}

document.getElementById('btn-search').addEventListener('click', load);
['q','status','source','dept'].forEach(k => f[k].addEventListener('keydown', (e)=>{ if(e.key==='Enter'){ load(); }}));

load();

// modal helpers
const modal = document.getElementById('file-modal');
const fileList = document.getElementById('file-list');
document.getElementById('file-close').addEventListener('click', ()=> modal.classList.add('hidden'));

async function openFiles(candidateId) {
  fileList.innerHTML = '<div class="text-gray-500">กำลังโหลด…</div>';
  modal.classList.remove('hidden');
  const r = await fetch(`/api/v1/recruitment/candidates/${candidateId}/files`);
  if (!r.ok) { fileList.innerHTML = '<div class="text-red-600">โหลดไฟล์ไม่สำเร็จ</div>'; return; }
  const files = await r.json();
  if (!files.length) { fileList.innerHTML = '<div class="text-gray-500">ไม่มีไฟล์แนบ</div>'; return; }
  fileList.innerHTML = '';
  files.forEach(f => {
    const a = document.createElement('a');
    a.href = f.file_url; a.target = '_blank'; a.rel = 'noopener';
    a.className = 'block px-3 py-2 rounded border hover:bg-gray-50';
    a.textContent = `${f.original_name || 'ไฟล์'} (${(f.size || 0)} bytes)`;
    fileList.appendChild(a);
  });
}

// bind ปุ่ม "ไฟล์"
tr.querySelector('[data-files]')?.addEventListener('click', (ev) => {
  const id = ev.target.getAttribute('data-files');
  openFiles(id);
});
