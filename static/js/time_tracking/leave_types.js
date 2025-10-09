// static/js/time_tracking/leave_types.js
(() => {
  const API = "/api/v1/time-tracking/leave-types";

  // ---------- helpers ----------
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const byId = (id) => (id ? document.getElementById(id) : null);

  // firstNotNullId("a","b") -> element ตัวแรกที่หาเจอ
  const firstNotNullId = (...ids) => {
    for (const id of ids) {
      const el = byId(id);
      if (el) return el;
    }
    return null;
  };

  const toNumber = (v) => {
    if (v === "" || v === null || v === undefined) return 0;
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  };

  const showMsg = (el, msg, ok = true) => {
    if (!el) return;
    el.textContent = msg || "";
    el.className =
      "mt-3 text-sm font-medium " + (ok ? "text-green-700" : "text-red-600");
  };

  const fmt2 = (v) => Number(v || 0).toFixed(2);

  async function apiFetch(url, opts = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    if (!res.ok) {
      let detail = "";
      try {
        detail = (await res.json()).detail || "";
      } catch {}
      throw new Error(detail || res.statusText);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ปลอดภัย: set/get ค่า โดยเช็ค element ก่อน
  const setVal = (id, value) => {
    const el = byId(id);
    if (!el) return;
    if ("checked" in el && typeof value === "boolean") {
      el.checked = value;
    } else {
      el.value = value ?? "";
    }
  };
  const getVal = (id, def = "") => {
    const el = byId(id);
    if (!el) return def;
    if ("checked" in el && el.type === "checkbox") {
      return !!el.checked;
    }
    return el.value ?? def;
  };

  // ---------- table render ----------
  const tbody = $("#leaveTypesTableBody");
  const listMsg = $("#leaveTypesMessage");

  const boolBadge = (val) =>
    val
      ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">Yes</span>`
      : `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">No</span>`;

  function rowHTML(item) {
    const id = item.id;
    const name = item.name || "";
    const desc = item.description || "";
    const annual = item.annual_quota ?? item.max_days_per_year ?? 0;
    const accrue = item.accrue_per_year ?? 0;
    const maxq = item.max_quota ?? 0;
    const affects = !!(item.affects_balance ?? true);
    const paid = !!(item.is_paid_leave ?? item.is_paid ?? true);

    return `
      <tr data-id="${id}">
        <td class="px-4 py-3 text-sm text-gray-700">${id}</td>
        <td class="px-4 py-3 text-sm text-gray-900">${name}</td>
        <td class="px-4 py-3 text-sm text-gray-600">${desc}</td>
        <td class="px-4 py-3 text-right text-sm text-gray-900">${fmt2(annual)}</td>
        <td class="px-4 py-3 text-right text-sm text-gray-900">${fmt2(accrue)}</td>
        <td class="px-4 py-3 text-right text-sm text-gray-900">${fmt2(maxq)}</td>
        <td class="px-4 py-3 text-center">${boolBadge(affects)}</td>
        <td class="px-4 py-3 text-center">${boolBadge(paid)}</td>
        <td class="px-4 py-3 text-center">
          <button class="edit-btn px-3 py-1.5 rounded-md text-sm bg-indigo-600 text-white hover:bg-indigo-700">แก้ไข</button>
          <button class="del-btn px-3 py-1.5 rounded-md text-sm bg-red-600 text-white hover:bg-red-700 ml-2">ลบ</button>
        </td>
      </tr>
    `;
  }

  async function loadList() {
    if (tbody)
      tbody.innerHTML =
        '<tr><td colspan="9" class="px-6 py-4 text-center text-sm text-gray-500">กำลังโหลดข้อมูล...</td></tr>';
    try {
      const data = await apiFetch(`${API}/`);
      if (!tbody) return;
      if (!data || data.length === 0) {
        tbody.innerHTML =
          '<tr><td colspan="9" class="px-6 py-4 text-center text-sm text-gray-500">ยังไม่มีประเภทการลา</td></tr>';
        return;
      }
      tbody.innerHTML = data.map(rowHTML).join("");
    } catch (e) {
      if (tbody)
        tbody.innerHTML = `<tr><td colspan="9" class="px-6 py-4 text-center text-sm text-red-600">โหลดข้อมูลไม่สำเร็จ: ${e.message}</td></tr>`;
    }
  }

  // ---------- Add ----------
  const addForm = $("#addLeaveTypeForm");
  const addMsg = $("#addLeaveTypeMessage");

  async function onAddSubmit(ev) {
    ev.preventDefault();
    showMsg(addMsg, "");

    const annualEl = firstNotNullId("addAnnualQuota", "addMaxDaysPerYear");
    const payload = {
      name: getVal("addName").trim(),
      description: getVal("addDescription").trim(),
      annual_quota: toNumber(annualEl ? annualEl.value : 0),
      accrue_per_year: toNumber(getVal("addAccruePerYear", 0)),
      max_quota: toNumber(getVal("addMaxQuota", 0)),
      affects_balance: !!getVal("addAffects", true),
      is_paid_leave: !!(
        firstNotNullId("addIsPaidLeave", "addIsPaid")?.checked ?? true
      ),
    };

    if (!payload.name) {
      showMsg(addMsg, "กรุณาระบุชื่อประเภทการลา", false);
      return;
    }

    try {
      await apiFetch(`${API}/`, { method: "POST", body: JSON.stringify(payload) });
      showMsg(addMsg, "เพิ่มประเภทการลาสำเร็จ");
      addForm?.reset();
      // reset default checkbox ถ้ามี
      if (byId("addAffects")) byId("addAffects").checked = true;
      const paidEl = firstNotNullId("addIsPaidLeave", "addIsPaid");
      if (paidEl) paidEl.checked = true;
      await loadList();
    } catch (e) {
      showMsg(addMsg, `เพิ่มไม่สำเร็จ: ${e.message}`, false);
    }
  }

  // ---------- Edit modal ----------
  const modal = $("#editLeaveTypeModal");
  const editForm = $("#editLeaveTypeForm");
  const editMsg = $("#editLeaveTypeMessage");
  const openModal = () => {
    if (modal) modal.style.display = "flex";
    showMsg(editMsg, "");
  };
  const closeModal = () => {
    if (modal) modal.style.display = "none";
    showMsg(editMsg, "");
  };

  byId("closeEditModalButton")?.addEventListener("click", closeModal);
  modal?.addEventListener("click", (e) => { if (e.target === modal) closeModal(); });

  async function openEdit(id) {
    showMsg(editMsg, "");
    try {
      const item = await apiFetch(`${API}/${id}`);

      setVal("editLeaveTypeId", item.id);
      setVal("editName", item.name || "");
      setVal("editDescription", item.description || "");

      const annual = item.annual_quota ?? item.max_days_per_year ?? 0;
      const accrue = item.accrue_per_year ?? 0;
      const maxq = item.max_quota ?? 0;

      // map ทั้ง field ใหม่/เก่า อย่าง “ปลอดภัย”
      const annualEl = firstNotNullId("editAnnualQuota", "editMaxDaysPerYear");
      if (annualEl) annualEl.value = annual;

      setVal("editAccruePerYear", accrue);
      setVal("editMaxQuota", maxq);

      const affectsEl = byId("editAffects");
      if (affectsEl) affectsEl.checked = !!(item.affects_balance ?? true);

      const paidEl = byId("editIsPaidLeave");
      if (paidEl) paidEl.checked = !!(item.is_paid_leave ?? item.is_paid ?? true);

      openModal();
    } catch (e) {
      showMsg(listMsg, `เกิดข้อผิดพลาดในการโหลดประเภทการลาเพื่อแก้ไข: ${e.message}`, false);
    }
  }

  async function onEditSubmit(ev) {
    ev.preventDefault();
    showMsg(editMsg, "");

    const id = getVal("editLeaveTypeId");
    const annualEl = firstNotNullId("editAnnualQuota", "editMaxDaysPerYear");

    const payload = {
      name: getVal("editName").trim(),
      description: getVal("editDescription").trim(),
      annual_quota: toNumber(annualEl ? annualEl.value : 0),
      accrue_per_year: toNumber(getVal("editAccruePerYear", 0)),
      max_quota: toNumber(getVal("editMaxQuota", 0)),
      affects_balance: !!(byId("editAffects")?.checked ?? true),
      is_paid_leave: !!(byId("editIsPaidLeave")?.checked ?? true),
    };

    if (!payload.name) {
      showMsg(editMsg, "กรุณาระบุชื่อประเภทการลา", false);
      return;
    }

    try {
      await apiFetch(`${API}/${id}`, { method: "PUT", body: JSON.stringify(payload) });
      showMsg(editMsg, "บันทึกสำเร็จ");
      closeModal();
      await loadList();
    } catch (e) {
      showMsg(editMsg, `บันทึกไม่สำเร็จ: ${e.message}`, false);
    }
  }

  // ---------- Delete ----------
  async function onDelete(id) {
    if (!confirm("ยืนยันการลบประเภทการลานี้?")) return;
    try {
      await apiFetch(`${API}/${id}`, { method: "DELETE" });
      await loadList();
    } catch (e) {
      showMsg(listMsg, `ลบไม่สำเร็จ: ${e.message}`, false);
    }
  }

  // ---------- delegates ----------
  tbody?.addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (!tr) return;
    const id = tr.getAttribute("data-id");
    if (e.target.closest(".edit-btn")) openEdit(id);
    else if (e.target.closest(".del-btn")) onDelete(id);
  });

  addForm?.addEventListener("submit", onAddSubmit);
  editForm?.addEventListener("submit", onEditSubmit);

  // ---------- init ----------
  loadList();
})();
