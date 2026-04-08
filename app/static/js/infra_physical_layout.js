/* ── Physical Layout: Tree + Content Panel ── */

const LAYOUT_TREE_WIDTH_KEY = "physicalLayout.treeWidth";

let _centers = [];
let _rooms = {};      // centerId -> rooms[]
let _racks = {};       // roomId -> racks[]
let _selectedNode = null; // { type, id, data }
let _selectedCenterId = null;
let _selectedRoomId = null;
let _treeCollapsed = new Set();

/* ── Data Loading ── */

async function loadTree() {
  const cid = getCtxPartnerId();
  if (!cid) {
    _centers = [];
    _rooms = {};
    _racks = {};
    _selectedNode = null;
    _selectedCenterId = null;
    _selectedRoomId = null;
    renderEmptyTree();
    renderEmptyContent();
    syncButtons();
    return;
  }

  _centers = await apiFetch("/api/v1/centers?partner_id=" + cid);
  _rooms = {};
  _racks = {};

  for (const center of _centers) {
    const rooms = await apiFetch("/api/v1/centers/" + center.id + "/rooms");
    _rooms[center.id] = rooms;
    for (const room of rooms) {
      const racks = await apiFetch("/api/v1/rooms/" + room.id + "/racks");
      _racks[room.id] = racks;
    }
  }

  renderTree();
  syncButtons();

  // Re-select previously selected node if still valid
  if (_selectedNode) {
    const { type, id } = _selectedNode;
    const found = findNodeData(type, id);
    if (found) {
      selectNode(type, id, found);
    } else {
      _selectedNode = null;
      _selectedCenterId = null;
      _selectedRoomId = null;
      renderEmptyContent();
    }
  }
}

function findNodeData(type, id) {
  if (type === "center") return _centers.find(c => c.id === id) || null;
  if (type === "room") {
    for (const rooms of Object.values(_rooms)) {
      const r = rooms.find(r => r.id === id);
      if (r) return r;
    }
    return null;
  }
  if (type === "rack") {
    for (const racks of Object.values(_racks)) {
      const r = racks.find(r => r.id === id);
      if (r) return r;
    }
    return null;
  }
  return null;
}

/* ── Tree Rendering ── */

function renderEmptyTree() {
  const container = document.getElementById("layout-tree");
  container.textContent = "";
  const p = document.createElement("p");
  p.className = "text-muted";
  p.style.padding = "12px";
  p.textContent = "고객사를 선택하면 배치 구조를 표시합니다.";
  container.appendChild(p);
}

