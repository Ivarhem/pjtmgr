let _centers = [];
let _rooms = [];
let _racks = [];
let _selectedCenterId = null;
let _selectedRoomId = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function selectedCenter() {
  return _centers.find((item) => item.id === _selectedCenterId) || null;
}

function selectedRoom() {
  return _rooms.find((item) => item.id === _selectedRoomId) || null;
}

async function loadCenters() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    _centers = [];
    _rooms = [];
    _racks = [];
    _selectedCenterId = null;
    _selectedRoomId = null;
    renderCenters();
    renderRooms();
    renderRacks();
    syncButtons();
    return;
  }
  _centers = await apiFetch(`/api/v1/centers?partner_id=${partnerId}`);
  if (_selectedCenterId && !_centers.some((item) => item.id === _selectedCenterId)) {
    _selectedCenterId = null;
    _selectedRoomId = null;
  }
  renderCenters();
  if (_selectedCenterId) {
    await loadRooms(_selectedCenterId);
  } else {
    _rooms = [];
    _racks = [];
    renderRooms();
    renderRacks();
  }
  syncButtons();
}

async function loadRooms(centerId) {
  _rooms = await apiFetch(`/api/v1/centers/${centerId}/rooms`);
  if (_selectedRoomId && !_rooms.some((item) => item.id === _selectedRoomId)) {
    _selectedRoomId = null;
  }
  renderRooms();
  if (_selectedRoomId) {
    await loadRacks(_selectedRoomId);
  } else {
    _racks = [];
    renderRacks();
  }
  syncButtons();
}

async function loadRacks(roomId) {
  _racks = await apiFetch(`/api/v1/rooms/${roomId}/racks`);
  renderRacks();
  syncButtons();
}

function renderCenters() {
  const tbody = document.getElementById("center-table-body");
  if (!getCtxPartnerId()) {
    tbody.innerHTML = '<tr><td colspan="6" class="placeholder-message">고객사를 먼저 선택하세요.</td></tr>';
    return;
  }
  if (!_centers.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="placeholder-message">등록된 센터가 없습니다.</td></tr>';
    return;
  }
  tbody.innerHTML = _centers.map((center) => `
    <tr class="${center.id === _selectedCenterId ? "is-selected" : ""}" data-center-id="${center.id}">
      <td>${escapeHtml(center.center_code)}</td>
      <td>${escapeHtml(center.center_name)}</td>
      <td>${escapeHtml(center.location || "—")}</td>
      <td>${center.room_count ?? 0}</td>
      <td>${center.rack_count ?? 0}</td>
      <td class="physical-table-actions">
        <button class="btn btn-xs btn-secondary" data-action="edit-center" data-id="${center.id}">수정</button>
        <button class="btn btn-xs btn-danger" data-action="delete-center" data-id="${center.id}">삭제</button>
      </td>
    </tr>
  `).join("");
}

function renderRooms() {
  const center = selectedCenter();
  const title = document.getElementById("room-panel-title");
  const help = document.getElementById("room-panel-help");
  const tbody = document.getElementById("room-table-body");
  if (!center) {
    title.textContent = "전산실";
    help.textContent = "센터를 선택하면 전산실 목록을 볼 수 있습니다.";
    tbody.innerHTML = '<tr><td colspan="6" class="placeholder-message">센터를 먼저 선택하세요.</td></tr>';
    return;
  }
  title.textContent = `${center.center_name} 전산실`;
  help.textContent = `${center.center_code} 아래의 전산실 기준 데이터를 관리합니다.`;
  if (!_rooms.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="placeholder-message">등록된 전산실이 없습니다.</td></tr>';
    return;
  }
  tbody.innerHTML = _rooms.map((room) => `
    <tr class="${room.id === _selectedRoomId ? "is-selected" : ""}" data-room-id="${room.id}">
      <td>${escapeHtml(room.room_code)}</td>
      <td>${escapeHtml(room.room_name)}</td>
      <td>${escapeHtml(room.floor || "—")}</td>
      <td>${room.rack_count ?? 0}</td>
      <td>${room.is_active ? '<span class="badge badge-active">활성</span>' : '<span class="badge badge-decommissioned">비활성</span>'}</td>
      <td class="physical-table-actions">
        <button class="btn btn-xs btn-secondary" data-action="edit-room" data-id="${room.id}">수정</button>
        <button class="btn btn-xs btn-danger" data-action="delete-room" data-id="${room.id}">삭제</button>
      </td>
    </tr>
  `).join("");
}

