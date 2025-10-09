// /static/js/meeting/dashboard.js
document.addEventListener('DOMContentLoaded', () => {
  // ---- DOM refs ----
  const monthPicker = document.getElementById('monthPicker');
  const dtFrom   = document.getElementById('dtFrom');
  const dtTo     = document.getElementById('dtTo');
  const btnLoad  = document.getElementById('btnLoad'); // มีหรือไม่มีก็ได้

  const kpiRooms    = document.getElementById('kpiRooms');
  const kpiBookings = document.getElementById('kpiBookings');
  const kpiHours    = document.getElementById('kpiHours');
  const kpiUtil     = document.getElementById('kpiUtil');

  const ctxStatus   = document.getElementById('chartStatus');
  const ctxTopRooms = document.getElementById('chartTopRooms');

  const heatTable   = document.getElementById('heatTable');
  const heatLegend  = document.getElementById('heatLegend');

  const dashTbody   = document.getElementById('dashBookings');
  const prevBtn     = document.getElementById('prevPage');
  const nextBtn     = document.getElementById('nextPage');
  const pageInfo    = document.getElementById('pageInfo');

  // ---- API base ----
  const API = {
    summary: (d1, d2) => `/api/v1/meeting/rooms/booking-summary?date_from=${d1}&date_to=${d2}`,
    bookings: `/api/v1/meeting/bookings/`,
  };

  // ---- State ----
  let allBookings = [];       // ทั้งหมด (ไม่กรอง) สำหรับตาราง + paginate
  let filtered = [];          // สำหรับกราฟ/heatmap (เฉพาะช่วงเดือนที่เลือก)
  let page = 1;
  const PAGE_SIZE = 10;

  // Auto refresh (5 นาที)
  const REFRESH_MS = 5 * 60 * 1000;
  let refreshHandle = null;
  let followCurrentMonth = true; // โหมด “ติดตามเดือนปัจจุบัน”

  // ---- Helpers ----
  const pad2 = (n) => String(n).padStart(2, '0');
  const toDateStr = (d) => `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`;
  const fmtDT = (iso) => {
    const d = new Date(iso);
    return `${d.toLocaleDateString()} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  };
  const statusOf = (b) => (typeof b.status === 'string' ? b.status : (b.status?.name || 'PENDING'));

  const getJSON = async (url) => {
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  };

  // ---- Month range helpers ----
  function getMonthRange(ymStr) {
    // ymStr = "YYYY-MM"
    const [y, m] = ymStr.split('-').map(Number);
    const first = new Date(y, m - 1, 1);
    const last  = new Date(y, m, 0); // day 0 ของเดือนถัดไป = วันสุดท้ายของเดือนนี้
    return { from: toDateStr(first), to: toDateStr(last) };
  }

  function setRangeFromMonth(ymStr) {
    const { from, to } = getMonthRange(ymStr);
    if (dtFrom) dtFrom.value = from;
    if (dtTo)   dtTo.value   = to;
  }

  function ensureMonthMatchesTodayIfFollowing() {
    if (!followCurrentMonth) return;
    const today = new Date();
    const ym = `${today.getFullYear()}-${pad2(today.getMonth()+1)}`;
    if (monthPicker && monthPicker.value !== ym) {
      monthPicker.value = ym;
      setRangeFromMonth(ym);
    }
  }

  // ---- Charts instances ----
  let chartStatus = null;
  let chartTopRooms = null;

  function buildStatusChart(rows) {
    const counts = { PENDING:0, APPROVED:0, REJECTED:0, CANCELLED:0 };
    rows.forEach(b => {
      const s = statusOf(b);
      if (counts[s] == null) counts[s] = 0;
      counts[s] += 1;
    });
    const labels = Object.keys(counts);
    const data   = labels.map(k => counts[k]);

    if (chartStatus) chartStatus.destroy();
    chartStatus = new Chart(ctxStatus, {
      type: 'pie',
      data: {
        labels,
        datasets: [{ data }]
      },
      options: {
        responsive: true,
        plugins: { legend: { position: 'bottom' } }
      }
    });
  }

  function buildTopRoomsChart(summary) {
    const items = (summary.top_rooms || []).slice(0, 10);
    const labels = items.map(x => x.room_name);
    const data   = items.map(x => x.hours);

    if (chartTopRooms) chartTopRooms.destroy();
    chartTopRooms = new Chart(ctxTopRooms, {
      type: 'bar',
      data: {
        labels,
        datasets: [{ label: 'ชั่วโมง', data }]
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true } },
        plugins: { legend: { display: false } }
      }
    });
  }

  // Heatmap: 7 วัน x 24 ชั่วโมง (นับการใช้งานในเดือนที่เลือก)
  function buildHeatmap(rows) {
    const matrix = Array.from({length:7}, () => Array(24).fill(0));
    rows.forEach(b => {
      const s = new Date(b.start_time);
      const e = new Date(b.end_time);
      const cur = new Date(s);
      cur.setMinutes(0,0,0);
      const last = new Date(e);
      last.setMinutes(0,0,0);
      while (cur <= last) {
        const weekday = cur.getDay();
        const hour = cur.getHours();
        matrix[weekday][hour] += 1;
        cur.setHours(cur.getHours() + 1);
      }
    });

    let maxVal = 0;
    for (let d=0; d<7; d++) for (let h=0; h<24; h++) maxVal = Math.max(maxVal, matrix[d][h]);
    heatLegend.textContent = maxVal ? `สีเข้ม = ใช้งานมาก (สูงสุด ~${maxVal}/ชม.)` : 'ยังไม่มีข้อมูลในช่วงเดือนที่เลือก';

    const dayNames = ['อา', 'จ', 'อ', 'พ', 'พฤ', 'ศ', 'ส'];
    let html = '<thead><tr><th class="sticky bg-white">วัน/ชม.</th>';
    for (let h=0; h<24; h++) html += `<th>${h}</th>`;
    html += '</tr></thead><tbody>';

    for (let d=0; d<7; d++) {
      html += `<tr><th class="sticky bg-white">${dayNames[d]}</th>`;
      for (let h=0; h<24; h++) {
        const v = matrix[d][h];
        const ratio = maxVal ? (v / maxVal) : 0;
        const bg = `rgba(59,130,246,${0.1 + ratio*0.6})`;
        html += `<td style="background:${bg}">${v ? v : ''}</td>`;
      }
      html += '</tr>';
    }
    html += '</tbody>';
    heatTable.innerHTML = html;
  }

  // ตารางรายการ (ทั้งหมด, ไม่กรอง) + paginate
  function renderPage() {
    const total = allBookings.length;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (page > totalPages) page = totalPages;
    if (page < 1) page = 1;
    const start = (page - 1) * PAGE_SIZE;
    const end   = Math.min(total, start + PAGE_SIZE);
    const rows  = allBookings.slice(start, end);

    dashTbody.innerHTML = rows.map(b => {
      const roomName = b.room?.name ?? `Room#${b.room_id}`;
      const img = b.room?.image_url
        ? `<img src="${b.room.image_url}" class="h-12 w-16 object-cover rounded border" />`
        : '-';

      const attendees = Array.isArray(b.attendees) ? b.attendees : [];
      const names = attendees
        .map(a => a.attendee_name || a.attendee_email)
        .filter(Boolean);
      let attendeeCell = '-';
      if (names.length) {
        const head = names.slice(0, 2).join(', ');
        const more = names.length > 2 ? ` และอีก ${names.length - 2}` : '';
        attendeeCell = `${head}${more}`;
      }

      const timeCell = `${fmtDT(b.start_time)} – ${fmtDT(b.end_time)}`;
      const statusText = statusOf(b);

      return `
        <tr>
          <td class="px-3 py-2 border">${b.id}</td>
          <td class="px-3 py-2 border">${img}</td>
          <td class="px-3 py-2 border">${roomName}</td>
          <td class="px-3 py-2 border">${b.contact_person || '-'}</td>
          <td class="px-3 py-2 border whitespace-nowrap">${timeCell}</td>
          <td class="px-3 py-2 border">${b.requester_email || '-'}</td>
          <td class="px-3 py-2 border">${b.subject || '-'}</td>
          <td class="px-3 py-2 border">${attendeeCell}</td>
          <td class="px-3 py-2 border font-semibold">${statusText}</td>
        </tr>
      `;
    }).join('');

    if (pageInfo) {
      const totalPages2 = Math.max(1, Math.ceil(allBookings.length / PAGE_SIZE));
      pageInfo.textContent = `หน้า ${page}/${totalPages2}`;
    }
    if (prevBtn) prevBtn.disabled = (page <= 1);
    if (nextBtn) nextBtn.disabled = (page >= Math.max(1, Math.ceil(allBookings.length / PAGE_SIZE)));
  }

  prevBtn?.addEventListener('click', () => { page -= 1; renderPage(); });
  nextBtn?.addEventListener('click', () => { page += 1; renderPage(); });

  // ---- Load summary + bookings (ตามเดือนใน dtFrom/dtTo) ----
  async function loadAll() {
    try {
      ensureMonthMatchesTodayIfFollowing();

      const from = dtFrom.value;
      const to   = dtTo.value;

      // KPI + TopRooms (เฉพาะเดือนที่เลือก)
      const summary = await getJSON(API.summary(from, to));
      if (kpiRooms)    kpiRooms.textContent    = summary.total_rooms ?? '-';
      if (kpiBookings) kpiBookings.textContent = summary.total_bookings ?? '-';
      if (kpiHours)    kpiHours.textContent    = (summary.total_hours ?? 0).toFixed(1);
      if (kpiUtil)     kpiUtil.textContent     = (summary.utilization_pct ?? 0).toFixed(1);

      buildTopRoomsChart(summary);

      // Bookings ทั้งหมด (ใช้ในตารางและคัดกรองสำหรับกราฟ/heatmap)
      const bookings = await getJSON(API.bookings);

      // ตาราง: เรียงล่าสุดก่อน + แบ่งหน้า
      allBookings = (bookings || []).slice().sort((a, b) => {
        return new Date(b.start_time) - new Date(a.start_time);
      });
      page = 1;
      renderPage();

      // กรองเฉพาะเดือนที่เลือกสำหรับกราฟ/heatmap
      const fromDT = new Date(from + 'T00:00:00');
      const toDT   = new Date(to   + 'T23:59:59');
      filtered = allBookings.filter(b => {
        const s = new Date(b.start_time);
        const e = new Date(b.end_time);
        return e >= fromDT && s <= toDT;
      });

      buildStatusChart(filtered);
      buildHeatmap(filtered);
    } catch (err) {
      console.error('loadAll error:', err);
      // ไม่ throw — หน้าจอมอนิเตอร์จะพยายามรอบต่อไปเอง
    }
  }

  function scheduleRefresh() {
    if (refreshHandle) clearInterval(refreshHandle);
    refreshHandle = setInterval(() => {
      loadAll();
    }, REFRESH_MS);
  }

  // ใช้ Page Visibility API: พักรีเฟรชตอนแท็บไม่โฟกัส
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      if (refreshHandle) {
        clearInterval(refreshHandle);
        refreshHandle = null;
      }
    } else {
      // กลับมาเห็นหน้า → โหลดทันที แล้วเริ่มนับรอบใหม่
      loadAll().finally(scheduleRefresh);
    }
  });

  window.addEventListener('beforeunload', () => {
    if (refreshHandle) clearInterval(refreshHandle);
  });

  // ---- Auto month init & events ----
  (function initMonth() {
    // ตั้งเดือนปัจจุบัน
    const today = new Date();
    const ym = `${today.getFullYear()}-${pad2(today.getMonth()+1)}`;
    if (monthPicker) monthPicker.value = ym;
    else {
      // ไม่มี monthPicker ใน DOM ก็ยังทำงาน: คิดช่วงเดือนปัจจุบันแล้วเซ็ตให้
      const { from, to } = getMonthRange(ym);
      if (dtFrom) dtFrom.value = from;
      if (dtTo)   dtTo.value   = to;
    }

    // เซ็ตช่วงวันตามเดือน แล้วโหลดข้อมูลอัตโนมัติ
    if (monthPicker) setRangeFromMonth(monthPicker.value);
    loadAll().finally(scheduleRefresh);

    // เปลี่ยนเดือนด้วยมือ → จะเลิก “ตามเดือนปัจจุบัน” และโหลดใหม่
    monthPicker?.addEventListener('input', () => {
      followCurrentMonth = false;
      setRangeFromMonth(monthPicker.value);
      loadAll();
    });

    // ปุ่มโหลด (ถ้ามี) ยังใช้งานได้
    btnLoad?.addEventListener('click', () => loadAll());
  })();
});