function renderTree() {
  const container = document.getElementById("layout-tree");
  container.textContent = "";

  if (!_centers.length) {
    const p = document.createElement("p");
    p.className = "text-muted";
    p.style.padding = "12px";
    p.textContent = "등록된 센터가 없습니다.";
    container.appendChild(p);
    return;
  }

  const rootUl = document.createElement("ul");
  rootUl.className = "classification-tree-root";

  _centers.forEach(center => {
    const rooms = _rooms[center.id] || [];
    const centerKey = "center-" + center.id;
    const centerCollapsed = _treeCollapsed.has(centerKey);

    // Group rooms by floor
    const floorMap = {};
    rooms.forEach(room => {
      const floor = room.floor || "\uAE30\uBCF8\uCE35";
      if (!floorMap[floor]) floorMap[floor] = [];
      floorMap[floor].push(room);
    });
    const floorKeys = Object.keys(floorMap).sort((a, b) => a.localeCompare(b, "ko-KR"));

    // Build floor children
    const centerChildUl = document.createElement("ul");
    floorKeys.forEach(floor => {
      const floorRooms = floorMap[floor];
      const floorKey = "floor-" + center.id + "-" + floor;
      const floorCollapsed = _treeCollapsed.has(floorKey);

      // Build room children
      const floorChildUl = document.createElement("ul");
      floorRooms.forEach(room => {
        const racks = _racks[room.id] || [];
        const roomKey = "room-" + room.id;
        const roomCollapsed = _treeCollapsed.has(roomKey);

        // Build rack children
        const roomChildUl = document.createElement("ul");
        racks.forEach(rack => {
          roomChildUl.appendChild(createTreeNode({
            key: "rack-" + rack.id,
            icon: "\uD83D\uDCBD",
            label: rack.rack_name || rack.rack_code,
            meta: rack.total_units + "U",
            nodeType: "rack",
            nodeId: rack.id,
            nodeData: rack,
            hasChildren: false,
            collapsed: false,
            childUl: null,
          }));
        });

        floorChildUl.appendChild(createTreeNode({
          key: roomKey,
          icon: "\uD83D\uDEAA",
          label: room.room_name,
          meta: racks.length + " \uB799",
          nodeType: "room",
          nodeId: room.id,
          nodeData: room,
          hasChildren: racks.length > 0,
          collapsed: roomCollapsed,
          childUl: roomChildUl,
        }));
      });

      // Only show floor grouping if there are multiple floors
      if (floorKeys.length > 1) {
        centerChildUl.appendChild(createTreeNode({
          key: floorKey,
          icon: "",
          label: floor,
          meta: floorRooms.length + " \uC2E4",
          nodeType: "floor",
          nodeId: center.id + "-" + floor,
          nodeData: { center, floor, rooms: floorRooms },
          hasChildren: floorRooms.length > 0,
          collapsed: floorCollapsed,
          childUl: floorChildUl,
        }));
      } else {
        // Single floor: attach rooms directly under center
        floorRooms.forEach(room => {
          const racks = _racks[room.id] || [];
          const roomKey = "room-" + room.id;
          const roomCollapsed2 = _treeCollapsed.has(roomKey);

          const roomChildUl2 = document.createElement("ul");
          racks.forEach(rack => {
            roomChildUl2.appendChild(createTreeNode({
              key: "rack-" + rack.id,
              icon: "\uD83D\uDCBD",
              label: rack.rack_name || rack.rack_code,
              meta: rack.total_units + "U",
              nodeType: "rack",
              nodeId: rack.id,
              nodeData: rack,
              hasChildren: false,
              collapsed: false,
              childUl: null,
            }));
          });

          centerChildUl.appendChild(createTreeNode({
            key: roomKey,
            icon: "\uD83D\uDEAA",
            label: room.room_name,
            meta: racks.length + " \uB799",
            nodeType: "room",
            nodeId: room.id,
            nodeData: room,
            hasChildren: racks.length > 0,
            collapsed: roomCollapsed2,
            childUl: roomChildUl2,
          }));
        });
      }
    });

    const totalRacks = rooms.reduce((sum, r) => sum + (_racks[r.id] || []).length, 0);
    rootUl.appendChild(createTreeNode({
      key: centerKey,
      icon: "\uD83D\uDCCD",
      label: center.center_name,
      meta: rooms.length + " \uC2E4 / " + totalRacks + " \uB799",
      nodeType: "center",
      nodeId: center.id,
      nodeData: center,
      hasChildren: rooms.length > 0,
      collapsed: centerCollapsed,
      childUl: centerChildUl,
    }));
  });

  container.appendChild(rootUl);
}

function createTreeNode({ key, icon, label, meta, nodeType, nodeId, nodeData, hasChildren, collapsed, childUl }) {
  const li = document.createElement("li");
  li.className = "classification-tree-item";

  const nodeDiv = document.createElement("div");
  nodeDiv.className = "classification-tree-node";
  nodeDiv.setAttribute("data-node-type", nodeType);
  nodeDiv.setAttribute("data-node-id", String(nodeId));

  // Mark active
  if (_selectedNode && _selectedNode.type === nodeType && String(_selectedNode.id) === String(nodeId)) {
    nodeDiv.classList.add("is-selected");
  }

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "classification-tree-node-main";

  // Toggle arrow
  const toggle = document.createElement("span");
  if (hasChildren) {
    toggle.className = "classification-tree-toggle";
    toggle.textContent = collapsed ? "\u25B8" : "\u25BE";
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      if (_treeCollapsed.has(key)) {
        _treeCollapsed.delete(key);
      } else {
        _treeCollapsed.add(key);
      }
      renderTree();
    });
  } else {
    toggle.className = "classification-tree-toggle is-placeholder";
    toggle.textContent = "\u2022";
  }

  const mainSpan = document.createElement("span");
  mainSpan.className = "classification-tree-main";

  const titleSpan = document.createElement("span");
  titleSpan.className = "classification-tree-title";

  const nameSpan = document.createElement("span");
  nameSpan.className = "classification-tree-name";
  nameSpan.textContent = (icon ? icon + " " : "") + label;

  const codeSpan = document.createElement("span");
  codeSpan.className = "classification-tree-code";
  codeSpan.textContent = meta;

  titleSpan.appendChild(nameSpan);
  titleSpan.appendChild(codeSpan);
  mainSpan.appendChild(titleSpan);
  btn.appendChild(toggle);
  btn.appendChild(mainSpan);

  btn.addEventListener("click", () => selectNode(nodeType, nodeId, nodeData));

  nodeDiv.appendChild(btn);
  li.appendChild(nodeDiv);

  if (hasChildren && childUl) {
    if (collapsed) {
      childUl.style.display = "none";
    }
    li.appendChild(childUl);
  }

  return li;
}