function renderRacks() {
  const room = selectedRoom();
  const title = document.getElementById("rack-panel-title");
  const help = document.getElementById("rack-panel-help");
  const tbody = document.getElementById("rack-table-body");
  if (!room) {
    title.textContent = "랙";
    help.textContent = "전산실을 선택하면 랙 목록을 볼 수 있습니다.";
    tbody.innerHTML = '<tr><td colspan="6" class="placeholder-message">전산실을 먼저 선택하세요.</td></tr>';
    return;
  }
  title.textContent = `${room.room_name} 랙`;
  help.textContent = `${room.room_code} 기준으로 자산 랙 정보를 관리합니다.`;
  if (!_racks.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="placeholder-message">등록된 랙이 없습니다.</td></tr>';
    return;
  }
  tbody.innerHTML = _racks.map((rack) => `
    <tr>
      <td>${escapeHtml(rack.rack_code)}</td>
      <td>${escapeHtml(rack.rack_name || "—")}</td>
      <td>${rack.total_units}</td>
      <td>${escapeHtml(rack.location_detail || "—")}</td>
      <td>${rack.is_active ? '<span class="badge badge-active">활성</span>' : '<span class="badge badge-decommissioned">비활성</span>'}</td>
      <td class="physical-table-actions">
        <button class="btn btn-xs btn-secondary" data-action="edit-rack" data-id="${rack.id}">수정</button>
        <button class="btn btn-xs btn-danger" data-action="delete-rack" data-id="${rack.id}">삭제</button>
      </td>
    </tr>
  `).join("");
}

function syncButtons() {
  document.getElementById("btn-add-room").disabled = !_selectedCenterId;
  document.getElementById("btn-add-rack").disabled = !_selectedRoomId;
}

function openCenterModal(center = null) {
  document.getElementById("modal-center-title").textContent = center ? "센터 수정" : "센터 등록";
  document.getElementById("center-id").value = center?.id ?? "";
  document.getElementById("center-code").value = center?.center_code ?? "";
  document.getElementById("center-name").value = center?.center_name ?? "";
  document.getElementById("center-location").value = center?.location ?? "";
  document.getElementById("center-active").value = String(center?.is_active ?? true);
  document.getElementById("center-note").value = center?.note ?? "";
  document.getElementById("modal-center").showModal();
}

function openRoomModal(room = null) {
  if (!_selectedCenterId) {
    showToast("센터를 먼저 선택하세요.", "warning");
    return;
  }
  document.getElementById("modal-room-title").textContent = room ? "전산실 수정" : "전산실 등록";
  document.getElementById("room-id").value = room?.id ?? "";
  document.getElementById("room-code").value = room?.room_code ?? "";
  document.getElementById("room-name").value = room?.room_name ?? "";
  document.getElementById("room-floor").value = room?.floor ?? "";
  document.getElementById("room-active").value = String(room?.is_active ?? true);
  document.getElementById("room-note").value = room?.note ?? "";
  document.getElementById("modal-room").showModal();
}

