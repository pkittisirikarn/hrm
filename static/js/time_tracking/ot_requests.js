// ===== API endpoints / constants =====
const API = {
  EMPLOYEES: "/api/v1/data-management/employees/",
  OT_TYPES:  "/api/v1/time-tracking/ot-types/",
  OT_REQS:   "/api/v1/time-tracking/ot-requests/",
};
const STATUS = {
  pending:   "Pending",
  approved:  "Approved",
  rejected:  "Rejected",
  cancelled: "Cancelled",
};

// ===== helpers =====
const $ = (s) => document.querySelector(s);

function msgBox() {
  const el = $("#otRequestMsg");
  if (el) return el;
  const div = document.createElement("div");
  div.id = "otRequestMsg";
  div.style.marginLeft = "8px";
  div.style.pointerEvents = "none";
  $("#create-ot-request-form")?.appendChild(div);
  return div;
}
function showError(m) {
  const box = msgBox();
  box.style.color = "#d33";
  box.textContent = typeof m === "string" ? m : JSON.stringify(m);
  console.error("OT Request error:", m);
}
function showSuccess(m) {
  const box = msgBox();
  box.style.color = "#0a0";
  box.textContent = m;
  setTimeout(() => { if (box.textContent === m) box.textContent = ""; }, 2000);
}
function parseFastAPIError(data) {
  try {
    if (!data) return "ไม่ทราบสาเหตุ";
    if (Array.isArray(data.detail)) return data.detail.map(d => d.msg || JSON.stringify(d)).join(" | ");
    if (typeof data.detail === "string") return data.detail;
    if (data.detail?.msg) return data.detail.msg;
    if (data.message) return data.message;
    return JSON.stringify(data);
  } catch {
    return "ไม่ทราบสาเหตุ";
  }
}
function ensureClickable(el) {
  if (!el) return;
  el.style.pointerEvents = "auto";
  el.disabled = false;
}

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`โหลดข้อมูลไม่สำเร็จ: ${url}`);
  return r.json();
}
async function postJSON(url, payload) {
  const r = await fetch(url, {
    method: "POST",
    headers: {"Accept":"application/json","Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  if (!r.ok) {
    let msg = "บันทึกไม่สำเร็จ";
    try { msg = parseFastAPIError(await r.json()); } catch {}
    throw new Error(msg);
  }
  return r.json();
}
async function putJSON(url, payload) {
  const r = await fetch(url, {
    method: "PUT",
    headers: {"Accept":"application/json","Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  if (!r.ok) {
    let msg = "อัปเดตไม่สำเร็จ";
    try { msg = parseFastAPIError(await r.json()); } catch {}
    throw new Error(msg);
  }
  return r.json();
}
async function del(url) {
  const r = await fetch(url, { method: "DELETE" });
  if (!r.ok) {
    let msg = "ลบไม่สำเร็จ";
    try { msg = parseFastAPIError(await r.json()); } catch {}
    throw new Error(msg);
  }
}

function toISOSeconds(v) {
  if (!v) return "";
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(v)) {
    return v.length === 16 ? `${v}:00` : v;
  }
  const m = v.match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})$/);
  if (m) {
    const [_, dd, MM, yyyy, hh, mm] = m;
    return `${yyyy}-${MM}-${dd}T${hh}:${mm}:00`;
  }
  const d = new Date(v);
  if (!isNaN(d.getTime())) {
    const pad = (n)=> String(n).padStart(2,"0");
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
  return v;
}

// ===== elements / state =====
const els = {
  empSel:   () => $("#employeeSelect"),
  typeSel:  () => $("#otTypeSelect"),
  startInp: () => $("#startTime"),
  endInp:   () => $("#endTime"),
  reason:   () => $("#reason"),
  table:    () => $("#otRequestsTableBody"),
  btnCreate:() => $("#btnCreateOTRequest"),
  form:     () => $("#create-ot-request-form"),
  modeLabel:() => $("#formModeLabel"),
  editBadge:() => $("#editingBadge"),
  editBtns: () => $("#editButtons"),
  btnSaveEdit: () => $("#btnSaveEdit"),
  btnCancelEdit: () => $("#btnCancelEdit"),
  editingId: () => $("#editingId"),
};

const STATUS_LABEL = {
  Pending:   { text: "รอดำเนินการ", cls: "bg-yellow-100 text-yellow-800" },
  Approved:  { text: "อนุมัติ",      cls: "bg-green-100 text-green-800" },
  Rejected:  { text: "ปฏิเสธ",       cls: "bg-red-100 text-red-800" },
  Cancelled: { text: "ยกเลิก",       cls: "bg-gray-100 text-gray-800" },
};

// ===== data loaders =====
async function loadEmployees() {
  const sel = els.empSel(); if (!sel) return;
  ensureClickable(sel);
  sel.innerHTML = `<option value="">กำลังโหลด...</option>`;
  const data = await getJSON(API.EMPLOYEES);
  sel.innerHTML = data.map(e => `<option value="${e.id}">${e.first_name} ${e.last_name}</option>`).join("");
}
async function loadOTTypes() {
  const sel = els.typeSel(); if (!sel) return;
  ensureClickable(sel);
  sel.innerHTML = `<option value="">กำลังโหลด...</option>`;
  const data = await getJSON(API.OT_TYPES);
  sel.innerHTML = data.map(t => `<option value="${t.id}">${t.name} (${t.rate_multiplier}x)</option>`).join("");
}
async function refreshTable() {
  const data = await getJSON(API.OT_REQS);
  renderTable(data);
}

// ===== render =====
function badge(status) {
  const s = STATUS_LABEL[status] || {text: status, cls: "bg-gray-100 text-gray-800"};
  return `<span class="px-2 py-1 rounded text-xs ${s.cls}">${s.text}</span>`;
}
function renderTable(items) {
  const tbody = els.table(); if (!tbody) return;
  tbody.innerHTML = (items||[]).map(r => `
    <tr>
      <td class="border px-3 py-2">${r.id}</td>
      <td class="border px-3 py-2">${r.employee?.first_name ?? ""} ${r.employee?.last_name ?? ""}</td>
      <td class="border px-3 py-2">${r.ot_type?.name ?? "-"}</td>
      <td class="border px-3 py-2">${new Date(r.start_time).toLocaleString()}</td>
      <td class="border px-3 py-2">${new Date(r.end_time).toLocaleString()}</td>
      <td class="border px-3 py-2">${badge(r.status)}</td>
      <td class="border px-3 py-2 space-x-2">
        <a href="/time-tracking/ot-requests/${r.id}/edit" class="px-2 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-700">แก้ไข</a>
        <button class="px-2 py-1 rounded bg-green-600 text-white hover:bg-green-700" data-approve="${r.id}">อนุมัติ</button>
        <button class="px-2 py-1 rounded bg-amber-600 text-white hover:bg-amber-700" data-pending="${r.id}">รอ</button>
        <button class="px-2 py-1 rounded bg-red-600 text-white hover:bg-red-700" data-reject="${r.id}">ปฏิเสธ</button>
        <button class="px-2 py-1 rounded bg-gray-200 hover:bg-gray-300" data-del="${r.id}">ลบ</button>
      </td>
    </tr>
  `).join("");
}

// ===== collect/clear form =====
function collectPayload() {
  const employee_id = parseInt(els.empSel()?.value || "", 10);
  const ot_type_id  = parseInt(els.typeSel()?.value || "", 10);
  const start_time  = toISOSeconds(els.startInp()?.value || "");
  const end_time    = toISOSeconds(els.endInp()?.value || "");
  const reason      = els.reason()?.value || null;

  if (!employee_id) throw new Error("กรุณาเลือกพนักงาน");
  if (!ot_type_id)  throw new Error("กรุณาเลือกประเภท OT");
  if (!start_time)  throw new Error("กรุณาระบุเวลาเริ่มต้น");
  if (!end_time)    throw new Error("กรุณาระบุเวลาสิ้นสุด");

  // ไม่ส่ง status ตอนสร้าง/แก้ไข (ให้ backend ดูแล)
  return { employee_id, ot_type_id, start_time, end_time, reason };
}
function fillFormFromRow(row) {
  if (els.empSel())   els.empSel().value = String(row.employee_id);
  if (els.typeSel())  els.typeSel().value = String(row.ot_type_id);
  if (els.startInp()) els.startInp().value = row.start_time.slice(0,19);
  if (els.endInp())   els.endInp().value = row.end_time.slice(0,19);
  if (els.reason())   els.reason().value = row.reason || "";
}
function clearForm() {
  els.editingId().value = "";
  if (els.empSel())   els.empSel().value = "";
  if (els.typeSel())  els.typeSel().value = "";
  if (els.startInp()) els.startInp().value = "";
  if (els.endInp())   els.endInp().value = "";
  if (els.reason())   els.reason().value = "";
}

// ===== mode toggle =====
function enterEditMode(id) {
  els.editingId().value = String(id);
  els.modeLabel().textContent = "แก้ไขคำขอ OT";
  els.editBadge().classList.remove("hidden");
  els.editBtns().classList.remove("hidden");
  els.btnCreate().classList.add("hidden");
}
function exitEditMode() {
  clearForm();
  els.modeLabel().textContent = "ยื่นคำขอ OT ใหม่";
  els.editBadge().classList.add("hidden");
  els.editBtns().classList.add("hidden");
  els.btnCreate().classList.remove("hidden");
}

// ===== handlers =====
async function handleCreate() {
  try {
    const payload = collectPayload();
    await postJSON(API.OT_REQS, payload);
    showSuccess("บันทึกคำขอ OT สำเร็จ");
    clearForm();
    await refreshTable();
  } catch (e) {
    showError(e.message || String(e));
  }
}
async function handleSaveEdit() {
  const id = els.editingId().value;
  if (!id) return;
  try {
    const payload = collectPayload();
    await putJSON(`${API.OT_REQS}${id}`, payload);
    showSuccess("บันทึกการแก้ไขสำเร็จ");
    exitEditMode();
    await refreshTable();
  } catch (e) {
    showError(e.message || String(e));
  }
}
function handleCancelEdit() { exitEditMode(); }

// อัปเดตสถานะ (ใช้ Title-case ให้ตรงกับ API)
async function updateStatus(id, newStatus) {
  try {
    await putJSON(`${API.OT_REQS}${id}`, { status: newStatus });
    showSuccess("อัปเดตสถานะสำเร็จ");
    await refreshTable();
  } catch (e) {
    showError(e.message || String(e));
  }
}

// event delegation ของปุ่มในตาราง
document.addEventListener("click", async (ev) => {
  const t = ev.target;
  if (!(t instanceof Element)) return;

  // แก้ไขแบบ in-form
  const editId = t.getAttribute("data-edit");
  if (editId) {
    try {
      const row = await getJSON(`${API.OT_REQS}${editId}`);
      row.employee_id = row.employee?.id ?? row.employee_id;
      row.ot_type_id  = row.ot_type?.id ?? row.ot_type_id;
      fillFormFromRow(row);
      enterEditMode(editId);
    } catch (e) { showError(e.message || String(e)); }
    return;
  }

  // ลบ
  const delId = t.getAttribute("data-del");
  if (delId) {
    if (!confirm("ยืนยันการลบคำขอ OT นี้?")) return;
    del(`${API.OT_REQS}${delId}`)
      .then(() => { showSuccess("ลบเรียบร้อย"); refreshTable(); })
      .catch((e) => showError(e.message || String(e)));
    return;
  }

  // สถานะ
  const approveId = t.getAttribute("data-approve");
  if (approveId) { updateStatus(approveId, STATUS.approved); return; }

  const rejectId = t.getAttribute("data-reject");
  if (rejectId) { updateStatus(rejectId, STATUS.rejected); return; }

  const pendingId = t.getAttribute("data-pending");
  if (pendingId) { updateStatus(pendingId, STATUS.pending); return; }
});

// ===== init =====
document.addEventListener("DOMContentLoaded", async () => {
  ensureClickable(els.empSel());
  ensureClickable(els.typeSel());

  els.btnCreate()?.addEventListener("click", handleCreate);
  els.btnSaveEdit()?.addEventListener("click", handleSaveEdit);
  els.btnCancelEdit()?.addEventListener("click", handleCancelEdit);
  els.form()?.addEventListener("submit", (e)=> e.preventDefault());

  try {
    await Promise.all([loadEmployees(), loadOTTypes()]);
    await refreshTable();
  } catch (e) {
    showError(e.message || String(e));
  }
});
