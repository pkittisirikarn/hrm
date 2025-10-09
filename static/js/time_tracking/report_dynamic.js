document.addEventListener('DOMContentLoaded', () => {
  const API = '/api/v1/time-tracking';

  const $emp   = document.getElementById('repEmpId');
  const $from  = document.getElementById('repFrom');
  const $to    = document.getElementById('repTo');
  const $btn   = document.getElementById('btnLoad');
  const $exp   = document.getElementById('btnExport');
  const $thead = document.getElementById('repThead');
  const $tbody = document.getElementById('repTbody');
  const $msg   = document.getElementById('repMsg');

  // เก็บ “รายการคอลัมน์ไดนามิก”
  let LEAVE_TYPES = []; // [{id, name, ...}]
  let OT_TYPES    = []; // [{id, name, ...}]
  let LAST_ROWS   = []; // แคชข้อมูลตารางล่าสุด (ไว้ export)

  const fmtNum = (n, d=2) => (n === null || n === undefined) ? '' : Number(n).toFixed(d);
  const safe   = (v) => v == null ? '' : v;

  async function fetchJSON(url, opts){
    const res = await fetch(url, opts);
    if(!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
  }

  async function loadMeta(){
    // ดึง leave-types ทั้งหมด (ต้องการแสดงทั้งแบบหัก/ไม่หักยอด)
    LEAVE_TYPES = await fetchJSON(`${API}/leave-types/`);
    // ดึง ot-types ทั้งหมด (คอลัมน์ชั่วโมง OT)
    OT_TYPES = await fetchJSON(`${API}/ot-types/`);
  }

  function buildHeader(){
    // คอลัมน์หลัก
    const fixedCols = [
      { key:'employee_id',        label:'ID (emp)' },
      { key:'employee_id_number', label:'รหัสพนักงาน' },
      { key:'full_name',          label:'ชื่อ-นามสกุล' },
      { key:'date',               label:'วันที่' },
      { key:'check_in_time',      label:'เวลาเข้างาน' },
      { key:'check_out_time',     label:'เวลาออกงาน' },
      { key:'late_minutes',       label:'สาย(นาที)' },
      { key:'early_leave_minutes',label:'ออกก่อน(นาที)' },
    ];

    // คอลัมน์ลา (ชื่อจาก leave types)
    const leaveCols = LEAVE_TYPES.map(t => ({ key:`lv:${t.name}`, label:t.name })); // แสดงเป็น "วัน" (0, 0.5, 1)
    // คอลัมน์ OT (ชั่วโมง)
    const otCols = OT_TYPES.map(t => ({ key:`ot:${t.name}`, label:`OT-${t.name} (ชม.)` }));

    // รวม header
    const all = [...fixedCols, ...leaveCols, ...otCols];

    const tr = document.createElement('tr');
    all.forEach(col => {
      const th = document.createElement('th');
      th.className = 'px-4 py-2 text-left text-xs font-medium text-gray-700 uppercase tracking-wider';
      th.textContent = col.label;
      tr.appendChild(th);
    });
    $thead.innerHTML = '';
    $thead.appendChild(tr);

    return { fixedCols, leaveCols, otCols, all };
  }

  function renderRows(rows){
    $tbody.innerHTML = '';
    if(!rows || rows.length === 0){
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="px-4 py-4 text-center text-gray-500" colspan="${$thead.querySelectorAll('th').length}">ไม่พบข้อมูล</td>`;
      $tbody.appendChild(tr);
      return;
    }

    rows.forEach(r => {
      const tr = document.createElement('tr');

      // คอลัมน์หลัก
      const fixedCells = [
        r.employee_id,
        safe(r.employee_id_number),
        safe(r.full_name),
        safe(r.date),
        r.check_in_time ? new Date(r.check_in_time).toLocaleString('th-TH') : '',
        r.check_out_time ? new Date(r.check_out_time).toLocaleString('th-TH') : '',
        r.late_minutes || 0,
        r.early_leave_minutes || 0,
      ];
      fixedCells.forEach(v => {
        const td = document.createElement('td');
        td.className = 'px-4 py-2 text-sm text-gray-800 whitespace-nowrap';
        td.textContent = v;
        tr.appendChild(td);
      });

      // คอลัมน์ลาตามชนิด (หน่วยเป็น “วัน”)
      LEAVE_TYPES.forEach(t => {
        const td = document.createElement('td');
        td.className = 'px-4 py-2 text-sm text-gray-800 text-center';
        const used = (r.leaves && r.leaves[t.name]) ? r.leaves[t.name] : 0;
        td.textContent = used ? fmtNum(used, 2) : '';
        tr.appendChild(td);
      });

      // คอลัมน์ OT ตามชนิด (หน่วยเป็น “ชั่วโมง”)
      OT_TYPES.forEach(t => {
        const td = document.createElement('td');
        td.className = 'px-4 py-2 text-sm text-gray-800 text-center';
        const hrs = (r.ot_hours && r.ot_hours[t.name]) ? r.ot_hours[t.name] : 0;
        td.textContent = hrs ? fmtNum(hrs, 2) : '';
        tr.appendChild(td);
      });

      $tbody.appendChild(tr);
    });
  }

  async function loadReport(){
    const emp = ($emp.value || '').trim();
    const df  = $from.value;
    const dt  = $to.value;

    if(!df || !dt){
      $msg.textContent = 'กรุณาเลือกช่วงวันที่';
      $msg.className = 'text-red-600';
      return;
    }
    $msg.textContent = 'กำลังโหลด...';
    $msg.className = 'text-gray-600';

    try {
      // ให้ services.build_daily_report ทำงาน (รวมลา & OT)
      const url = new URL(`${API}/report/data`, window.location.origin);
      url.searchParams.set('date_from', df);
      url.searchParams.set('date_to', dt);
      url.searchParams.set('include_leaves', 'true');
      url.searchParams.set('include_ot', 'true');
      if(emp) url.searchParams.set('employee_id_number', emp);

      const rows = await fetchJSON(url.toString());
      LAST_ROWS = rows.slice(); // เก็บไว้ export
      buildHeader();
      renderRows(rows);

      $msg.textContent = `แสดงผล ${rows.length} แถว`;
      $msg.className = 'text-gray-600';
    } catch (e){
      $thead.innerHTML = '';
      $tbody.innerHTML = '';
      $msg.textContent = `โหลดข้อมูลล้มเหลว: ${e.message}`;
      $msg.className = 'text-red-600';
    }
  }

  function exportCSV(){
    if(!LAST_ROWS.length){
      $msg.textContent = 'ยังไม่มีข้อมูลสำหรับส่งออก';
      $msg.className = 'text-red-600';
      return;
    }
    // สร้าง header อีกครั้งเพื่อเรียงคอลัมน์
    const { all } = buildHeader();

    // map keys สำหรับ fixed + leave + ot
    const keyMap = [
      'employee_id','employee_id_number','full_name','date','check_in_time','check_out_time','late_minutes','early_leave_minutes',
      ...LEAVE_TYPES.map(t => `lv:${t.name}`),
      ...OT_TYPES.map(t => `ot:${t.name}`),
    ];

    const header = all.map(c => c.label);
    const rows = LAST_ROWS.map(r => {
      const base = {
        'employee_id': r.employee_id,
        'employee_id_number': safe(r.employee_id_number),
        'full_name': safe(r.full_name),
        'date': safe(r.date),
        'check_in_time': r.check_in_time || '',
        'check_out_time': r.check_out_time || '',
        'late_minutes': r.late_minutes || 0,
        'early_leave_minutes': r.early_leave_minutes || 0,
      };
      // leaves
      LEAVE_TYPES.forEach(t => {
        base[`lv:${t.name}`] = (r.leaves && r.leaves[t.name]) ? r.leaves[t.name] : '';
      });
      // ot
      OT_TYPES.forEach(t => {
        base[`ot:${t.name}`] = (r.ot_hours && r.ot_hours[t.name]) ? r.ot_hours[t.name] : '';
      });
      return keyMap.map(k => base[k]);
    });

    const csv = [header, ...rows].map(r => r.map(v => {
      const s = (v === null || v === undefined) ? '' : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g,'""')}"` : s;
    }).join(',')).join('\n');

    const blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const stamp = new Date().toISOString().slice(0,19).replace(/[:T]/g,'-');
    a.href = url;
    a.download = `time_report_${stamp}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // init
  (async () => {
    // default วันที่วันนี้
    const today = new Date();
    const y = today.getFullYear();
    const m = String(today.getMonth()+1).padStart(2,'0');
    const d = String(today.getDate()).padStart(2,'0');
    $from.value = `${y}-${m}-${d}`;
    $to.value   = `${y}-${m}-${d}`;

    await loadMeta();     // โหลดประเภทลา/OT
    buildHeader();        // สร้างหัวตารางตาม meta
    await loadReport();   // โหลดข้อมูลครั้งแรก
  })();

  $btn.addEventListener('click', loadReport);
  $exp.addEventListener('click', exportCSV);
});