function openRackModal(rack = null) {
  if (!_selectedRoomId) {
    showToast("전산실을 먼저 선택하세요.", "warning");
    return;
  }
  document.getElementById("modal-rack-title").textContent = rack ? "랙 수정" : "랙 등록";
  document.getElementById("rack-id").value = rack?.id ?? "";
  document.getElementById("rack-code").value = rack?.rack_code ?? "";
  document.getElementById("rack-name").value = rack?.rack_name ?? "";
  document.getElementById("rack-total-units").value = rack?.total_units ?? 42;
  document.getElementById("rack-location-detail").value = rack?.location_detail ?? "";
  document.getElementById("rack-active").value = String(rack?.is_active ?? true);
  document.getElementById("rack-note").value = rack?.note ?? "";
  document.getElementById("modal-rack").showModal();
}

async function saveCenter() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    showToast("고객사를 먼저 선택하세요.", "warning");
    return;
  }
  const centerId = document.getElementById("center-id").value;
  const payload = {
    partner_id: partnerId,
    center_name: document.getElementById("center-name").value.trim(),
    location: document.getElementById("center-location").value.trim() || null,
    is_active: document.getElementById("center-active").value === "true",
    note: document.getElementById("center-note").value.trim() || null,
  };
  if (!payload.center_name) {
    showToast("센터명은 필수입니다.", "warning");
    return;
  }
  if (centerId) {
    await apiFetch(`/api/v1/centers/${centerId}`, { method: "PATCH", body: payload });
    showToast("센터를 수정했습니다.");
  } else {
    const created = await apiFetch("/api/v1/centers", { method: "POST", body: payload });
    _selectedCenterId = created.id;
    _selectedRoomId = null;
    showToast("센터를 등록했습니다. 기본 전산실 MAIN이 함께 생성되었습니다.");
  }
  document.getElementById("modal-center").close();
  await loadCenters();
}

async function saveRoom() {
  if (!_selectedCenterId) {
    showToast("센터를 먼저 선택하세요.", "warning");
    return;
  }
  const roomId = document.getElementById("room-id").value;
  const payload = {
    center_id: _selectedCenterId,
    room_name: document.getElementById("room-name").value.trim(),
    floor: document.getElementById("room-floor").value.trim() || null,
    is_active: document.getElementById("room-active").value === "true",
    note: document.getElementById("room-note").value.trim() || null,
  };
  if (!payload.room_name) {
    showToast("전산실명은 필수입니다.", "warning");
    return;
  }
  if (roomId) {
    await apiFetch(`/api/v1/rooms/${roomId}`, { method: "PATCH", body: payload });
    showToast("전산실을 수정했습니다.");
  } else {
    const created = await apiFetch(`/api/v1/centers/${_selectedCenterId}/rooms`, { method: "POST", body: payload });
    _selectedRoomId = created.id;
    showToast("전산실을 등록했습니다.");
  }
  document.getElementById("modal-room").close();
  await loadRooms(_selectedCenterId);
}

async function saveRack() {
  if (!_selectedRoomId) {
    showToast("전산실을 먼저 선택하세요.", "warning");
    return;
  }
  const rackId = document.getElementById("rack-id").value;
  const payload = {
    room_id: _selectedRoomId,
    rack_name: document.getElementById("rack-name").value.trim() || null,
    total_units: Number(document.getElementById("rack-total-units").value || 42),
    location_detail: document.getElementById("rack-location-detail").value.trim() || null,
    is_active: document.getElementById("rack-active").value === "true",
    note: document.getElementById("rack-note").value.trim() || null,
  };
  if (rackId) {
    await apiFetch(`/api/v1/racks/${rackId}`, { method: "PATCH", body: payload });
    showToast("랙을 수정했습니다.");
  } else {
    await apiFetch(`/api/v1/rooms/${_selectedRoomId}/racks`, { method: "POST", body: payload });
    showToast("랙을 등록했습니다.");
  }
  document.getElementById("modal-rack").close();
  await loadRacks(_selectedRoomId);
  await loadCenters();
}

