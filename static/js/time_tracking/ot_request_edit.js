const API = {
  EMPLOYEES: "/api/v1/data-management/employees/",
  OT_TYPES:  "/api/v1/time-tracking/ot-types/",
  OT_REQS:   "/api/v1/time-tracking/ot-requests/",
};

const $ = (s) => document.querySelector(s);

function pad(n){return String(n).padStart(2,"0");}
function toISOSeconds(v){
  if (!v) return "";
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?$/.test(v)) return v.length===16?`${v}:00`:v;
  const d = new Date(v);
  if (!isNaN(d.getTime())) {
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }
  return v;
}
function showMsg(m, ok=false){
  const el = $("#msg"); if (!el) return;
  el.style.color = ok ? "#0a0" : "#d33";
  el.textContent = m;
  if (ok) setTimeout(()=>{ if (el.textContent===m) el.textContent=""; }, 2000);
}
async function getJSON(url){ const r = await fetch(url); if(!r.ok) throw new Error("โหลดข้อมูลไม่สำเร็จ"); return r.json(); }
async function putJSON(url,payload){
  const r = await fetch(url,{method:"PUT",headers:{"Accept":"application/json","Content-Type":"application/json"},body:JSON.stringify(payload)});
  if(!r.ok){ let t="อัปเดตไม่สำเร็จ"; try{ const j=await r.json(); t=(j.detail?.msg||j.detail||j.message||t);}catch{} throw new Error(t); }
  return r.json();
}

function getIdFromURL(){
  // /time-tracking/ot-requests/{id}/edit
  const parts = location.pathname.split("/").filter(Boolean);
  const idx = parts.findIndex(p => p==="ot-requests");
  if (idx>=0 && parts[idx+1]) return parts[idx+1];
  return null;
}

async function loadEmployees(){
  const sel = $("#employeeSelect");
  sel.innerHTML = `<option value="">กำลังโหลด...</option>`;
  const data = await getJSON(API.EMPLOYEES);
  sel.innerHTML = data.map(e=>`<option value="${e.id}">${e.first_name} ${e.last_name}</option>`).join("");
}
async function loadOTTypes(){
  const sel = $("#otTypeSelect");
  sel.innerHTML = `<option value="">กำลังโหลด...</option>`;
  const data = await getJSON(API.OT_TYPES);
  sel.innerHTML = data.map(t=>`<option value="${t.id}">${t.name} (${t.rate_multiplier}x)</option>`).join("");
}

function fillForm(row){
  $("#recordId").value = row.id;
  $("#employeeSelect").value = row.employee?.id ?? row.employee_id;
  $("#otTypeSelect").value  = row.ot_type?.id ?? row.ot_type_id;
  $("#startTime").value = row.start_time.slice(0,19);
  $("#endTime").value   = row.end_time.slice(0,19);
  $("#reason").value    = row.reason || "";
}

function collect(){
  const employee_id = parseInt($("#employeeSelect").value || "",10);
  const ot_type_id  = parseInt($("#otTypeSelect").value || "",10);
  const start_time  = toISOSeconds($("#startTime").value || "");
  const end_time    = toISOSeconds($("#endTime").value || "");
  const reason      = $("#reason").value || null;
  if(!employee_id) throw new Error("กรุณาเลือกพนักงาน");
  if(!ot_type_id)  throw new Error("กรุณาเลือกประเภท OT");
  if(!start_time)  throw new Error("กรุณาระบุเวลาเริ่มต้น");
  if(!end_time)    throw new Error("กรุณาระบุเวลาสิ้นสุด");
  return { employee_id, ot_type_id, start_time, end_time, reason };
}

document.addEventListener("DOMContentLoaded", async ()=>{
  const id = getIdFromURL();
  if(!id){ showMsg("ไม่พบรหัสคำขอ", false); return; }

  try{
    await Promise.all([loadEmployees(), loadOTTypes()]);
    const row = await getJSON(`${API.OT_REQS}${id}`);
    fillForm(row);
  }catch(e){
    showMsg(e.message || String(e), false);
  }

  $("#btnSave").addEventListener("click", async ()=>{
    try{
      const payload = collect();
      await putJSON(`${API.OT_REQS}${id}`, payload);
      showMsg("บันทึกสำเร็จ", true);
      setTimeout(()=>{ location.href="/time-tracking/ot-requests"; }, 600);
    }catch(e){
      showMsg(e.message || String(e), false);
    }
  });

  $("#edit-form")?.addEventListener("submit", (e)=> e.preventDefault());
});
