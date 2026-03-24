/* ── 프로젝트 업체 (고객사/프로젝트 스코프) ── */

let _pcPartnersCache = [];
let _pcContactsCache = [];

async function loadProjectPartners() {
  const container = document.getElementById("partners-list");
  const pid = getCtxProjectId();
  if (!pid) {
    container.textContent = "";
    const p = document.createElement("p");
    p.className = "text-muted";
    p.textContent = "프로젝트를 선택하세요.";
    container.appendChild(p);
    return;
  }
  try {
    const [partners, contacts] = await Promise.all([
      apiFetch("/api/v1/period-partners?contract_period_id=" + pid),
      apiFetch("/api/v1/period-partner-contacts?contract_period_id=" + pid),
    ]);
    _pcPartnersCache = partners;
    _pcContactsCache = contacts;
    renderProjectPartners(container, partners, contacts);
  } catch (err) {
    container.textContent = "업체 정보를 불러올 수 없습니다.";
    showToast(err.message, "error");
  }
}

function renderProjectPartners(container, partners, contacts) {
  container.textContent = "";
  if (partners.length === 0) {
    const p = document.createElement("p");
    p.className = "text-muted pc-placeholder";
    p.textContent = "연결된 업체가 없습니다. '업체 연결' 버튼으로 추가하세요.";
    container.appendChild(p);
    return;
  }

  partners.forEach(pc => {
    const card = document.createElement("div");
    card.className = "card mb-sm pc-card";

    const header = document.createElement("div");
    header.className = "pc-header";
    const badge = document.createElement("span");
    badge.className = "badge badge-active";
    badge.textContent = pc.role;
    header.appendChild(badge);
    const name = document.createElement("strong");
    name.textContent = pc.partner_name || "(알수없음)";
    header.appendChild(name);
    if (pc.scope_text) {
      const scope = document.createElement("span");
      scope.className = "text-muted pc-scope";
      scope.textContent = " — " + pc.scope_text;
      header.appendChild(scope);
    }
    const spacer = document.createElement("span");
    spacer.className = "pc-spacer";
    header.appendChild(spacer);
    const addBtn = document.createElement("button");
    addBtn.className = "btn btn-xs btn-secondary";
    addBtn.textContent = "+ 담당자";
    addBtn.addEventListener("click", () => openAddContactModal(pc));
    header.appendChild(addBtn);
    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-xs btn-danger";
    delBtn.textContent = "해제";
    delBtn.addEventListener("click", () => deleteProjectPartner(pc.id));
    header.appendChild(delBtn);
    card.appendChild(header);

    const pcContacts = contacts.filter(c => c.project_partner_id === pc.id);
    if (pcContacts.length > 0) {
      const table = document.createElement("table");
      table.className = "pc-contacts-table";
      pcContacts.forEach(ct => {
        const tr = document.createElement("tr");
        [ct.project_role, ct.contact_name || "", ct.contact_phone || "", ct.contact_email || ""].forEach(txt => {
          const td = document.createElement("td");
          td.textContent = txt;
          tr.appendChild(td);
        });
        const tdAction = document.createElement("td");
        const rmBtn = document.createElement("button");
        rmBtn.className = "btn btn-xs btn-danger";
        rmBtn.textContent = "해제";
        rmBtn.addEventListener("click", () => deleteProjectPartnerContact(ct.id));
        tdAction.appendChild(rmBtn);
        tr.appendChild(tdAction);
        table.appendChild(tr);
      });
      card.appendChild(table);
    } else {
      const empty = document.createElement("p");
      empty.className = "text-muted pc-empty";
      empty.textContent = "담당자 없음";
      card.appendChild(empty);
    }
    container.appendChild(card);
  });
}

/* ── Modals ── */
const pcModal = document.getElementById("modal-project-partner");
const pccModal = document.getElementById("modal-project-partner-contact");