function bindCenterTable() {
  document.getElementById("center-table-body").addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    const row = event.target.closest("tr[data-center-id]");
    if (button) {
      const center = _centers.find((item) => item.id === Number(button.dataset.id));
      if (!center) return;
      if (button.dataset.action === "edit-center") {
        openCenterModal(center);
        return;
      }
      confirmDelete(`센터 "${center.center_name}"을(를) 삭제하시겠습니까?`, async () => {
        try {
          await apiFetch(`/api/v1/centers/${center.id}`, { method: "DELETE" });
          if (_selectedCenterId === center.id) {
            _selectedCenterId = null;
            _selectedRoomId = null;
          }
          showToast("센터를 삭제했습니다.");
          await loadCenters();
        } catch (err) {
          showToast(err.message, "error");
        }
      });
      return;
    }
    if (!row) return;
    const centerId = Number(row.dataset.centerId);
    if (!centerId || centerId === _selectedCenterId) return;
    _selectedCenterId = centerId;
    _selectedRoomId = null;
    renderCenters();
    await loadRooms(centerId);
  });
}

function bindRoomTable() {
  document.getElementById("room-table-body").addEventListener("click", async (event) => {
    const button = event.target.closest("button[data-action]");
    const row = event.target.closest("tr[data-room-id]");
    if (button) {
      const room = _rooms.find((item) => item.id === Number(button.dataset.id));
      if (!room) return;
      if (button.dataset.action === "edit-room") {
        openRoomModal(room);
        return;
      }
      confirmDelete(`전산실 "${room.room_name}"을(를) 삭제하시겠습니까?`, async () => {
        try {
          await apiFetch(`/api/v1/rooms/${room.id}`, { method: "DELETE" });
          if (_selectedRoomId === room.id) {
            _selectedRoomId = null;
          }
          showToast("전산실을 삭제했습니다.");
          await loadRooms(_selectedCenterId);
          await loadCenters();
        } catch (err) {
          showToast(err.message, "error");
        }
      });
      return;
    }
    if (!row) return;
    const roomId = Number(row.dataset.roomId);
    if (!roomId || roomId === _selectedRoomId) return;
    _selectedRoomId = roomId;
    renderRooms();
    await loadRacks(roomId);
  });
}

function bindRackTable() {
  document.getElementById("rack-table-body").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const rack = _racks.find((item) => item.id === Number(button.dataset.id));
    if (!rack) return;
    if (button.dataset.action === "edit-rack") {
      openRackModal(rack);
      return;
    }
    confirmDelete(`랙 "${rack.rack_code}"을(를) 삭제하시겠습니까?`, async () => {
      try {
        await apiFetch(`/api/v1/racks/${rack.id}`, { method: "DELETE" });
        showToast("랙을 삭제했습니다.");
        await loadRacks(_selectedRoomId);
        await loadCenters();
      } catch (err) {
        showToast(err.message, "error");
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindCenterTable();
  bindRoomTable();
  bindRackTable();
  loadCenters().catch((err) => showToast(err.message, "error"));
});

window.addEventListener("ctx-changed", () => {
  _selectedCenterId = null;
  _selectedRoomId = null;
  _rooms = [];
  _racks = [];
  loadCenters().catch((err) => showToast(err.message, "error"));
});

document.getElementById("btn-add-center").addEventListener("click", () => openCenterModal());
document.getElementById("btn-add-room").addEventListener("click", () => openRoomModal());
document.getElementById("btn-add-rack").addEventListener("click", () => openRackModal());
document.getElementById("btn-cancel-center").addEventListener("click", () => document.getElementById("modal-center").close());
document.getElementById("btn-save-center").addEventListener("click", () => saveCenter().catch((err) => showToast(err.message, "error")));
document.getElementById("btn-cancel-room").addEventListener("click", () => document.getElementById("modal-room").close());
document.getElementById("btn-save-room").addEventListener("click", () => saveRoom().catch((err) => showToast(err.message, "error")));
document.getElementById("btn-cancel-rack").addEventListener("click", () => document.getElementById("modal-rack").close());
document.getElementById("btn-save-rack").addEventListener("click", () => saveRack().catch((err) => showToast(err.message, "error")));