/* ── Node Selection ── */

function selectNode(type, id, data) {
  _selectedNode = { type, id, data };

  // Track selection for CRUD
  if (type === "center") {
    _selectedCenterId = id;
  } else if (type === "floor") {
    _selectedCenterId = data.center ? data.center.id : null;
  } else if (type === "room") {
    _selectedCenterId = data.center_id;
    _selectedRoomId = id;
  } else if (type === "rack") {
    _selectedRoomId = data.room_id;
    // Find center from room
    for (const [centerId, rooms] of Object.entries(_rooms)) {
      if (rooms.some(r => r.id === data.room_id)) {
        _selectedCenterId = Number(centerId);
        break;
      }
    }
  }

  syncButtons();

  // Highlight active tree node
  document.querySelectorAll(".classification-tree-node").forEach(n => n.classList.remove("is-selected"));
  const activeNode = document.querySelector('[data-node-type="' + type + '"][data-node-id="' + id + '"]');
  if (activeNode) activeNode.classList.add("is-selected");

  // Render right panel
  const content = document.getElementById("layout-content");
  content.textContent = "";
  content.style.margin = "";

  if (type === "center") renderCenterView(content, data);
  else if (type === "floor") renderFloorView(content, data);
  else if (type === "room") renderRoomView(content, data);
  else if (type === "rack") renderRackView(content, data);
}

function renderEmptyContent() {
  const content = document.getElementById("layout-content");
  content.textContent = "";
  const div = document.createElement("div");
  div.className = "placeholder-message";
  div.style.margin = "auto";
  const p = document.createElement("p");
  p.textContent = "\uC67C\uCABD \uD2B8\uB9AC\uC5D0\uC11C \uC13C\uD130, \uC804\uC0B0\uC2E4 \uB610\uB294 \uB799\uC744 \uC120\uD0DD\uD558\uC138\uC694.";
  div.appendChild(p);
  content.appendChild(div);
}

function syncButtons() {
  const type = _selectedNode ? _selectedNode.type : null;
  document.getElementById("btn-add-room").disabled = !(type === "center" || type === "floor");
  document.getElementById("btn-add-rack").disabled = type !== "room";
}

/* ── Content Views ── */

function createStatusBadge(isActive) {
  const span = document.createElement("span");
  span.className = isActive ? "badge badge-active" : "badge badge-decommissioned";
  span.textContent = isActive ? "\uD65C\uC131" : "\uBE44\uD65C\uC131";
  return span;
}

function appendFieldRow(parent, label, valueOrNode) {
  const row = document.createElement("div");
  row.style.cssText = "display:flex;gap:12px;padding:4px 0;";
  const labelSpan = document.createElement("span");
  labelSpan.className = "text-muted";
  labelSpan.style.cssText = "min-width:80px;flex-shrink:0;";
  labelSpan.textContent = label;
  row.appendChild(labelSpan);
  const valueSpan = document.createElement("span");
  if (typeof valueOrNode === "string") {
    valueSpan.textContent = valueOrNode;
  } else {
    valueSpan.appendChild(valueOrNode);
  }
  row.appendChild(valueSpan);
  parent.appendChild(row);
}