async function openAddPartnerModal() {
  const pid = getCtxProjectId();
  if (!pid) { showToast("프로젝트를 먼저 선택하세요.", "warning"); return; }
  document.getElementById("pc-id").value = "";
  document.getElementById("pc-scope-text").value = "";
  document.getElementById("pc-note").value = "";
  document.getElementById("pc-role").value = "고객사";
  document.getElementById("modal-pc-title").textContent = "업체 연결";
  const sel = document.getElementById("pc-partner-id");
  sel.textContent = "";
  try {
    const partners = await apiFetch("/api/v1/partners");
    partners.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      sel.appendChild(opt);
    });
  } catch (err) { showToast("거래처 로드 실패", "error"); }
  pcModal.showModal();
}

async function saveProjectPartner() {
  const pid = getCtxProjectId();
  const pcId = document.getElementById("pc-id").value;
  const payload = {
    contract_period_id: pid,
    partner_id: Number(document.getElementById("pc-partner-id").value),
    role: document.getElementById("pc-role").value,
    scope_text: document.getElementById("pc-scope-text").value || null,
    note: document.getElementById("pc-note").value || null,
  };
  try {
    if (pcId) {
      await apiFetch("/api/v1/period-partners/" + pcId, { method: "PATCH", body: payload });
      showToast("업체 정보가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/period-partners", { method: "POST", body: payload });
      showToast("업체가 연결되었습니다.");
    }
    pcModal.close();
    loadProjectPartners();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteProjectPartner(pcId) {
  confirmDelete("업체 연결을 해제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/period-partners/" + pcId, { method: "DELETE" });
      showToast("업체 연결이 해제되었습니다.");
      loadProjectPartners();
    } catch (err) { showToast(err.message, "error"); }
  });
}

async function openAddContactModal(pc) {
  document.getElementById("pcc-id").value = "";
  document.getElementById("pcc-project-partner-id").value = pc.id;
  document.getElementById("pcc-note").value = "";
  document.getElementById("pcc-project-role").value = "고객PM";
  document.getElementById("modal-pcc-title").textContent = "담당자 연결 — " + pc.partner_name + " (" + pc.role + ")";
  const sel = document.getElementById("pcc-contact-id");
  sel.textContent = "";
  try {
    const contacts = await apiFetch("/api/v1/partners/" + pc.partner_id + "/contacts");
    contacts.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name + (c.phone ? " (" + c.phone + ")" : "");
      sel.appendChild(opt);
    });
    if (contacts.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(등록된 담당자 없음)";
      sel.appendChild(opt);
    }
  } catch (err) { showToast("담당자 로드 실패", "error"); }
  pccModal.showModal();
}

async function saveProjectPartnerContact() {
  const pccId = document.getElementById("pcc-id").value;
  const payload = {
    project_partner_id: Number(document.getElementById("pcc-project-partner-id").value),
    contact_id: Number(document.getElementById("pcc-contact-id").value),
    project_role: document.getElementById("pcc-project-role").value,
    note: document.getElementById("pcc-note").value || null,
  };
  try {
    if (pccId) {
      await apiFetch("/api/v1/period-partner-contacts/" + pccId, { method: "PATCH", body: payload });
      showToast("담당자 정보가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/period-partner-contacts", { method: "POST", body: payload });
      showToast("담당자가 연결되었습니다.");
    }
    pccModal.close();
    loadProjectPartners();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteProjectPartnerContact(pccId) {
  confirmDelete("담당자 연결을 해제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/period-partner-contacts/" + pccId, { method: "DELETE" });
      showToast("담당자 연결이 해제되었습니다.");
      loadProjectPartners();
    } catch (err) { showToast(err.message, "error"); }
  });
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("btn-add-partner").addEventListener("click", openAddPartnerModal);
  document.getElementById("btn-cancel-pc").addEventListener("click", () => pcModal.close());
  document.getElementById("btn-save-pc").addEventListener("click", saveProjectPartner);
  document.getElementById("btn-cancel-pcc").addEventListener("click", () => pccModal.close());
  document.getElementById("btn-save-pcc").addEventListener("click", saveProjectPartnerContact);

  setTimeout(() => loadProjectPartners(), 400);
});

window.addEventListener("ctx-changed", () => loadProjectPartners());
