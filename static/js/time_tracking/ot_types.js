// static/js/time_tracking/ot_types.js  (robust selectors + safe version)

const API_BASE = "/api/v1/time-tracking/ot-types";

// ---------- helpers ----------
function $(sel) { return document.querySelector(sel); }
function pick(selList) {
  const sels = selList.split(",").map(s => s.trim());
  for (const s of sels) { const el = $(s); if (el) return el; }
  return null;
}
function ensureErrorBox() {
  let box = $("#otTypeError");
  if (!box) {
    box = document.createElement("div");
    box.id = "otTypeError";
    box.style.marginTop = "8px";
    const host = document.getElementById("create-ot-type-form") || $("form") || document.body;
    host.appendChild(box);
  }
  return box;
}
function showError(msg) {
  const box = ensureErrorBox();
  box.style.color = "#d33";
  box.textContent = typeof msg === "string" ? msg : JSON.stringify(msg);
  console.error(msg);
}
function showSuccess(msg) {
  const box = ensureErrorBox();
  box.style.color = "#0a0";
  box.textContent = msg;
  setTimeout(() => { if (box.textContent === msg) box.textContent = ""; }, 2000);
}
function extractErrorMessage(data) {
  try {
    if (!data) return "ไม่ทราบสาเหตุ";
    if (Array.isArray(data.detail)) return data.detail.map(d => d.msg || JSON.stringify(d)).join("\n");
    if (typeof data.detail === "string") return data.detail;
    if (data.detail && data.detail.msg) return data.detail.msg;
    return JSON.stringify(data);
  } catch { return "ไม่ทราบสาเหตุ"; }
}

// ----- find inputs robustly -----
function findNameInput() {
  const candidates = [
    "#otTypeName", "#ot-type-name", "#ot_type_name", "#name",
    "input[name='ot_type_name']", "input[name='otTypeName']", "input[name='name']",
    "input[data-field='name']"
  ];
  for (const c of candidates) { const el = $(c); if (el) return el; }

  const form = document.getElementById("create-ot-type-form") || $("form");
  if (form) {
    const inputs = form.querySelectorAll("input[type='text']");
    for (const i of inputs) {
      const n = (i.name || "").toLowerCase();
      const id = (i.id || "").toLowerCase();
      if (!n.includes("rate") && !id.includes("rate")) return i;
    }
  }
  return null;
}
function findRateInput() {
  const candidates = [
    "#otRateMultiplier", "#rateMultiplier", "#rate_multiplier",
    "input[name='rate_multiplier']", "input[data-field='rate_multiplier']"
  ];
  for (const c of candidates) { const el = $(c); if (el) return el; }

  const form = document.getElementById("create-ot-type-form") || $("form");
  if (form) {
    const nums = form.querySelectorAll("input[type='number'], input[type='text']");
    for (const i of nums) {
      const n = (i.name || "").toLowerCase();
      const id = (i.id || "").toLowerCase();
      if (n.includes("rate") || id.includes("rate")) return i;
    }
  }
  return null;
}
function findDescInput() {
  return pick("#otTypeDescription, #ot-type-description, #description, textarea[name='description']");
}
function findActiveInput() {
  return pick("#otTypeActive, #ot-type-active, #is_active, input[name='is_active']");
}

// ---------- API ----------
async function apiList() {
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) throw new Error("โหลดรายการประเภท OT ไม่ได้");
  return res.json();
}
async function apiCreate(payload) {
  const res = await fetch(`${API_BASE}/`, {
    method: "POST",
    headers: { "Accept": "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    let msg = "ไม่สามารถสร้างประเภท OT ได้";
    try { msg = extractErrorMessage(await res.json()); } catch {}
    throw new Error(msg);
  }
  return res.json();
}
async function apiDelete(id) {
  const res = await fetch(`${API_BASE}/${id}`, { method: "DELETE" });
  if (!res.ok) {
    let msg = "ลบไม่สำเร็จ";
    try { msg = extractErrorMessage(await res.json()); } catch {}
    throw new Error(msg);
  }
}

// ---------- UI ----------
function getFormValues() {
  const nameEl = findNameInput();
  const rateEl = findRateInput();
  const descEl = findDescInput();
  const activeEl = findActiveInput();

  const name = nameEl ? String(nameEl.value || "").trim() : "";
  const rateRaw = rateEl ? String(rateEl.value || "").trim() : "";
  const description = descEl ? (String(descEl.value || "").trim() || null) : null;
  const is_active = activeEl ? !!activeEl.checked : true;

  const rate = parseFloat((rateRaw || "").replace(",", "."));
  if (!name) throw new Error("กรุณากรอกชื่อประเภท OT");
  if (!isFinite(rate) || rate <= 0) throw new Error("กรุณากรอกอัตราเป็นตัวเลขมากกว่า 0 เช่น 1.5");

  return { name, description, rate_multiplier: rate, is_active };
}

function renderRows(items) {
  let tbody = $("#otTypesTableBody") || $("table tbody");
  if (!tbody) {
    const table = document.createElement("table");
    table.className = "table-auto w-full";
    table.innerHTML = `
      <thead><tr>
        <th>ID</th><th>ชื่อ</th><th>คำอธิบาย</th><th>ตัวคูณ</th><th>สถานะ</th><th>การดำเนินการ</th>
      </tr></thead><tbody></tbody>`;
    document.body.appendChild(table);
    tbody = table.querySelector("tbody");
  }
  tbody.innerHTML = (items || []).map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${r.name}</td>
      <td>${r.description || "-"}</td>
      <td>${r.rate_multiplier}</td>
      <td>${r.is_active ? "ใช้งาน" : "ไม่ใช้งาน"}</td>
      <td><button type="button" class="btn btn-sm btn-danger" data-del="${r.id}">ลบ</button></td>
    </tr>
  `).join("");
}

async function refreshTable() {
  try { renderRows(await apiList()); }
  catch (e) { showError(e.message || String(e)); }
}

async function handleCreate(ev) {
  if (ev && ev.preventDefault) ev.preventDefault();
  try {
    const payload = getFormValues();
    await apiCreate(payload);
    showSuccess("เพิ่มประเภท OT สำเร็จ");
    await refreshTable();

    const n = findNameInput(); if (n) n.value = "";
    const r = findRateInput(); if (r) r.value = "";
    const d = findDescInput(); if (d) d.value = "";
    const a = findActiveInput(); if (a) a.checked = true;
  } catch (err) { showError(err.message || String(err)); }
}

document.addEventListener("DOMContentLoaded", function () {
  const btn = $("#btnCreateOTType, #btnAddOTType, #add-ot-type-btn, [data-action='create-ot-type']");
  if (btn) btn.addEventListener("click", handleCreate);

  const form = document.getElementById("create-ot-type-form") || $("form");
  if (form) form.addEventListener("submit", handleCreate);

  document.body.addEventListener("click", function (ev) {
    const t = ev.target;
    if (!t || !t.getAttribute) return;
    const id = t.getAttribute("data-del");
    if (!id) return;
    if (!confirm("ยืนยันการลบประเภท OT นี้?")) return;
    apiDelete(id).then(() => { showSuccess("ลบเรียบร้อย"); refreshTable(); })
                 .catch(err => showError(err.message || String(err)));
  });

  refreshTable();
});