function createContentHeader(icon, title, editCb, deleteCb) {
  const header = document.createElement("div");
  header.style.cssText = "display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;";
  const h = document.createElement("h3");
  h.textContent = icon + " " + title;
  h.style.margin = "0";
  header.appendChild(h);

  const actions = document.createElement("div");
  actions.className = "infra-inline-actions";
  const btnEdit = document.createElement("button");
  btnEdit.className = "btn btn-secondary btn-sm";
  btnEdit.textContent = "\uC218\uC815";
  btnEdit.addEventListener("click", editCb);
  const btnDel = document.createElement("button");
  btnDel.className = "btn btn-danger btn-sm";
  btnDel.textContent = "\uC0AD\uC81C";
  btnDel.addEventListener("click", deleteCb);
  actions.appendChild(btnEdit);
  actions.appendChild(btnDel);
  header.appendChild(actions);
  return header;
}

function renderCenterView(container, center) {
  const wrapper = createContentWrapper();
  container.appendChild(wrapper);

  wrapper.appendChild(createContentHeader(
    "\uD83D\uDCCD", center.center_name,
    () => openCenterModal(center),
    () => deleteCenter(center),
  ));

  // Info card
  const info = document.createElement("div");
  info.className = "card";
  info.style.padding = "16px";
  appendFieldRow(info, "\uC13C\uD130\uCF54\uB4DC", center.center_code);
  appendFieldRow(info, "\uC704\uCE58", center.location || "\u2014");
  appendFieldRow(info, "\uC0C1\uD0DC", createStatusBadge(center.is_active));
  appendFieldRow(info, "\uBE44\uACE0", center.note || "\u2014");
  wrapper.appendChild(info);

  // Room summary
  const rooms = _rooms[center.id] || [];
  if (rooms.length) {
    const h2 = document.createElement("h4");
    h2.textContent = "\uC804\uC0B0\uC2E4 \uBAA9\uB85D (" + rooms.length + ")";
    h2.style.marginTop = "20px";
    wrapper.appendChild(h2);

    rooms.forEach(room => {
      const racks = _racks[room.id] || [];
      const card = document.createElement("div");
      card.className = "card";
      card.style.cssText = "padding:12px;margin-top:8px;cursor:pointer;";
      const strong = document.createElement("strong");
      strong.textContent = "\uD83D\uDEAA " + room.room_name;
      card.appendChild(strong);
      const meta = document.createElement("span");
      meta.className = "text-muted";
      meta.style.marginLeft = "8px";
      meta.textContent = (room.floor || "") + " / " + racks.length + " \uB799";
      card.appendChild(meta);
      card.addEventListener("click", () => selectNode("room", room.id, room));
      wrapper.appendChild(card);
    });
  }
}

function renderFloorView(container, data) {
  const wrapper = createContentWrapper();
  container.appendChild(wrapper);

  const h = document.createElement("h3");
  h.textContent = data.floor + " (" + data.center.center_name + ")";
  wrapper.appendChild(h);

  const rooms = data.rooms || [];
  if (rooms.length) {
    rooms.forEach(room => {
      const racks = _racks[room.id] || [];
      const card = document.createElement("div");
      card.className = "card";
      card.style.cssText = "padding:12px;margin-top:8px;cursor:pointer;";
      const strong = document.createElement("strong");
      strong.textContent = "\uD83D\uDEAA " + room.room_name;
      card.appendChild(strong);
      const meta = document.createElement("span");
      meta.className = "text-muted";
      meta.style.marginLeft = "8px";
      meta.textContent = racks.length + " \uB799";
      card.appendChild(meta);
      card.addEventListener("click", () => selectNode("room", room.id, room));
      wrapper.appendChild(card);
    });
  } else {
    const p = document.createElement("p");
    p.className = "text-muted";
    p.textContent = "\uC774 \uCE35\uC5D0 \uC804\uC0B0\uC2E4\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.";
    wrapper.appendChild(p);
  }
}

