// static/js/time_tracking/leave_balance_view.js
document.addEventListener('DOMContentLoaded', () => {
  const API = '/api/v1/time-tracking';
  const DM  = '/api/v1/data-management';

  const $emp  = document.getElementById('lbEmployee');
  const $year = document.getElementById('lbYear');
  const $load = document.getElementById('lbLoad');
  const $seed = document.getElementById('lbSeed');
  const $body = document.getElementById('lbBody');
  const $msg  = document.getElementById('lbMsg');

  const fmt = n => (Number(n || 0)).toFixed(2);

  // -------- LeaveType cache (ดู base quota) --------
  const LT_BY_ID = Object.create(null);

  // =========================
  // ฟิลเตอร์ด้วย pills
  // =========================
  const FilterState = { current: 'all' };

  function createFilterButton(label, value, isActive = false) {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = label;
    b.dataset.filter = value; // 'all' หรือ `lt:<id>`
    b.className =
      'lt-filter px-3 py-1 rounded-full border text-sm ' +
      (isActive ? 'bg-blue-600 text-white' : 'bg-white hover:bg-gray-50');
    b.addEventListener('click', onFilterClick);
    return b;
  }

  function onFilterClick(e) {
    const val = e.currentTarget.dataset.filter;
    FilterState.current = val;
    document.querySelectorAll('#ltFilterBar .lt-filter').forEach(btn => {
      const active = btn.dataset.filter === val;
      btn.classList.toggle('bg-blue-600', active);
      btn.classList.toggle('text-white', active);
    });
    applyFilterToTable();
  }

  function buildFilterBar(leaveTypes) {
    const bar = document.getElementById('ltFilterBar');
    if (!bar) return;
    bar.innerHTML = '';
    bar.appendChild(createFilterButton('ทั้งหมด', 'all', true));
    leaveTypes.forEach(t => {
      bar.appendChild(createFilterButton(t.name, `lt:${t.id}`));
    });
  }

  function applyFilterToTable() {
    const rows = document.querySelectorAll('#lbBody tr');
    rows.forEach(tr => {
      const match =
        FilterState.current === 'all' ||
        (`lt:${tr.dataset.ltId}` === FilterState.current);
      tr.style.display = match ? '' : 'none';
    });
  }

  // =========================
  // helpers
  // =========================
  async function fetchJSON(url, opts) {
    const res = await fetch(url, opts);
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  }

  async function loadEmployees() {
    const emps = await fetchJSON(`${DM}/employees/`);
    $emp.innerHTML = emps
      .map(
        e =>
          `<option value="${e.id}">${e.id} - ${e.first_name} ${e.last_name}</option>`
      )
      .join('');
  }

  async function loadLeaveTypes() {
    const types = await fetchJSON(`${API}/leave-types/?affects_balance=true`);
    types.forEach(t => {
      LT_BY_ID[t.id] = t;
    });
    buildFilterBar(types);
  }

  function renderRows(items) {
    $body.innerHTML = '';
    if (!items.length) {
      $body.innerHTML =
        `<tr><td colspan="7" class="text-center py-6">ไม่พบข้อมูล</td></tr>`;
      return;
    }

    for (const r of items) {
      const lt    = LT_BY_ID[r.leave_type_id] || {};
      const base  = Number(lt.annual_quota ?? 0);

      // opening/accrued จริงจาก API (บางระบบอาจเป็น opening_quota)
      const openingDB = Number(
        (r.opening ?? r.opening_quota ?? base)
      );
      const accruedDB = Number(r.accrued ?? 0);

      // รวมสิทธิ์จริง = openingDB + accruedDB
      const totalActual = openingDB + accruedDB;

      // ช่อง “เพิ่ม/ลด” = รวมจริง - base
      const extra = totalActual - base;

      const tr = document.createElement('tr');
      tr.dataset.ltId = String(r.leave_type_id);
      tr.innerHTML = `
        <td class="px-4 py-2">${r.employee_id}</td>
        <td class="px-4 py-2">
          ${r.leave_type_name}
          <div class="text-xs text-gray-500">Base (annual): ${fmt(base)}</div>
        </td>
        <td class="px-4 py-2">
          <input data-k="opening" class="border rounded px-2 py-1 w-24 bg-gray-100" value="${fmt(totalActual)}" readonly>
        </td>
        <td class="px-4 py-2">
          <input data-k="accrued" class="border rounded px-2 py-1 w-24" value="${fmt(extra)}" title="เพิ่มสิทธิ์พิเศษ/เพิ่มตามอายุงาน">
        </td>
        <td class="px-4 py-2">${fmt(r.used)}</td>
        <td class="px-4 py-2">${fmt(r.available)}</td>
        <td class="px-4 py-2">
          <button class="bg-blue-600 text-white px-3 py-1 rounded" data-save="${r.id}">บันทึก</button>
        </td>
      `;

      // พิมพ์เพิ่ม/ลด → อัปเดต opening โชว์ (base + extraNow)
      const $acc = tr.querySelector('input[data-k="accrued"]');
      const $opn = tr.querySelector('input[data-k="opening"]');
      $acc.addEventListener('input', () => {
        const extraNow = Number($acc.value || 0);
        $opn.value = fmt(base + extraNow);
      });

      $body.appendChild(tr);
    }

    // apply filter หลังจากเติมครบ
    applyFilterToTable();

    // บันทึก (PATCH opening=base, accrued=extra)
    $body.querySelectorAll('[data-save]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id   = btn.dataset.save;
        const tr   = btn.closest('tr');
        const ltId = tr.dataset.ltId;
        const lt   = LT_BY_ID[ltId] || {};
        const base = Number(lt.annual_quota ?? 0);
        const extra = Number(
          tr.querySelector('input[data-k="accrued"]').value || 0
        );

        btn.disabled = true;
        try {
          const res = await fetch(`${API}/leave-balances/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              opening: base,   // เก็บฐานไว้ที่ opening
              accrued: extra   // ส่วนเพิ่ม/ลด
            })
          });
          if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
          $msg.textContent = `✔ Updated balance #${id}`;
          $msg.className = 'text-green-600';
          await loadBalances();
        } catch (e) {
          $msg.textContent = `✖ Update failed: ${e.message}`;
          $msg.className = 'text-red-600';
        } finally {
          btn.disabled = false;
        }
      });
    });
  }

  async function loadBalances() {
    const employee_id = $emp.value;
    const year = $year.value;
    $msg.textContent = 'กำลังโหลด...';
    try {
      const rows = await fetchJSON(
        `${API}/leave-balances/?employee_id=${employee_id}&year=${year}`
      );
      renderRows(rows);
      $msg.textContent = `พบ ${rows.length} รายการ`;
      $msg.className = '';
    } catch (e) {
      $body.innerHTML =
        `<tr><td colspan="7" class="text-center py-6 text-red-600">โหลดข้อมูลล้มเหลว</td></tr>`;
      $msg.textContent = e.message;
      $msg.className = 'text-red-600';
    }
  }

  // seed (สร้าง/รีเซ็ตปีนี้เป็น base quota)
  $seed.addEventListener('click', async () => {
    const y = parseInt($year.value, 10);
    if (!y) return;
    $msg.textContent = 'Seeding...';
    try {
      const r = await fetchJSON(
        `${API}/leave-balances/seed?year=${y}`,
        { method: 'POST' }
      );
      $msg.textContent = `Seeded year ${r.year}: created ${r.created}`;
      await loadBalances();
    } catch (e) {
      $msg.textContent = `Seed failed: ${e.message}`;
      $msg.className = 'text-red-600';
    }
  });

  $load.addEventListener('click', loadBalances);

  (async () => {
    await loadEmployees();
    await loadLeaveTypes(); // มี base quota ก่อน
    await loadBalances();
  })();
});