function renderRoomView(container, room) {
  const wrapper = createContentWrapper();
  container.appendChild(wrapper);

  wrapper.appendChild(createContentHeader(
    "\uD83D\uDEAA", room.room_name,
    () => openRoomModal(room),
    () => deleteRoom(room),
  ));

  // Info card
  const info = document.createElement("div");
  info.className = "card";
  info.style.padding = "16px";
  appendFieldRow(info, "\uC804\uC0B0\uC2E4\uCF54\uB4DC", room.room_code);
  appendFieldRow(info, "\uCE35", room.floor || "\u2014");
  appendFieldRow(info, "\uB799 \uC5F4 \uC218", String(room.racks_per_row ?? "\u2014"));
  appendFieldRow(info, "\uC0C1\uD0DC", createStatusBadge(room.is_active));
  appendFieldRow(info, "\uBE44\uACE0", room.note || "\u2014");
  wrapper.appendChild(info);

  // Placeholder for rack layout visualization
  const p = document.createElement("p");
  p.className = "text-muted";
  p.style.marginTop = "16px";
  p.textContent = "\uB799 \uBC30\uCE58\uB3C4\uAC00 \uC5EC\uAE30\uC5D0 \uD45C\uC2DC\uB429\uB2C8\uB2E4.";
  wrapper.appendChild(p);

  // List racks as cards
  const racks = _racks[room.id] || [];
  if (racks.length) {
    const h2 = document.createElement("h4");
    h2.textContent = "\uB799 \uBAA9\uB85D (" + racks.length + ")";
    h2.style.marginTop = "16px";
    wrapper.appendChild(h2);

    racks.forEach(rack => {
      const card = document.createElement("div");
      card.className = "card";
      card.style.cssText = "padding:12px;margin-top:8px;cursor:pointer;";
      card.textContent = "\uD83D\uDCBD " + (rack.rack_name || rack.rack_code) + " (" + rack.total_units + "U)";
      card.addEventListener("click", () => selectNode("rack", rack.id, rack));
      wrapper.appendChild(card);
    });
  }
}

function renderRackView(container, rack) {
  const wrapper = createContentWrapper();
  container.appendChild(wrapper);

  wrapper.appendChild(createContentHeader(
    "\uD83D\uDCBD", rack.rack_name || rack.rack_code,
    () => openRackModal(rack),
    () => deleteRack(rack),
  ));

  // Info card
  const info = document.createElement("div");
  info.className = "card";
  info.style.padding = "16px";
  appendFieldRow(info, "\uB799\uCF54\uB4DC", rack.rack_code);
  appendFieldRow(info, "\uB799\uBA85", rack.rack_name || "\u2014");
  appendFieldRow(info, "\uCD1D U", String(rack.total_units));
  appendFieldRow(info, "\uC704\uCE58\uC0C1\uC138", rack.location_detail || "\u2014");
  appendFieldRow(info, "\uC0C1\uD0DC", createStatusBadge(rack.is_active));
  appendFieldRow(info, "\uBE44\uACE0", rack.note || "\u2014");
  wrapper.appendChild(info);

  // Placeholder for equipment layout
  const p = document.createElement("p");
  p.className = "text-muted";
  p.style.marginTop = "16px";
  p.textContent = "\uC7A5\uBE44 \uBC30\uCE58\uB3C4\uAC00 \uC5EC\uAE30\uC5D0 \uD45C\uC2DC\uB429\uB2C8\uB2E4.";
  wrapper.appendChild(p);
}

/* ── Helpers ── */

function createContentWrapper() {
  const div = document.createElement("div");
  div.style.cssText = "padding:20px;overflow:auto;width:100%;";
  return div;
}

/* ── CRUD Modals ── */

function openCenterModal(center) {
  document.getElementById("modal-center-title").textContent = center ? "\uC13C\uD130 \uC218\uC815" : "\uC13C\uD130 \uB4F1\uB85D";
  document.getElementById("center-id").value = center?.id ?? "";
  document.getElementById("center-code").value = center?.center_code ?? "";
  document.getElementById("center-name").value = center?.center_name ?? "";
  document.getElementById("center-location").value = center?.location ?? "";
  document.getElementById("center-active").value = String(center?.is_active ?? true);
  document.getElementById("center-note").value = center?.note ?? "";
  document.getElementById("modal-center").showModal();
}

function openRoomModal(room) {
  if (!_selectedCenterId) {
    showToast("\uC13C\uD130\uB97C \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.", "warning");
    return;
  }
  document.getElementById("modal-room-title").textContent = room ? "\uC804\uC0B0\uC2E4 \uC218\uC815" : "\uC804\uC0B0\uC2E4 \uB4F1\uB85D";
  document.getElementById("room-id").value = room?.id ?? "";
  document.getElementById("room-code").value = room?.room_code ?? "";
  document.getElementById("room-name").value = room?.room_name ?? "";
  document.getElementById("room-floor").value = room?.floor ?? "";
  document.getElementById("room-racks-per-row").value = room?.racks_per_row ?? 4;
  document.getElementById("room-active").value = String(room?.is_active ?? true);
  document.getElementById("room-note").value = room?.note ?? "";
  document.getElementById("modal-room").showModal();
}

function openRackModal(rack) {
  if (!_selectedRoomId) {
    showToast("\uC804\uC0B0\uC2E4\uC744 \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.", "warning");
    return;
  }
  document.getElementById("modal-rack-title").textContent = rack ? "\uB799 \uC218\uC815" : "\uB799 \uB4F1\uB85D";
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
    showToast("\uACE0\uAC1D\uC0AC\uB97C \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.", "warning");
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
    showToast("\uC13C\uD130\uBA85\uC740 \uD544\uC218\uC785\uB2C8\uB2E4.", "warning");
    return;
  }
  if (centerId) {
    await apiFetch("/api/v1/centers/" + centerId, { method: "PATCH", body: payload });
    showToast("\uC13C\uD130\uB97C \uC218\uC815\uD588\uC2B5\uB2C8\uB2E4.");
  } else {
    const created = await apiFetch("/api/v1/centers", { method: "POST", body: payload });
    _selectedCenterId = created.id;
    _selectedRoomId = null;
    showToast("\uC13C\uD130\uB97C \uB4F1\uB85D\uD588\uC2B5\uB2C8\uB2E4. \uAE30\uBCF8 \uC804\uC0B0\uC2E4 MAIN\uC774 \uD568\uAED8 \uC0DD\uC131\uB418\uC5C8\uC2B5\uB2C8\uB2E4.");
  }
  document.getElementById("modal-center").close();
  await loadTree();
}

async function saveRoom() {
  if (!_selectedCenterId) {
    showToast("\uC13C\uD130\uB97C \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.", "warning");
    return;
  }
  const roomId = document.getElementById("room-id").value;
  const payload = {
    center_id: _selectedCenterId,
    room_name: document.getElementById("room-name").value.trim(),
    floor: document.getElementById("room-floor").value.trim() || null,
    racks_per_row: Number(document.getElementById("room-racks-per-row").value) || null,
    is_active: document.getElementById("room-active").value === "true",
    note: document.getElementById("room-note").value.trim() || null,
  };
  if (!payload.room_name) {
    showToast("\uC804\uC0B0\uC2E4\uBA85\uC740 \uD544\uC218\uC785\uB2C8\uB2E4.", "warning");
    return;
  }
  if (roomId) {
    await apiFetch("/api/v1/rooms/" + roomId, { method: "PATCH", body: payload });
    showToast("\uC804\uC0B0\uC2E4\uC744 \uC218\uC815\uD588\uC2B5\uB2C8\uB2E4.");
  } else {
    const created = await apiFetch("/api/v1/centers/" + _selectedCenterId + "/rooms", { method: "POST", body: payload });
    _selectedRoomId = created.id;
    showToast("\uC804\uC0B0\uC2E4\uC744 \uB4F1\uB85D\uD588\uC2B5\uB2C8\uB2E4.");
  }
  document.getElementById("modal-room").close();
  await loadTree();
}

async function saveRack() {
  if (!_selectedRoomId) {
    showToast("\uC804\uC0B0\uC2E4\uC744 \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.", "warning");
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
    await apiFetch("/api/v1/racks/" + rackId, { method: "PATCH", body: payload });
    showToast("\uB799\uC744 \uC218\uC815\uD588\uC2B5\uB2C8\uB2E4.");
  } else {
    await apiFetch("/api/v1/rooms/" + _selectedRoomId + "/racks", { method: "POST", body: payload });
    showToast("\uB799\uC744 \uB4F1\uB85D\uD588\uC2B5\uB2C8\uB2E4.");
  }
  document.getElementById("modal-rack").close();
  await loadTree();
}

function deleteCenter(center) {
  confirmDelete("\uC13C\uD130 \u201C" + center.center_name + "\u201D\uC744(\uB97C) \uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?", async () => {
    try {
      await apiFetch("/api/v1/centers/" + center.id, { method: "DELETE" });
      if (_selectedCenterId === center.id) {
        _selectedCenterId = null;
        _selectedRoomId = null;
        _selectedNode = null;
      }
      showToast("\uC13C\uD130\uB97C \uC0AD\uC81C\uD588\uC2B5\uB2C8\uB2E4.");
      await loadTree();
      if (!_selectedNode) renderEmptyContent();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

function deleteRoom(room) {
  confirmDelete("\uC804\uC0B0\uC2E4 \u201C" + room.room_name + "\u201D\uC744(\uB97C) \uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?", async () => {
    try {
      await apiFetch("/api/v1/rooms/" + room.id, { method: "DELETE" });
      if (_selectedRoomId === room.id) {
        _selectedRoomId = null;
      }
      if (_selectedNode && _selectedNode.type === "room" && _selectedNode.id === room.id) {
        _selectedNode = null;
      }
      showToast("\uC804\uC0B0\uC2E4\uC744 \uC0AD\uC81C\uD588\uC2B5\uB2C8\uB2E4.");
      await loadTree();
      if (!_selectedNode) renderEmptyContent();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

function deleteRack(rack) {
  confirmDelete("\uB799 \u201C" + (rack.rack_name || rack.rack_code) + "\u201D\uC744(\uB97C) \uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C?", async () => {
    try {
      await apiFetch("/api/v1/racks/" + rack.id, { method: "DELETE" });
      if (_selectedNode && _selectedNode.type === "rack" && _selectedNode.id === rack.id) {
        _selectedNode = null;
      }
      showToast("\uB799\uC744 \uC0AD\uC81C\uD588\uC2B5\uB2C8\uB2E4.");
      await loadTree();
      if (!_selectedNode) renderEmptyContent();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

/* ── Splitter ── */

function initTreeSplitter() {
  const splitter = document.getElementById("layout-category-splitter");
  const layout = document.getElementById("layout-shell");
  if (!splitter || !layout) return;

  const storedWidth = Number(localStorage.getItem(LAYOUT_TREE_WIDTH_KEY) || 0);
  if (storedWidth >= 280 && storedWidth <= 520) {
    layout.style.setProperty("--catalog-category-width", storedWidth + "px");
  }

  let dragging = false;
  splitter.addEventListener("mousedown", (event) => {
    dragging = true;
    splitter.classList.add("is-dragging");
    event.preventDefault();
  });
  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    const width = Math.min(520, Math.max(280, event.clientX - rect.left));
    layout.style.setProperty("--catalog-category-width", width + "px");
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    const current = parseInt(getComputedStyle(layout).getPropertyValue("--catalog-category-width"), 10);
    if (!Number.isNaN(current)) {
      localStorage.setItem(LAYOUT_TREE_WIDTH_KEY, String(current));
    }
  });
}

/* ── Event Listeners ── */

document.addEventListener("DOMContentLoaded", () => {
  initTreeSplitter();
  loadTree().catch(err => showToast(err.message, "error"));
});

window.addEventListener("ctx-changed", () => {
  _selectedNode = null;
  _selectedCenterId = null;
  _selectedRoomId = null;
  _treeCollapsed.clear();
  loadTree().catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-add-center").addEventListener("click", () => openCenterModal());
document.getElementById("btn-add-room").addEventListener("click", () => openRoomModal());
document.getElementById("btn-add-rack").addEventListener("click", () => openRackModal());
document.getElementById("btn-cancel-center").addEventListener("click", () => document.getElementById("modal-center").close());
document.getElementById("btn-save-center").addEventListener("click", () => saveCenter().catch(err => showToast(err.message, "error")));
document.getElementById("btn-cancel-room").addEventListener("click", () => document.getElementById("modal-room").close());
document.getElementById("btn-save-room").addEventListener("click", () => saveRoom().catch(err => showToast(err.message, "error")));
document.getElementById("btn-cancel-rack").addEventListener("click", () => document.getElementById("modal-rack").close());
document.getElementById("btn-save-rack").addEventListener("click", () => saveRack().catch(err => showToast(err.message, "error")));
