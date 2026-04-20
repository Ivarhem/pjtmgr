/* ── Physical Layout: Tree + Content Panel ── */

const LAYOUT_TREE_WIDTH_KEY = "physicalLayout.treeWidth";
const LAYOUT_TREE_COLLAPSED_KEY = "physicalLayout.treeCollapsed";
const LAYOUT_AUTO_COLLAPSE_KEY = "physicalLayout.autoCollapse";
const LAYOUT_TREE_ACTION_MODE_KEY = "physicalLayout.treeActionMode";
const LAYOUT_ZOOM_KEY = "physicalLayout.zoom";
const LAYOUT_AXIS_KEY_PREFIX = "physicalLayout.axis.v2";
const LAYOUT_ORIENTATION_KEY_PREFIX = "physicalLayout.orientation.v2";
const LAYOUT_EXCLUDED_CELLS_KEY_PREFIX = "physicalLayout.excludedCells.v2";
const LAYOUT_LINE_TAGS_KEY_PREFIX = "physicalLayout.lineTags.v2";
const LAYOUT_NUMBER_RANGE_KEY_PREFIX = "physicalLayout.numberRange.v2";

let _centers = [];
let _rooms = {};      // centerId -> rooms[]
let _racks = {};       // roomId -> racks[]
let _rackLines = {};   // roomId -> rackLines[]
let _selectedNode = null; // { type, id, data }
let _selectedCenterId = null;
let _selectedRoomId = null;
let _treeCollapsed = new Set();
let _layoutAutoCollapse = localStorage.getItem(LAYOUT_AUTO_COLLAPSE_KEY) !== "0";
let _layoutTreeActionMode = localStorage.getItem(LAYOUT_TREE_ACTION_MODE_KEY) || "compact";
let _expandedTreeActions = new Set();
let _layoutTreeRetryTimer = null;
let _layoutTreeRetryCount = 0;
let _editMode = false;
let _codeDisplay = "rack_code"; // "rack_code" | "project_code" | "rack_position"
let _draggedRackId = null;
let _layoutZoom = Number(localStorage.getItem(LAYOUT_ZOOM_KEY) || 1);
let _selectedSlotKey = null;
let _selectedSlotContext = null;
let _rackCodeSuggestionLocked = false;
let _lineCreateMode = null;
let _lineCreateStart = null;
let _lineRepositionTarget = null;

function _getLinePositionLabel(lineName, position) {
  return `라인 ${lineName} / 위치 ${Number(position) + 1}`;
}

function _alphaIndex(label) {
  const s = (label || "").trim().toUpperCase();
  if (!/^[A-Z]+$/.test(s)) return null;
  let n = 0;
  for (const ch of s) n = n * 26 + (ch.charCodeAt(0) - 64);
  return n - 1;
}

function _alphaLabel(index) {
  let n = Number(index) + 1;
  if (!Number.isFinite(n) || n <= 0) return "A";
  let out = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    out = String.fromCharCode(65 + rem) + out;
    n = Math.floor((n - 1) / 26);
  }
  return out;
}

function getLineLabelByIndex(index, rackLines = []) {
  const idx = Number(index);
  if (!Number.isFinite(idx) || idx < 0) return "";
  const exact = (rackLines || []).find((line) => Number(line.col_index) === idx);
  const name = String(exact?.line_name || "").trim();
  if (name) return name;
  return _alphaLabel(idx);
}

function getPositionLabel(index) {
  const idx = Number(index);
  if (!Number.isFinite(idx) || idx < 0) return "";
  return String(idx + 1).padStart(2, "0");
}

function isUnassignedLine(line) {
  return Number(line?.col_index) === -1 && [line?.start_col, line?.start_row, line?.end_col, line?.end_row].every((v) => v == null);
}

function getLineCells(line, room) {
  const startCol = Number(line?.start_col);
  const startRow = Number(line?.start_row);
  const endCol = Number(line?.end_col);
  const endRow = Number(line?.end_row);
  if ([startCol, startRow, endCol, endRow].every(Number.isFinite)) {
    if (startCol === endCol) {
      const step = endRow >= startRow ? 1 : -1;
      return Array.from({ length: Math.abs(endRow - startRow) + 1 }, (_, idx) => ({
        col: startCol,
        row: startRow + (idx * step),
        position: idx,
      }));
    }
    if (startRow === endRow) {
      const step = endCol >= startCol ? 1 : -1;
      return Array.from({ length: Math.abs(endCol - startCol) + 1 }, (_, idx) => ({
        col: startCol + (idx * step),
        row: startRow,
        position: idx,
      }));
    }
  }
  const colIndex = Number(line?.col_index);
  const slotCount = Math.max(0, Number(line?.slot_count || room?.grid_rows || 0));
  if (Number.isFinite(colIndex) && colIndex >= 0 && slotCount > 0) {
    return Array.from({ length: slotCount }, (_, idx) => ({ col: colIndex, row: idx, position: idx }));
  }
  return [];
}

function buildRoomLineLayout(room, rackLines = []) {
  const byCoord = new Map();
  const byLineId = new Map();
  (rackLines || []).forEach((line) => {
    if (isUnassignedLine(line)) return;
    const cells = getLineCells(line, room).filter((cell) => (
      cell.col >= 0 && cell.col < (room.grid_cols || 0) && cell.row >= 0 && cell.row < (room.grid_rows || 0)
    ));
    byLineId.set(Number(line.id), cells);
    cells.forEach((cell) => {
      byCoord.set(`${cell.col}:${cell.row}`, { line, position: cell.position, col: cell.col, row: cell.row });
    });
  });
  return { byCoord, byLineId };
}

function suggestNextLineName(rackLines = []) {
  const used = (rackLines || [])
    .map((line) => _alphaIndex(String(line?.line_name || '').trim()))
    .filter((idx) => idx != null);
  if (!used.length) return 'A';
  return _alphaLabel(Math.max(...used) + 1);
}

function getRoomOrientation(roomId) {
  try {
    return localStorage.getItem(`${LAYOUT_ORIENTATION_KEY_PREFIX}.${roomId}`) || "vertical";
  } catch {
    return "vertical";
  }
}

function setRoomOrientation(roomId, orientation) {
  const nextOrientation = orientation === "horizontal" ? "horizontal" : "vertical";
  const prevOrientation = getRoomOrientation(roomId);
  if (prevOrientation === nextOrientation) {
    localStorage.setItem(`${LAYOUT_ORIENTATION_KEY_PREFIX}.${roomId}`, nextOrientation);
    _selectedSlotKey = null;
    _selectedSlotContext = null;
    return;
  }
  const axisState = getRoomAxisState(roomId);
  localStorage.setItem(`${LAYOUT_AXIS_KEY_PREFIX}.${roomId}`, JSON.stringify({
    x: axisState.y || {},
    y: axisState.x || {},
  }));
  const tags = getRoomLineTags(roomId);
  localStorage.setItem(`${LAYOUT_LINE_TAGS_KEY_PREFIX}.${roomId}`, JSON.stringify(tags));
  localStorage.setItem(`${LAYOUT_ORIENTATION_KEY_PREFIX}.${roomId}`, nextOrientation);
  _selectedSlotKey = null;
  _selectedSlotContext = null;
}

function getRoomAxisState(roomId) {
  try {
    const raw = localStorage.getItem(`${LAYOUT_AXIS_KEY_PREFIX}.${roomId}`);
    const parsed = raw ? JSON.parse(raw) : {};
    return {
      x: parsed.x && typeof parsed.x === "object" ? parsed.x : {},
      y: parsed.y && typeof parsed.y === "object" ? parsed.y : {},
    };
  } catch {
    return { x: {}, y: {} };
  }
}

function setRoomAxisValue(roomId, axis, index, value) {
  const state = getRoomAxisState(roomId);
  const bucket = axis === "y" ? state.y : state.x;
  const cleaned = String(value || "").trim();
  if (cleaned) bucket[String(index)] = cleaned;
  else delete bucket[String(index)];
  localStorage.setItem(`${LAYOUT_AXIS_KEY_PREFIX}.${roomId}`, JSON.stringify(state));
}

function getRoomLineTags(roomId) {
  try {
    const raw = localStorage.getItem(`${LAYOUT_LINE_TAGS_KEY_PREFIX}.${roomId}`);
    const parsed = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function setRoomLineTag(roomId, index, tag) {
  const state = getRoomLineTags(roomId);
  if (!tag || tag === "normal") delete state[String(index)];
  else state[String(index)] = tag;
  localStorage.setItem(`${LAYOUT_LINE_TAGS_KEY_PREFIX}.${roomId}`, JSON.stringify(state));
}

function cycleRoomLineTag(roomId, index) {
  const current = getRoomLineTags(roomId)[String(index)] || "normal";
  const order = ["normal", "start", "exclude", "end"];
  const next = order[(order.indexOf(current) + 1) % order.length];
  setRoomLineTag(roomId, index, next);
  return next;
}

function getRoomNumberRange(roomId) {
  try {
    const raw = localStorage.getItem(`${LAYOUT_NUMBER_RANGE_KEY_PREFIX}.${roomId}`);
    const parsed = raw ? JSON.parse(raw) : {};
    const start = Number(parsed.start ?? 1);
    const end = Number(parsed.end ?? 12);
    const width = Number(parsed.width ?? 2);
    return { start, end: Math.max(start, end), width: Math.max(1, width) };
  } catch {
    return { start: 1, end: 12, width: 2 };
  }
}

function setRoomNumberRange(roomId, range) {
  const next = {
    start: Number(range.start ?? 1) || 1,
    end: Number(range.end ?? 12) || 12,
    width: Number(range.width ?? 2) || 2,
  };
  if (next.end < next.start) next.end = next.start;
  localStorage.setItem(`${LAYOUT_NUMBER_RANGE_KEY_PREFIX}.${roomId}`, JSON.stringify(next));
}

function getLineAxisKey(roomId) {
  return getRoomOrientation(roomId) === "vertical" ? "x" : "y";
}

function getSequenceAxisKey(roomId) {
  return getLineAxisKey(roomId) === "x" ? "y" : "x";
}

function getSequenceTags(roomId) {
  return getRoomLineTags(roomId);
}

function getActiveSequenceIndices(roomId, totalCount) {
  const tags = getSequenceTags(roomId);
  const startIdx = Object.entries(tags).find(([, tag]) => tag === "start")?.[0];
  const endIdx = Object.entries(tags).find(([, tag]) => tag === "end")?.[0];
  const excludes = new Set(Object.entries(tags).filter(([, tag]) => tag === "exclude").map(([idx]) => Number(idx)));
  let active = Array.from({ length: totalCount }, (_, i) => i);
  if (startIdx != null && endIdx != null) {
    const lo = Math.min(Number(startIdx), Number(endIdx));
    const hi = Math.max(Number(startIdx), Number(endIdx));
    active = active.filter((idx) => idx >= lo && idx <= hi);
  }
  return active.filter((idx) => !excludes.has(idx));
}

function getSequenceTag(index, roomId) {
  return getSequenceTags(roomId)[String(index)] || "normal";
}

function getLineLabel(roomId, index, rackLines = [], { fallback = true } = {}) {
  const state = getRoomAxisState(roomId);
  const axisKey = getLineAxisKey(roomId);
  const user = String(state[axisKey]?.[String(index)] || "").trim();
  if (user) return user;
  if (!fallback) return "";
  return getLineLabelByIndex(index, rackLines);
}

function getNumberLabel(roomId, positionIndex, totalCount = null) {
  const range = getRoomNumberRange(roomId);
  const count = totalCount ?? Math.max(range.end, positionIndex + 1);
  const active = getActiveSequenceIndices(roomId, count);
  const ordinal = active.indexOf(Number(positionIndex));
  if (ordinal < 0) return "";
  const value = range.start + ordinal;
  if (value > range.end) return "";
  return String(value).padStart(range.width, "0");
}

function getActiveLineIndices(roomId, cols, rackLines = []) {
  const lineCount = getLineAxisKey(roomId) === "x" ? cols : (rackLines.length || cols);
  const labeled = [];
  for (let i = 0; i < lineCount; i++) {
    if (getLineLabel(roomId, i, rackLines, { fallback: true })) labeled.push(i);
  }
  return labeled;
}

function isLineActive(roomId, index, cols, rackLines = []) {
  return getActiveLineIndices(roomId, cols, rackLines).includes(Number(index));
}

function getLineTag(roomId, index) {
  return getSequenceTag(index, roomId);
}

function getLineTagLabel(tag) {
  if (tag === "start") return "시작";
  if (tag === "exclude") return "제외";
  if (tag === "end") return "종료";
  return "일반";
}

function getCrossCellKey({ lineIndex = 0, positionIndex = 0 } = {}) {
  return `${lineIndex}:${positionIndex}`;
}

function getRoomExcludedCells(roomId) {
  try {
    const raw = localStorage.getItem(`${LAYOUT_EXCLUDED_CELLS_KEY_PREFIX}.${roomId}`);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveRoomExcludedCells(roomId, keys) {
  localStorage.setItem(`${LAYOUT_EXCLUDED_CELLS_KEY_PREFIX}.${roomId}`, JSON.stringify([...new Set(keys)]));
}

function isCrossCellExcluded(roomId, context) {
  return getRoomExcludedCells(roomId).includes(getCrossCellKey(context));
}

function toggleCrossCellExcluded(roomId, context) {
  const key = getCrossCellKey(context);
  const keys = getRoomExcludedCells(roomId);
  const next = keys.includes(key) ? keys.filter((item) => item !== key) : [...keys, key];
  saveRoomExcludedCells(roomId, next);
}

async function placeRackAtContext(rackId, room, context) {
  if (!rackId) return;
  if (context.isExcluded) {
    showToast("제외된 칸에는 랙을 배치할 수 없습니다.", "warning");
    return;
  }
  const targetLineId = context.line?.id || null;
  if (!targetLineId) {
    showToast("라인을 먼저 배치한 뒤 랙을 놓아주세요.", "warning");
    return;
  }
  await apiFetch("/api/v1/racks/" + rackId, {
    method: "PATCH",
    body: { rack_line_id: Number(targetLineId), line_position: Number(context.position) },
  });
}

function getAxisSuggestedLabel(axis, index, rackLines = []) {
  if (axis === "x") return getLineLabelByIndex(index, rackLines);
  return getPositionLabel(index);
}

function axisHasAnyUserValue(roomId, axis) {
  const state = getRoomAxisState(roomId);
  const bucket = axis === "y" ? state.y : state.x;
  return Object.values(bucket || {}).some((value) => String(value || "").trim());
}

function formatLineCoordinates(line) {
  const startCol = Number(line?.start_col);
  const startRow = Number(line?.start_row);
  const endCol = Number(line?.end_col);
  const endRow = Number(line?.end_row);
  if ([startCol, startRow, endCol, endRow].every(Number.isFinite)) {
    return `(${startCol + 1}, ${startRow + 1}) → (${endCol + 1}, ${endRow + 1})`;
  }
  if (line?.col_index != null && Number(line.col_index) >= 0) {
    return `(${Number(line.col_index) + 1}, 1) → (${Number(line.col_index) + 1}, ${Number(line.slot_count || 1)})`;
  }
  return '미배치';
}

async function applyTwoPointLineToExisting(line, room, startCtx, endCtx) {
  const startCol = Number(startCtx.colIndex ?? startCtx.lineIndex);
  const startRow = Number(startCtx.rowIndex ?? startCtx.positionIndex);
  const endCol = Number(endCtx.colIndex ?? endCtx.lineIndex);
  const endRow = Number(endCtx.rowIndex ?? endCtx.positionIndex);
  const sameRow = startRow === endRow;
  const sameCol = startCol === endCol;
  if (!sameRow && !sameCol) {
    showToast('시작셀과 종료셀은 같은 행 또는 같은 열이어야 합니다.', 'warning');
    return false;
  }
  const direction = sameRow ? 'horizontal' : 'vertical';
  return await apiFetch('/api/v1/rack-lines/' + line.id, {
    method: 'PATCH',
    body: {
      line_name: line.line_name,
      prefix: line.prefix ?? null,
      col_index: Math.min(startCol, endCol),
      slot_count: (sameRow ? Math.abs(endCol - startCol) : Math.abs(endRow - startRow)) + 1,
      start_col: startCol,
      start_row: startRow,
      end_col: endCol,
      end_row: endRow,
      direction,
    },
  });
}

function openLineModal(line) {
  document.getElementById('modal-line-title').textContent = '라인 수정';
  document.getElementById('line-id').value = line?.id ?? '';
  document.getElementById('line-room-id').value = line?.room_id ?? '';
  document.getElementById('line-code').value = line?.prefix ?? '';
  document.getElementById('line-name').value = line?.line_name ?? '';
  document.getElementById('line-coordinates').value = formatLineCoordinates(line);
  document.getElementById('modal-line').showModal();
}

async function saveLineModal() {
  const lineId = document.getElementById('line-id').value;
  if (!lineId) return;
  const payload = {
    prefix: document.getElementById('line-code').value.trim() || null,
    line_name: document.getElementById('line-name').value.trim(),
  };
  if (!payload.line_name) {
    showToast('라인명은 필수입니다.', 'warning');
    return;
  }
  await apiFetch('/api/v1/rack-lines/' + lineId, { method: 'PATCH', body: payload });
  document.getElementById('modal-line').close();
  showToast('라인 정보를 저장했습니다.');
  await loadTree();
  const roomId = Number(document.getElementById('line-room-id').value || 0);
  const content = document.getElementById('layout-content');
  if (content && roomId) {
    content.textContent = '';
    const roomData = _findRoomData(roomId);
    if (roomData) renderRoomView(content, roomData);
  }
}

function beginLineReposition(line) {
  const roomId = Number(line?.room_id || 0);
  if (!roomId) return;
  document.getElementById('modal-line').close();
  _selectedRoomId = roomId;
  _lineRepositionTarget = line;
  _lineCreateMode = { roomId, mode: 'reposition', lineId: line.id };
  _lineCreateStart = null;
  const content = document.getElementById('layout-content');
  if (content) {
    content.textContent = '';
    const roomData = _findRoomData(roomId);
    if (roomData) renderRoomView(content, roomData);
  }
}

function resetLineCreateMode() {
  _lineCreateMode = null;
  _lineCreateStart = null;
  _lineRepositionTarget = null;
}

function beginLineCreate(roomId) {
  _lineCreateMode = { roomId };
  _lineCreateStart = null;
}

async function applyTwoPointLine(room, startCtx, endCtx) {
  if (!startCtx || !endCtx) return;
  const startCol = Number(startCtx.colIndex ?? startCtx.lineIndex);
  const startRow = Number(startCtx.rowIndex ?? startCtx.positionIndex);
  const endCol = Number(endCtx.colIndex ?? endCtx.lineIndex);
  const endRow = Number(endCtx.rowIndex ?? endCtx.positionIndex);
  const sameRow = startRow === endRow;
  const sameCol = startCol === endCol;
  if (!sameRow && !sameCol) {
    showToast("시작셀과 종료셀은 같은 행 또는 같은 열이어야 합니다.", "warning");
    return false;
  }

  const rackLines = await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines");
  const suggestedName = suggestNextLineName(rackLines.filter((line) => !isUnassignedLine(line)));
  const lineName = (prompt("라인명을 입력하세요", suggestedName) || suggestedName || "").trim();
  if (!lineName) return false;

  const direction = sameRow ? "horizontal" : "vertical";
  const targetLine = await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines", {
    method: "POST",
    body: {
      line_name: lineName,
      col_index: Math.min(startCol, endCol),
      slot_count: (sameRow ? Math.abs(endCol - startCol) : Math.abs(endRow - startRow)) + 1,
      start_col: startCol,
      start_row: startRow,
      end_col: endCol,
      end_row: endRow,
      direction,
      prefix: null,
    },
  });

  return { line: targetLine, direction, startCol, startRow, endCol, endRow };
}

function getSlotDefaultCode({ line = null, lineName = "", positionIndex = 0 } = {}) {
  const effectiveLineName = (line?.line_name || lineName || "").trim();
  if (!effectiveLineName) return "";
  return `${effectiveLineName}-${String(Number(positionIndex) + 1).padStart(2, "0")}`;
}

function suggestLineNameForColumn(colIndex, rackLines = []) {
  const sorted = [...rackLines].sort((a, b) => (a.col_index || 0) - (b.col_index || 0));
  const left = [...sorted].filter((line) => (line.col_index || 0) < colIndex).pop();
  const right = sorted.find((line) => (line.col_index || 0) > colIndex);
  const leftIdx = left ? _alphaIndex(left.line_name) : null;
  const rightIdx = right ? _alphaIndex(right.line_name) : null;
  if (leftIdx != null) return _alphaLabel(leftIdx + 1);
  if (rightIdx != null && rightIdx > 0) return _alphaLabel(rightIdx - 1);
  return _alphaLabel(colIndex);
}

function suggestRackCode(lineName, position, rowLabel = null) {
  const cleanLine = (lineName || "").trim().toUpperCase();
  const pos = String(rowLabel || Number(position) + 1).padStart(2, "0");
  return cleanLine ? `${cleanLine}-${pos}` : `RACK-${pos}`;
}

function applySuggestedRackCode({ force = false } = {}) {
  const input = document.getElementById("rack-code");
  if (!input) return;
  if (_rackCodeSuggestionLocked && !force) return;
  const ctx = _selectedSlotContext;
  if (!ctx?.line) return;
  input.value = getSlotDefaultCode({ line: ctx.line, lineName: ctx.line?.line_name, positionIndex: ctx.position }) || suggestRackCode(ctx.line.line_name, ctx.position);
}

function clampLayoutZoom(value) {
  return Math.min(1.5, Math.max(0.7, Number(value) || 1));
}

function setLayoutZoom(value, { persist = true } = {}) {
  _layoutZoom = clampLayoutZoom(value);
  if (persist) localStorage.setItem(LAYOUT_ZOOM_KEY, String(_layoutZoom));
}

function getZoomPercentLabel() {
  return `${Math.round(_layoutZoom * 100)}%`;
}

function applyPhysicalLayoutResponsiveSizing() {
  const shell = document.getElementById("layout-shell");
  if (shell) {
    const shellTop = shell.getBoundingClientRect().top;
    const availableShellHeight = Math.max(360, window.innerHeight - shellTop - 16);
    shell.style.height = `${availableShellHeight}px`;
  }
  document.querySelectorAll(".floor-plan-viewport").forEach((viewport) => {
    const viewportTop = viewport.getBoundingClientRect().top;
    const availableViewportHeight = Math.max(240, window.innerHeight - viewportTop - 20);
    viewport.style.maxHeight = `${availableViewportHeight}px`;
  });
}

function enableFloorPlanPanning(viewport) {
  if (!viewport || viewport.dataset.panningBound === "1") return;
  viewport.dataset.panningBound = "1";
  let active = false;
  let startX = 0;
  let startY = 0;
  let scrollLeft = 0;
  let scrollTop = 0;
  viewport.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    active = true;
    startX = event.clientX;
    startY = event.clientY;
    scrollLeft = viewport.scrollLeft;
    scrollTop = viewport.scrollTop;
    viewport.classList.add("is-panning");
  });
  const stop = () => {
    active = false;
    viewport.classList.remove("is-panning");
  };
  viewport.addEventListener("pointermove", (event) => {
    if (!active) return;
    viewport.scrollLeft = scrollLeft - (event.clientX - startX);
    viewport.scrollTop = scrollTop - (event.clientY - startY);
  });
  viewport.addEventListener("pointerup", stop);
  viewport.addEventListener("pointercancel", stop);
  viewport.addEventListener("pointerleave", stop);
}

function _setSlotStatus(statusEl, message, emphasis = "") {
  if (!statusEl) return;
  statusEl.innerHTML = "";
  if (emphasis) {
    const strong = document.createElement("strong");
    strong.textContent = emphasis;
    statusEl.appendChild(strong);
    statusEl.appendChild(document.createTextNode(" "));
  }
  statusEl.appendChild(document.createTextNode(message));
}


/* ── Data Loading ── */

async function getEffectiveLayoutPartnerId() {
  const direct = getCtxPartnerId();
  if (direct) return direct;
  try {
    const res = await fetch(withRootPath('/api/v1/preferences/infra.pinned_partner_id'));
    if (res.ok) {
      const pref = await res.json();
      if (pref?.value) return pref.value;
    }
  } catch {
    // ignore fallback errors
  }
  return null;
}

function scheduleLayoutTreeRetry() {
  if (_layoutTreeRetryTimer || _layoutTreeRetryCount >= 8) return;
  _layoutTreeRetryCount += 1;
  _layoutTreeRetryTimer = setTimeout(() => {
    _layoutTreeRetryTimer = null;
    loadTree()
      .then(() => loadLabelBaseSetting())
      .catch(() => {});
  }, 300 * _layoutTreeRetryCount);
}

async function loadTree() {
  const cid = await getEffectiveLayoutPartnerId();
  if (!cid) {
    _centers = [];
    _rooms = {};
    _racks = {};
    _rackLines = {};
    _selectedNode = null;
    _selectedCenterId = null;
    _selectedRoomId = null;
    renderEmptyTree();
    renderEmptyContent();
    syncButtons();
    scheduleLayoutTreeRetry();
    return;
  }

  _layoutTreeRetryCount = 0;
  if (_layoutTreeRetryTimer) {
    clearTimeout(_layoutTreeRetryTimer);
    _layoutTreeRetryTimer = null;
  }

  _centers = await apiFetch("/api/v1/centers?partner_id=" + cid);
  _rooms = {};
  _racks = {};
  _rackLines = {};

  for (const center of _centers) {
    const rooms = await apiFetch("/api/v1/centers/" + center.id + "/rooms");
    _rooms[center.id] = rooms;
    for (const room of rooms) {
      const racks = await apiFetch("/api/v1/rooms/" + room.id + "/racks");
      _racks[room.id] = racks;
      try {
        _rackLines[room.id] = await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines");
      } catch {
        _rackLines[room.id] = [];
      }
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
      return;
    }
    _selectedNode = null;
    _selectedCenterId = null;
    _selectedRoomId = null;
  }

  const preferred = getPreferredDefaultNode();
  if (preferred) {
    selectNode(preferred.type, preferred.id, preferred.data);
  } else {
    renderEmptyContent();
  }
}

function getPreferredDefaultNode() {
  const mainCenter = _centers.find((center) => center.is_main) || null;
  const firstCenter = _centers[0] || null;
  const targetCenter = mainCenter || firstCenter;
  if (!targetCenter) return null;
  const rooms = _rooms[targetCenter.id] || [];
  const mainRoom = rooms.find((room) => room.is_main) || null;
  const firstRoom = rooms[0] || null;
  if (mainRoom) return { type: "room", id: mainRoom.id, data: mainRoom };
  if (firstRoom) return { type: "room", id: firstRoom.id, data: firstRoom };
  return { type: "center", id: targetCenter.id, data: targetCenter };
}

function getNodeBranchInfo(nodeType, nodeId, nodeData) {
  if (nodeType === "center") {
    return { centerId: Number(nodeId), roomId: null, lineId: null, rackId: null };
  }
  if (nodeType === "floor") {
    return { centerId: Number(nodeData?.center?.id || 0) || null, roomId: null, lineId: null, rackId: null };
  }
  if (nodeType === "room") {
    return { centerId: Number(nodeData?.center_id || 0) || null, roomId: Number(nodeId), lineId: null, rackId: null };
  }
  if (nodeType === "line") {
    const roomId = Number(nodeData?.room_id || 0) || null;
    let centerId = null;
    if (roomId) {
      for (const [cid, rooms] of Object.entries(_rooms)) {
        if ((rooms || []).some((room) => Number(room.id) === roomId)) {
          centerId = Number(cid);
          break;
        }
      }
    }
    return { centerId, roomId, lineId: nodeData?.is_unassigned ? `unassigned-${roomId}` : String(nodeData?.id ?? nodeId), rackId: null };
  }
  if (nodeType === "rack") {
    const roomId = Number(nodeData?.room_id || 0) || null;
    let centerId = null;
    if (roomId) {
      for (const [cid, rooms] of Object.entries(_rooms)) {
        if ((rooms || []).some((room) => Number(room.id) === roomId)) {
          centerId = Number(cid);
          break;
        }
      }
    }
    const lineId = nodeData?.rack_line_id != null ? String(nodeData.rack_line_id) : `unassigned-${roomId}`;
    return { centerId, roomId, lineId, rackId: Number(nodeId) };
  }
  return { centerId: null, roomId: null, lineId: null, rackId: null };
}

function isNodeWithinSelectedBranch(nodeType, nodeId, nodeData) {
  if (!_selectedNode) return true;
  const selected = getNodeBranchInfo(_selectedNode.type, _selectedNode.id, _selectedNode.data || _selectedNode);
  const current = getNodeBranchInfo(nodeType, nodeId, nodeData);
  if (!selected.centerId || !current.centerId) return true;
  if (current.centerId !== selected.centerId) return false;
  if (!selected.roomId) return true;
  if (!current.roomId) return true;
  if (current.roomId !== selected.roomId) return false;
  if (!selected.lineId) return true;
  if (!current.lineId) return true;
  if (String(current.lineId) !== String(selected.lineId)) return false;
  if (!selected.rackId) return true;
  if (!current.rackId) return true;
  return Number(current.rackId) === Number(selected.rackId);
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
  if (type === "line") {
    for (const lines of Object.values(_rackLines)) {
      const line = lines.find(line => String(line.id) === String(id));
      if (line) return line;
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

function updateLayoutTreeModeBtn() {
  const btn = document.getElementById("btn-layout-tree-mode");
  if (!btn) return;
  const detail = _layoutTreeActionMode === "detail";
  btn.textContent = detail ? "간단히" : "자세히";
  btn.className = "btn btn-secondary btn-sm" + (detail ? " is-active" : "");
  btn.title = detail ? "모든 노드 액션 항상 표시" : "노드별 작은 아이콘으로 액션 표시";
}

function isTreeActionExpanded(key) {
  return _layoutTreeActionMode === "detail" || _expandedTreeActions.has(key);
}

function toggleTreeActionMenu(key) {
  if (_layoutTreeActionMode === "detail") return;
  const isOpen = _expandedTreeActions.has(key);
  _expandedTreeActions.clear();
  if (!isOpen) _expandedTreeActions.add(key);
  renderTree();
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

  const makeRackNode = (rack) => createTreeNode({
    key: "rack-" + rack.id,
    icon: "💽",
    label: rack.rack_name || rack.rack_code,
    meta: rack.total_units + "U",
    nodeType: "rack",
    nodeId: rack.id,
    nodeData: rack,
    hasChildren: false,
    collapsed: false,
    childUl: null,
  });

  const makeRoomChildUl = (room, racks) => {
    const roomChildUl = document.createElement("ul");
    const roomLines = (_rackLines[room.id] || []).filter((line) => !isUnassignedLine(line)).sort((a, b) => String(a.line_name || "").localeCompare(String(b.line_name || "")));
    const unassignedRacks = racks.filter(rack => !rack.rack_line_id);
    const unassignedUl = document.createElement("ul");
    unassignedRacks.forEach(rack => unassignedUl.appendChild(makeRackNode(rack)));

    roomLines.forEach(line => {
      const lineRacks = racks.filter(rack => Number(rack.rack_line_id) === Number(line.id));
      const lineUl = document.createElement("ul");
      lineRacks.forEach(rack => lineUl.appendChild(makeRackNode(rack)));
      roomChildUl.appendChild(createTreeNode({
        key: "line-" + line.id,
        icon: "📏",
        label: line.line_name,
        meta: lineRacks.length + " 랙",
        nodeType: "line",
        nodeId: line.id,
        nodeData: line,
        hasChildren: lineRacks.length > 0,
        collapsed: _treeCollapsed.has("line-" + line.id),
        childUl: lineUl,
      }));
    });

    roomChildUl.appendChild(createTreeNode({
      key: "line-unassigned-" + room.id,
      icon: "🗂️",
      label: "미할당",
      meta: unassignedRacks.length + " 랙",
      nodeType: "line",
      nodeId: "unassigned-" + room.id,
      nodeData: { id: "unassigned-" + room.id, room_id: room.id, line_name: "미할당", is_unassigned: true },
      hasChildren: unassignedRacks.length > 0,
      collapsed: _treeCollapsed.has("line-unassigned-" + room.id),
      childUl: unassignedUl,
    }));

    return roomChildUl;
  };

  const rootUl = document.createElement("ul");
  rootUl.className = "classification-tree-root";

  _centers.forEach(center => {
    const rooms = _rooms[center.id] || [];
    const centerKey = "center-" + center.id;
    const centerCollapsed = _treeCollapsed.has(centerKey);

    const floorMap = {};
    rooms.forEach(room => {
      const floor = room.floor || "기본층";
      if (!floorMap[floor]) floorMap[floor] = [];
      floorMap[floor].push(room);
    });
    const floorKeys = Object.keys(floorMap).sort((a, b) => a.localeCompare(b, "ko-KR"));
    const centerChildUl = document.createElement("ul");

    floorKeys.forEach(floor => {
      const floorRooms = floorMap[floor];
      const floorKey = "floor-" + center.id + "-" + floor;
      const floorCollapsed = _treeCollapsed.has(floorKey);
      const floorChildUl = document.createElement("ul");

      floorRooms.forEach(room => {
        const racks = _racks[room.id] || [];
        const roomKey = "room-" + room.id;
        const roomCollapsed = _treeCollapsed.has(roomKey);
        const roomChildUl = makeRoomChildUl(room, racks);
        floorChildUl.appendChild(createTreeNode({
          key: roomKey,
          icon: "🚪",
          label: room.room_name,
          meta: racks.length + " 랙",
          nodeType: "room",
          nodeId: room.id,
          nodeData: room,
          hasChildren: true,
          collapsed: roomCollapsed,
          childUl: roomChildUl,
        }));
      });

      if (floorKeys.length > 1) {
        centerChildUl.appendChild(createTreeNode({
          key: floorKey,
          icon: "",
          label: floor,
          meta: floorRooms.length + " 실",
          nodeType: "floor",
          nodeId: center.id + "-" + floor,
          nodeData: { center, floor, rooms: floorRooms },
          hasChildren: floorRooms.length > 0,
          collapsed: floorCollapsed,
          childUl: floorChildUl,
        }));
      } else {
        Array.from(floorChildUl.children).forEach(child => centerChildUl.appendChild(child));
      }
    });

    const totalRacks = rooms.reduce((sum, r) => sum + (_racks[r.id] || []).length, 0);
    rootUl.appendChild(createTreeNode({
      key: centerKey,
      icon: "📍",
      label: center.center_name,
      meta: rooms.length + " 실 / " + totalRacks + " 랙",
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
  nodeDiv.className = `classification-tree-node classification-tree-node-${nodeType}`;
  nodeDiv.setAttribute("data-node-type", nodeType);
  nodeDiv.setAttribute("data-node-id", String(nodeId));

  // Mark active / branch focus
  if (_selectedNode && _selectedNode.type === nodeType && String(_selectedNode.id) === String(nodeId)) {
    nodeDiv.classList.add("is-selected");
  }
  if (!isNodeWithinSelectedBranch(nodeType, nodeId, nodeData)) {
    nodeDiv.classList.add("is-branch-muted");
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
  nameSpan.textContent = label;

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
  const hasInlineActions = nodeType === "center" || nodeType === "room" || nodeType === "line" || nodeType === "rack";
  const actions = document.createElement("div");
  actions.className = "layout-tree-node-actions";
  const actionsOpen = isTreeActionExpanded(key);
  const addAction = (label, onClick) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn btn-secondary btn-sm layout-tree-node-action";
    if (label === "삭제") b.classList.add("is-delete-action");
    b.textContent = label;
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      onClick();
    });
    actions.appendChild(b);
  };
  if (nodeType === "center") {
    addAction("전산실 추가", () => { _selectedCenterId = nodeId; openRoomModal(); });
    addAction("수정", () => openCenterModal(nodeData));
    addAction("삭제", () => deleteCenter(nodeData));
  } else if (nodeType === "room") {
    addAction("라인 추가", () => { _selectedRoomId = nodeId; beginLineCreate(nodeId); selectNode("room", nodeId, nodeData); });
    addAction("수정", () => openRoomModal(nodeData));
    addAction("삭제", () => deleteRoom(nodeData));
  } else if (nodeType === "line") {
    if (nodeData?.is_unassigned) {
      addAction("랙 추가", async () => { _selectedRoomId = nodeData.room_id; _selectedSlotContext = null; await openRackModal(); });
    } else {
      addAction("랙 추가", async () => {
        _selectedRoomId = nodeData.room_id;
        const room = _findRoomData(nodeData.room_id);
        const nextPos = getFirstEmptyLinePosition(nodeData, _racks[nodeData.room_id] || [], room);
        _selectedSlotContext = { line: nodeData, position: nextPos, room, rackLines: _rackLines[nodeData.room_id] || [] };
        await openRackModal();
      });
      addAction("수정", () => openLineModal(nodeData));
      addAction("삭제", async () => {
        if (!confirm(`라인 '${nodeData.line_name}'을(를) 삭제하시겠습니까? 배치된 랙은 미배치 상태로 전환됩니다.`)) return;
        try {
          await apiFetch("/api/v1/rack-lines/" + nodeData.id, { method: "DELETE" });
          showToast("라인을 삭제했습니다.");
          await loadTree();
          const content = document.getElementById("layout-content");
          if (content) {
            content.textContent = "";
            const roomData = _findRoomData(nodeData.room_id);
            if (roomData) renderRoomView(content, roomData);
          }
        } catch (err) {
          showToast(err.message, "error");
        }
      });
    }
  } else if (nodeType === "rack") {
    addAction("수정", () => openRackModal(nodeData));
    addAction("삭제", () => deleteRack(nodeData));
  }
  if (_layoutTreeActionMode === "detail") {
    actions.classList.add("is-visible", "is-detail-mode");
    nodeDiv.appendChild(actions);
  } else if (hasInlineActions) {
    const actionWrap = document.createElement("div");
    actionWrap.className = "layout-tree-node-action-wrap";
    if (actionsOpen) actions.classList.add("is-visible");
    actionWrap.appendChild(actions);

    const actionToggle = document.createElement("button");
    actionToggle.type = "button";
    actionToggle.className = "btn btn-icon btn-sm layout-tree-node-toggle";
    actionToggle.title = actionsOpen ? "노드 작업 닫기" : "노드 작업 열기";
    actionToggle.setAttribute("aria-expanded", actionsOpen ? "true" : "false");
    actionToggle.textContent = actionsOpen ? ">" : "<";
    actionToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleTreeActionMenu(key);
    });
    actionWrap.appendChild(actionToggle);
    nodeDiv.appendChild(actionWrap);
  }
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

function setLayoutTreeCollapsed(collapsed) {
  const shell = document.getElementById("layout-shell");
  const treePanel = document.getElementById("layout-tree-panel");
  const splitter = document.getElementById("layout-category-splitter");
  const content = document.getElementById("layout-content");
  const toggleBtn = document.getElementById("btn-toggle-layout-tree");
  if (!shell) return;
  shell.classList.toggle("layout-tree-collapsed", !!collapsed);
  if (treePanel) treePanel.style.display = collapsed ? "none" : "flex";
  if (splitter) splitter.style.display = collapsed ? "none" : "block";
  if (content) content.style.width = collapsed ? "100%" : "";
  if (toggleBtn) toggleBtn.textContent = collapsed ? "❯" : "❮";
  localStorage.setItem(LAYOUT_TREE_COLLAPSED_KEY, collapsed ? "1" : "0");
}

function restoreLayoutTreeCollapsed() {
  const collapsed = window.innerWidth <= 960 && localStorage.getItem(LAYOUT_TREE_COLLAPSED_KEY) === "1";
  setLayoutTreeCollapsed(collapsed);
}

function updateLayoutAutoCollapseBtn() {
  const btn = document.getElementById("btn-layout-auto-collapse");
  if (!btn) return;
  btn.classList.toggle("active", _layoutAutoCollapse);
  btn.title = _layoutAutoCollapse ? "선택 시 목록 자동 접기 (켜짐)" : "선택 시 목록 자동 접기 (꺼짐)";
  btn.setAttribute("aria-label", btn.title);
}

function focusLayoutDetailPanel() {
  if (!_layoutAutoCollapse || window.innerWidth <= 960) return;
  setLayoutTreeCollapsed(true);
}

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
  } else if (type === "line") {
    _selectedRoomId = data.room_id;
    for (const [centerId, rooms] of Object.entries(_rooms)) {
      if (rooms.some(r => r.id === data.room_id)) {
        _selectedCenterId = Number(centerId);
        break;
      }
    }
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
  else if (type === "line") renderRoomView(content, _findRoomData(data.room_id) || data);
  else if (type === "rack") renderRackView(content, data);
  focusLayoutDetailPanel();
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
  requestAnimationFrame(() => applyPhysicalLayoutResponsiveSizing());
}

function syncButtons() {
  const addRoomBtn = document.getElementById("btn-add-room");
  const addRackBtn = document.getElementById("btn-add-rack");
  if (addRoomBtn) addRoomBtn.disabled = !_selectedCenterId;
  if (addRackBtn) addRackBtn.disabled = !_selectedRoomId;
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
    "\uD83D\uDCCD", center.center_name
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

async function renderRoomView(container, room) {
  const wrapper = document.createElement("div");
  wrapper.style.cssText = "padding:20px;overflow:auto;width:100%;";
  container.appendChild(wrapper);

  const header = document.createElement("div");
  header.className = "layout-view-header";
  const h3 = document.createElement("h3");
  h3.textContent = room.room_name + (room.floor ? " (" + room.floor + ")" : "");
  header.appendChild(h3);

  const headerActions = document.createElement("div");
  headerActions.className = "infra-inline-actions";

  const btnToggleEdit = document.createElement("button");
  btnToggleEdit.className = "btn btn-sm " + (_editMode ? "btn-primary" : "btn-secondary");
  btnToggleEdit.textContent = _editMode ? "편집 완료" : "편집 모드";
  btnToggleEdit.addEventListener("click", () => {
    _editMode = !_editMode;
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRoomView(content, room);
  });
  headerActions.appendChild(btnToggleEdit);

  const codeLabel = document.createElement("label");
  codeLabel.className = "layout-inline-select";
  codeLabel.textContent = "명칭";
  const codeSelect = document.createElement("select");
  [
    { value: "rack_code", label: "랙코드" },
    { value: "project_code", label: "프로젝트코드" },
    { value: "rack_position", label: "랙좌표" },
  ].forEach((opt) => {
    const o = document.createElement("option");
    o.value = opt.value;
    o.textContent = opt.label;
    if (opt.value === _codeDisplay) o.selected = true;
    codeSelect.appendChild(o);
  });
  codeSelect.addEventListener("change", () => {
    _codeDisplay = codeSelect.value;
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRoomView(content, room);
  });
  codeLabel.appendChild(codeSelect);
  headerActions.appendChild(codeLabel);

  const zoomWrap = document.createElement("div");
  zoomWrap.className = "floor-plan-zoom-group";
  const btnZoomOut = document.createElement("button");
  btnZoomOut.className = "btn btn-secondary btn-sm";
  btnZoomOut.textContent = "－";
  const zoomLabel = document.createElement("span");
  zoomLabel.className = "floor-plan-zoom-label";
  zoomLabel.textContent = getZoomPercentLabel();
  const btnZoomIn = document.createElement("button");
  btnZoomIn.className = "btn btn-secondary btn-sm";
  btnZoomIn.textContent = "＋";
  btnZoomOut.addEventListener("click", () => {
    setLayoutZoom(_layoutZoom - 0.1);
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRoomView(content, room);
  });
  btnZoomIn.addEventListener("click", () => {
    setLayoutZoom(_layoutZoom + 0.1);
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRoomView(content, room);
  });
  zoomWrap.appendChild(btnZoomOut);
  zoomWrap.appendChild(zoomLabel);
  zoomWrap.appendChild(btnZoomIn);
  headerActions.appendChild(zoomWrap);
  header.appendChild(headerActions);
  wrapper.appendChild(header);

  const slotStatus = document.createElement("div");
  slotStatus.className = "floor-plan-slot-status";
  _setSlotStatus(slotStatus, _lineCreateMode?.roomId === room.id ? (_lineCreateMode?.mode === "reposition" ? "좌표재설정 모드입니다. 시작셀과 종료셀을 차례로 클릭하세요." : "라인 추가 모드입니다. 시작셀과 종료셀을 차례로 클릭하세요.") : "라인은 가로/세로 직선으로 배치됩니다. 라인 추가 후 슬롯에 랙을 배치하세요.", "안내");
  const slotActions = document.createElement("div");
  slotActions.className = "infra-inline-actions";
  slotActions.style.marginBottom = "12px";

  let rackLines = [];
  try {
    rackLines = await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines");
  } catch {
    rackLines = [];
  }
  const placedLines = rackLines.filter((line) => !isUnassignedLine(line));
  const layout = buildRoomLineLayout(room, placedLines);
  const allRacks = _racks[room.id] || [];
  const cols = room.grid_cols || 10;
  const rows = room.grid_rows || 12;

  const rackByPos = {};
  placedLines.forEach((line) => {
    (line.racks || []).forEach((rack) => {
      if (rack.line_position != null) rackByPos[`${line.id}:${rack.line_position}`] = rack;
    });
  });
  const placedRackIds = new Set();
  placedLines.forEach((line) => (line.racks || []).forEach((rack) => placedRackIds.add(rack.id)));
  const unplacedRacks = allRacks.filter((rack) => !placedRackIds.has(rack.id));

  const renderSlotActions = () => {
    slotActions.textContent = "";
    const ctx = _selectedSlotContext;
    if (!ctx) return;
    if (ctx.line && _editMode) {
      const btnToggleSlot = document.createElement("button");
      btnToggleSlot.className = "btn btn-secondary btn-sm";
      btnToggleSlot.textContent = ctx.isDisabled ? "제외 해제" : "칸 제외";
      btnToggleSlot.addEventListener("click", () => _toggleDisabledSlot(ctx.line, ctx.position, room));
      slotActions.appendChild(btnToggleSlot);
    }
    if (ctx.line && !ctx.rack && !ctx.isDisabled) {
      const btnAddRackHere = document.createElement("button");
      btnAddRackHere.className = "btn btn-primary btn-sm";
      btnAddRackHere.textContent = "여기에 랙 추가";
      btnAddRackHere.addEventListener("click", () => openRackModal());
      slotActions.appendChild(btnAddRackHere);
    }
    if (!ctx.line && !_lineCreateMode) {
      const hint = document.createElement("span");
      hint.className = "text-muted";
      hint.style.fontSize = "12px";
      hint.textContent = "빈 칸은 트리의 라인 추가 후 배치에 사용됩니다.";
      slotActions.appendChild(hint);
    }
  };

  const info = document.createElement("div");
  info.className = "layout-view-info";
  info.textContent = `랙 ${allRacks.length}개 | 배치 ${placedRackIds.size} | 미배치 ${unplacedRacks.length} | 격자 ${cols}×${rows} | 라인 ${placedLines.length}`;
  wrapper.appendChild(info);

  const floorPlanShell = document.createElement("div");
  floorPlanShell.className = "floor-plan-shell";
  wrapper.appendChild(floorPlanShell);

  const floorPlanMain = document.createElement("div");
  floorPlanMain.className = "floor-plan-main";
  floorPlanShell.appendChild(floorPlanMain);

  const floorPlanSide = document.createElement("aside");
  floorPlanSide.className = "floor-plan-side";
  floorPlanShell.appendChild(floorPlanSide);

  const viewport = document.createElement("div");
  viewport.className = "floor-plan-viewport";
  viewport.style.minHeight = "360px";
  floorPlanMain.appendChild(viewport);
  enableFloorPlanPanning(viewport);
  requestAnimationFrame(() => applyPhysicalLayoutResponsiveSizing());

  const canvas = document.createElement("div");
  canvas.className = "floor-plan-canvas";
  viewport.appendChild(canvas);

  const grid = document.createElement("div");
  grid.className = "floor-plan-grid";
  const cellWidth = Math.round(64 * _layoutZoom);
  const cellHeight = Math.round(40 * _layoutZoom);
  const rowLabelWidth = Math.max(24, Math.round(28 * _layoutZoom));
  grid.style.setProperty("--floor-cell-width", cellWidth + "px");
  grid.style.setProperty("--floor-cell-height", cellHeight + "px");
  grid.style.setProperty("--floor-row-label-width", rowLabelWidth + "px");
  grid.style.setProperty("--floor-cell-font-size", Math.max(9, Math.round(11 * _layoutZoom)) + "px");
  grid.style.setProperty("--floor-header-font-size", Math.max(9, Math.round(11 * _layoutZoom)) + "px");
  grid.style.setProperty("--floor-row-label-font-size", Math.max(8, Math.round(10 * _layoutZoom)) + "px");
  grid.style.gridTemplateColumns = rowLabelWidth + "px repeat(" + cols + ", " + cellWidth + "px) " + rowLabelWidth + "px";
  canvas.appendChild(grid);

  const corner = document.createElement("div");
  corner.className = "floor-plan-row-label floor-plan-axis-corner";
  corner.textContent = "좌표";
  grid.appendChild(corner);

  for (let c = 0; c < cols; c++) {
    const headerCell = document.createElement("div");
    headerCell.className = "floor-plan-header floor-plan-axis-header";
    headerCell.textContent = String(c + 1);
    grid.appendChild(headerCell);
  }
  const topRightFrame = document.createElement("div");
  topRightFrame.className = "floor-plan-row-label floor-plan-axis-frame";
  topRightFrame.setAttribute("aria-hidden", "true");
  grid.appendChild(topRightFrame);

  for (let r = 0; r < rows; r++) {
    const rowLabel = document.createElement("div");
    rowLabel.className = "floor-plan-row-label floor-plan-axis-row";
    rowLabel.textContent = String(r + 1);
    grid.appendChild(rowLabel);

    for (let c = 0; c < cols; c++) {
      const cell = document.createElement("div");
      cell.className = "floor-plan-cell";
      const layoutEntry = layout.byCoord.get(`${c}:${r}`);
      const crossContext = { lineIndex: c, positionIndex: r, colIndex: c, rowIndex: r, position: r };
      const crossExcluded = false;

      if (!layoutEntry) {
        cell.classList.add("empty");
        cell.title = crossExcluded ? "제외된 빈 칸" : `빈 칸 (${c + 1}, ${r + 1})`;
        cell.addEventListener("mouseenter", () => {
          cell.classList.add("slot-hover");
          _setSlotStatus(slotStatus, _lineCreateMode?.roomId === room.id ? "라인 추가 모드입니다. 시작셀과 종료셀을 차례로 클릭하세요." : `빈 칸 좌표 ${c + 1}, ${r + 1}`, "현재 위치");
        });
        cell.addEventListener("mouseleave", () => {
          cell.classList.remove("slot-hover");
          if (_selectedSlotKey !== `empty:${c}:${r}`) {
            _setSlotStatus(slotStatus, _lineCreateMode?.roomId === room.id ? "라인 추가 모드입니다. 시작셀과 종료셀을 차례로 클릭하세요." : "라인은 가로/세로 직선으로 배치됩니다. 라인 추가 후 슬롯에 랙을 배치하세요.", "안내");
          }
        });
        cell.addEventListener("click", async () => {
          if (_lineCreateMode?.roomId === room.id) {
            if (!_lineCreateStart) {
              _lineCreateStart = { colIndex: c, rowIndex: r, lineIndex: c, positionIndex: r };
              grid.querySelectorAll(".floor-plan-cell.slot-selected").forEach((el) => el.classList.remove("slot-selected"));
              cell.classList.add("slot-selected");
              _setSlotStatus(slotStatus, "시작셀이 선택되었습니다. 종료셀을 클릭하세요.", "라인 추가");
              return;
            }
            try {
              const created = _lineCreateMode?.mode === "reposition" && _lineRepositionTarget
                ? await applyTwoPointLineToExisting(_lineRepositionTarget, room, _lineCreateStart, { colIndex: c, rowIndex: r, lineIndex: c, positionIndex: r })
                : await applyTwoPointLine(room, _lineCreateStart, { colIndex: c, rowIndex: r, lineIndex: c, positionIndex: r });
              if (created) {
                const wasReposition = _lineCreateMode?.mode === "reposition";
                resetLineCreateMode();
                showToast(wasReposition ? "라인 좌표를 재설정했습니다." : "라인을 생성했습니다.");
                await loadTree();
                const content = document.getElementById("layout-content");
                content.textContent = "";
                renderRoomView(content, _findRoomData(room.id) || room);
              }
            } catch (err) {
              showToast(err.message, "error");
            }
            return;
          }
          if (_editMode) return;
          _selectedSlotKey = `empty:${c}:${r}`;
          _selectedSlotContext = { line: null, colIndex: c, rowIndex: r, lineIndex: c, position: r, room, rackLines, isExcluded: false };
          grid.querySelectorAll(".floor-plan-cell.slot-selected").forEach((el) => el.classList.remove("slot-selected"));
          cell.classList.add("slot-selected");
          _setSlotStatus(slotStatus, `빈 칸 좌표 ${c + 1}, ${r + 1}`, "선택된 칸");
          renderSlotActions();
        });
        cell.addEventListener("dragover", (e) => {
          e.preventDefault();
          if (_draggedRackId) cell.classList.add("drag-invalid");
        });
        cell.addEventListener("dragleave", () => {
          cell.classList.remove("drag-over");
          cell.classList.remove("drag-invalid");
        });
        cell.addEventListener("drop", async (e) => {
          e.preventDefault();
          cell.classList.remove("drag-over");
          cell.classList.remove("drag-invalid");
          const rackId = Number(e.dataTransfer.getData("application/x-rack-id"));
          if (!rackId) return;
          await placeRackAtContext(rackId, room, { ...crossContext, line: null, isExcluded: true });
        });
        grid.appendChild(cell);
        continue;
      }

      const line = layoutEntry.line;
      const positionIndex = layoutEntry.position;
      const rack = rackByPos[`${line.id}:${positionIndex}`];
      const slotExcluded = (line.disabled_slots || []).includes(positionIndex);
      const isSelectedLine = _selectedNode?.type === "line" && String(_selectedNode.id) === String(line.id);
      cell.classList.add("line-slot");
      cell.dataset.lineId = line.id;
      cell.dataset.position = positionIndex;
      cell.dataset.lineName = line.line_name;
      cell.dataset.slotKey = `${line.id}:${positionIndex}`;
      if (slotExcluded) cell.classList.add("is-excluded");
      if (line.direction) cell.classList.add(`line-${line.direction}`);
      if (isSelectedLine) cell.classList.add("line-selected");
      const selectSlot = (message, extra = {}) => {
        _selectedSlotKey = cell.dataset.slotKey;
        _selectedSlotContext = { line, colIndex: c, rowIndex: r, lineIndex: c, position: positionIndex, room, rackLines, isDisabled: slotExcluded, isExcluded: slotExcluded, ...extra };
        grid.querySelectorAll(".floor-plan-cell.slot-selected").forEach((el) => el.classList.remove("slot-selected"));
        cell.classList.add("slot-selected");
        _setSlotStatus(slotStatus, message || `${_getLinePositionLabel(cell.dataset.lineName, positionIndex)} 슬롯입니다.`, "선택된 슬롯");
        renderSlotActions();
      };
      cell.addEventListener("mouseenter", () => {
        cell.classList.add("slot-hover");
        _setSlotStatus(slotStatus, `${_getLinePositionLabel(cell.dataset.lineName, positionIndex)} 슬롯입니다.`, "현재 위치");
      });
      cell.addEventListener("mouseleave", () => {
        cell.classList.remove("slot-hover");
        if (_selectedSlotKey !== cell.dataset.slotKey) {
          _setSlotStatus(slotStatus, _lineCreateMode?.roomId === room.id ? "라인 추가 모드입니다. 시작셀과 종료셀을 차례로 클릭하세요." : "라인은 가로/세로 직선으로 배치됩니다. 라인 추가 후 슬롯에 랙을 배치하세요.", "안내");
        }
      });

      if (slotExcluded) {
        cell.title = `${_getLinePositionLabel(cell.dataset.lineName, positionIndex)} (제외 슬롯)`;
        cell.addEventListener("click", () => {
          if (_editMode) {
            _toggleDisabledSlot(line, positionIndex, room);
            return;
          }
          selectSlot(`${_getLinePositionLabel(cell.dataset.lineName, positionIndex)} 제외된 슬롯입니다.`, { isDisabled: true, isExcluded: true });
        });
        grid.appendChild(cell);
        continue;
      }

      if (rack) {
        cell.classList.add("has-rack");
        cell.draggable = true;
        cell.dataset.rackId = rack.id;
        cell.textContent = getSlotDefaultCode({ line, positionIndex }) || `${line.line_name}-${positionIndex + 1}`;
        cell.title = (rack.rack_name || rack.rack_code) + " (" + rack.total_units + "U)";
        cell.addEventListener("click", () => {
          const fullRack = allRacks.find((ar) => ar.id === rack.id) || rack;
          selectSlot(`${_getLinePositionLabel(cell.dataset.lineName, positionIndex)}에 ${rack.rack_name || rack.rack_code} 랙이 배치되어 있습니다.`, { rack });
          selectNode("rack", rack.id, fullRack);
        });
        cell.addEventListener("dragstart", (e) => {
          _draggedRackId = rack.id;
          e.dataTransfer.setData("application/x-rack-id", String(rack.id));
          e.dataTransfer.effectAllowed = "move";
          cell.style.opacity = "0.4";
        });
        cell.addEventListener("dragend", () => {
          _draggedRackId = null;
          cell.style.opacity = "";
        });
      } else {
        cell.classList.add("slot-empty");
        cell.textContent = getSlotDefaultCode({ line, positionIndex }) || `${line.line_name}-${positionIndex + 1}`;
        cell.title = `${_getLinePositionLabel(cell.dataset.lineName, positionIndex)} (빈 슬롯)`;
        cell.addEventListener("click", () => {
          if (_editMode) {
            _toggleDisabledSlot(line, positionIndex, room);
            return;
          }
          selectSlot(`${_getLinePositionLabel(cell.dataset.lineName, positionIndex)} 빈 슬롯입니다.`);
        });
      }

      cell.addEventListener("dragover", (e) => {
        e.preventDefault();
        const occupantId = cell.dataset.rackId ? Number(cell.dataset.rackId) : null;
        if (_draggedRackId && !slotExcluded && (!occupantId || occupantId === _draggedRackId)) cell.classList.add("drag-over");
        if (_draggedRackId && (slotExcluded || (occupantId && occupantId !== _draggedRackId))) cell.classList.add("drag-invalid");
      });
      cell.addEventListener("dragleave", () => {
        cell.classList.remove("drag-over");
        cell.classList.remove("drag-invalid");
      });
      cell.addEventListener("drop", async (e) => {
        e.preventDefault();
        cell.classList.remove("drag-over");
        cell.classList.remove("drag-invalid");
        const rackId = Number(e.dataTransfer.getData("application/x-rack-id"));
        if (!rackId) return;
        const occupantId = cell.dataset.rackId ? Number(cell.dataset.rackId) : null;
        if (occupantId && occupantId !== rackId) {
          showToast("해당 슬롯은 이미 다른 랙이 배치되어 있습니다.", "warning");
          return;
        }
        if (slotExcluded) {
          showToast("비활성화된 슬롯에는 배치할 수 없습니다.", "warning");
          return;
        }
        try {
          await placeRackAtContext(rackId, room, { line, position: positionIndex, colIndex: c, rowIndex: r, isExcluded: false });
          showToast("랙을 배치했습니다.");
          await loadTree();
          const content = document.getElementById("layout-content");
          content.textContent = "";
          renderRoomView(content, _findRoomData(room.id) || room);
        } catch (err) {
          showToast(err.message, "error");
        }
      });
      grid.appendChild(cell);
    }

    const rowRightFrame = document.createElement("div");
    rowRightFrame.className = "floor-plan-row-label floor-plan-axis-frame";
    rowRightFrame.setAttribute("aria-hidden", "true");
    grid.appendChild(rowRightFrame);
  }

  const bottomLeftFrame = document.createElement("div");
  bottomLeftFrame.className = "floor-plan-row-label floor-plan-axis-frame";
  bottomLeftFrame.setAttribute("aria-hidden", "true");
  grid.appendChild(bottomLeftFrame);
  for (let p = 0; p < cols; p++) {
    const bottomFrame = document.createElement("div");
    bottomFrame.className = "floor-plan-header floor-plan-axis-frame";
    bottomFrame.setAttribute("aria-hidden", "true");
    grid.appendChild(bottomFrame);
  }
  const bottomRightFrame = document.createElement("div");
  bottomRightFrame.className = "floor-plan-row-label floor-plan-axis-frame";
  bottomRightFrame.setAttribute("aria-hidden", "true");
  grid.appendChild(bottomRightFrame);

  const sideCard = document.createElement("div");
  sideCard.className = "floor-plan-side-card";
  floorPlanSide.appendChild(sideCard);

  const unplacedTitle = document.createElement("div");
  unplacedTitle.className = "floor-plan-side-title";
  unplacedTitle.textContent = `미배치 랙 (${unplacedRacks.length})`;
  sideCard.appendChild(unplacedTitle);
  sideCard.appendChild(slotStatus);
  sideCard.appendChild(slotActions);

  const unplacedArea = document.createElement("div");
  unplacedArea.className = "unplaced-racks";
  sideCard.appendChild(unplacedArea);
  if (!unplacedRacks.length) {
    const emptyMsg = document.createElement("span");
    emptyMsg.className = "text-muted";
    emptyMsg.style.fontSize = "12px";
    emptyMsg.textContent = "모든 랙이 배치되었습니다.";
    unplacedArea.appendChild(emptyMsg);
  } else {
    unplacedRacks.forEach((rack) => {
      const chip = document.createElement("div");
      chip.className = "unplaced-rack-chip";
      chip.draggable = true;
      chip.dataset.rackId = rack.id;
      chip.textContent = (rack.rack_name || rack.rack_code) + " (" + rack.total_units + "U)";
      chip.addEventListener("dragstart", (e) => {
        _draggedRackId = rack.id;
        e.dataTransfer.setData("application/x-rack-id", String(rack.id));
        e.dataTransfer.effectAllowed = "move";
        chip.style.opacity = "0.4";
      });
      chip.addEventListener("dragend", () => {
        _draggedRackId = null;
        chip.style.opacity = "";
      });
      unplacedArea.appendChild(chip);
    });
  }

  const guide = document.createElement("div");
  guide.className = "floor-plan-guide";
  const guideCard = document.createElement("div");
  guideCard.className = "floor-plan-guide-card";
  guideCard.innerHTML = '<div class="floor-plan-guide-title">도움말</div><div class="floor-plan-guide-text">라인은 가로/세로 직선으로 생성됩니다. 트리에서 라인 추가를 누른 뒤 시작점과 종료점을 선택하세요. 미배치 랙은 오른쪽에서 원하는 라인 슬롯으로 끌어다 놓을 수 있습니다.</div>';
  guide.appendChild(guideCard);
  wrapper.appendChild(guide);

  unplacedArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    if (_draggedRackId) {
      unplacedArea.style.borderColor = "var(--primary-color, #2563eb)";
      unplacedArea.style.background = "rgba(37, 99, 235, 0.04)";
    }
  });
  unplacedArea.addEventListener("dragleave", () => {
    unplacedArea.style.borderColor = "";
    unplacedArea.style.background = "";
  });
  unplacedArea.addEventListener("drop", async (e) => {
    e.preventDefault();
    unplacedArea.style.borderColor = "";
    unplacedArea.style.background = "";
    const rackId = Number(e.dataTransfer.getData("application/x-rack-id"));
    if (!rackId) return;
    try {
      await apiFetch("/api/v1/racks/" + rackId, {
        method: "PATCH",
        body: { rack_line_id: null, line_position: null },
      });
      showToast("랙 배치를 해제했습니다.");
      await loadTree();
      const content = document.getElementById("layout-content");
      content.textContent = "";
      renderRoomView(content, _findRoomData(room.id) || room);
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

function _getRackDisplayCode(rack, context = null) {
  if (_codeDisplay === "project_code") return rack.project_code || rack.rack_code;
  if (_codeDisplay === "rack_position" && context) {
    return getSlotDefaultCode({
      line: context.line || null,
      lineName: context.line?.line_name,
      positionIndex: context.positionIndex,
    }) || rack.rack_code;
  }
  return rack.rack_code;
}

function _findRoomData(roomId) {
  for (const rooms of Object.values(_rooms)) {
    const r = rooms.find(r => r.id === roomId);
    if (r) return r;
  }
  return null;
}

async function _createSuggestedLineForColumn(colIndex, room) {
  const rackLines = await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines");
  const suggestedName = suggestNextLineName(rackLines.filter((line) => !isUnassignedLine(line)));
  return await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines", {
    method: "POST",
    body: {
      line_name: suggestedName,
      col_index: colIndex,
      slot_count: room.grid_rows || 12,
      start_col: colIndex,
      start_row: 0,
      end_col: colIndex,
      end_row: Math.max(0, (room.grid_rows || 12) - 1),
      direction: "vertical",
      prefix: null,
    },
  });
}

async function _startRackAddFromSelectedCell(room) {
  const ctx = _selectedSlotContext;
  if (!ctx?.line) {
    showToast("라인 슬롯을 먼저 선택하세요.", "warning");
    return;
  }
  openRackModal();
}

async function _onEmptyColumnClick(colIndex, room) {
  const name = prompt("\uB77C\uC778\uBA85\uC744 \uC785\uB825\uD558\uC138\uC694 (\uC608: A\uB77C\uC778):");
  if (!name) return;
  const prefix = prompt("\uB77C\uC778 \uC811\uB450\uC5B4 (project_code \uC0DD\uC131\uC6A9, \uC120\uD0DD):", "") || null;
  try {
    await apiFetch("/api/v1/rooms/" + room.id + "/rack-lines", {
      method: "POST",
      body: {
        line_name: name,
        col_index: colIndex,
        slot_count: room.grid_rows || 12,
        prefix: prefix,
      },
    });
    showToast("\uB77C\uC778\uC744 \uC0DD\uC131\uD588\uC2B5\uB2C8\uB2E4.");
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRoomView(content, room);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function _onLineHeaderClick(line, room) {
  const action = prompt("\uB77C\uC778 '" + line.line_name + "' \uC791\uC5C5\uC744 \uC120\uD0DD\uD558\uC138\uC694:\n1: \uC774\uB984 \uBCC0\uACBD\n2: \uC0AD\uC81C\n(\uBC88\uD638 \uC785\uB825)");
  if (action === "1") {
    const newName = prompt("\uC0C8 \uB77C\uC778\uBA85:", line.line_name);
    if (!newName) return;
    try {
      await apiFetch("/api/v1/rack-lines/" + line.id, {
        method: "PATCH",
        body: { line_name: newName },
      });
      showToast("\uB77C\uC778\uBA85\uC744 \uBCC0\uACBD\uD588\uC2B5\uB2C8\uB2E4.");
      const content = document.getElementById("layout-content");
      content.textContent = "";
      renderRoomView(content, room);
    } catch (err) {
      showToast(err.message, "error");
    }
  } else if (action === "2") {
    if (!confirm("\uB77C\uC778 '" + line.line_name + "'\uC744(\uB97C) \uC0AD\uC81C\uD558\uC2DC\uACA0\uC2B5\uB2C8\uAE4C? \uBC30\uCE58\uB41C \uB799\uC740 \uBBF8\uBC30\uCE58 \uC0C1\uD0DC\uB85C \uC804\uD658\uB429\uB2C8\uB2E4.")) return;
    try {
      await apiFetch("/api/v1/rack-lines/" + line.id, { method: "DELETE" });
      showToast("\uB77C\uC778\uC744 \uC0AD\uC81C\uD588\uC2B5\uB2C8\uB2E4.");
      await loadTree();
      const content = document.getElementById("layout-content");
      content.textContent = "";
      renderRoomView(content, room);
    } catch (err) {
      showToast(err.message, "error");
    }
  }
}

async function _toggleDisabledSlot(line, position, room) {
  const disabledSlots = (line.disabled_slots || []).slice();
  const idx = disabledSlots.indexOf(position);
  if (idx >= 0) {
    disabledSlots.splice(idx, 1);
  } else {
    disabledSlots.push(position);
  }
  try {
    await apiFetch("/api/v1/rack-lines/" + line.id, {
      method: "PATCH",
      body: { disabled_slots: disabledSlots },
    });
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRoomView(content, room);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function renderRackView(container, rack) {
  // Fetch assets for this rack
  let assets = [];
  try {
    assets = await apiFetch("/api/v1/racks/" + rack.id + "/assets");
  } catch { /* empty */ }

  const totalU = rack.total_units || 42;
  const labelBase = document.getElementById("rack-label-base")?.value || "start";

  // Header
  const header = document.createElement("div");
  header.className = "layout-view-header";
  const h3 = document.createElement("h3");
  h3.textContent = (rack.rack_name || rack.rack_code) + " (" + totalU + "U)";
  header.appendChild(h3);

  container.appendChild(header);

  // Usage summary
  const placed = assets.filter(a => a.rack_start_unit != null);
  const unplaced = assets.filter(a => a.rack_start_unit == null);
  const usedU = placed.reduce((sum, a) => sum + ((a.rack_end_unit || a.rack_start_unit) - a.rack_start_unit + 1), 0);
  const info = document.createElement("div");
  info.className = "layout-view-info";
  info.textContent = "사용 " + usedU + "U / " + totalU + "U (" + Math.round(usedU / totalU * 100) + "%) | 장비 " + assets.length + "대 (미배치 " + unplaced.length + ")";
  container.appendChild(info);

  // Build slot map
  const slotMap = {}; // u -> asset or null
  for (let u = 1; u <= totalU; u++) slotMap[u] = null;
  placed.forEach(a => {
    const start = a.rack_start_unit;
    const end = a.rack_end_unit || start;
    for (let u = start; u <= end; u++) slotMap[u] = a;
  });

  // U diagram
  const diagram = document.createElement("div");
  diagram.className = "u-diagram";
  container.appendChild(diagram);

  // Determine display order
  const uOrder = [];
  if (labelBase === "start") {
    for (let u = totalU; u >= 1; u--) uOrder.push(u); // top=42, bottom=1
  } else {
    for (let u = 1; u <= totalU; u++) uOrder.push(u); // top=1, bottom=42
  }

  const renderedAssets = new Set(); // track which assets already have a block rendered

  uOrder.forEach(u => {
    const slot = document.createElement("div");
    slot.className = "u-slot";
    slot.dataset.unit = u;

    const numEl = document.createElement("span");
    numEl.className = "u-slot-number";
    numEl.textContent = u;
    slot.appendChild(numEl);

    const contentEl = document.createElement("div");
    contentEl.className = "u-slot-content";

    const asset = slotMap[u];
    if (asset && !renderedAssets.has(asset.id)) {
      renderedAssets.add(asset.id);
      const sizeU = (asset.rack_end_unit || asset.rack_start_unit) - asset.rack_start_unit + 1;
      const block = document.createElement("div");
      block.className = "equipment-block";
      if (asset.environment) block.classList.add("env-" + asset.environment);
      block.draggable = true;
      block.dataset.assetId = asset.id;
      block.dataset.sizeUnit = sizeU;
      block.textContent = asset.asset_name + (asset.hostname ? " (" + asset.hostname + ")" : "");
      if (sizeU > 1) {
        block.style.height = (sizeU * 24 - 2) + "px"; // each slot is 24px
        block.style.position = "relative";
        block.style.zIndex = "1";
      }

      // Drag start
      block.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("application/x-asset-id", String(asset.id));
        e.dataTransfer.setData("application/x-size-unit", String(sizeU));
        e.dataTransfer.effectAllowed = "move";
        block.classList.add("is-dragging");
      });
      block.addEventListener("dragend", () => block.classList.remove("is-dragging"));

      contentEl.appendChild(block);
    } else if (asset && renderedAssets.has(asset.id)) {
      // This slot is part of a multi-U equipment — leave content empty (the block spans visually)
      contentEl.classList.add("u-slot-occupied");
    }

    // Drop zone handlers
    slot.addEventListener("dragover", (e) => {
      e.preventDefault();
      slot.classList.add("drop-target");
    });
    slot.addEventListener("dragleave", () => slot.classList.remove("drop-target"));
    slot.addEventListener("drop", async (e) => {
      e.preventDefault();
      slot.classList.remove("drop-target");
      const assetId = Number(e.dataTransfer.getData("application/x-asset-id"));
      const sizeUnit = Number(e.dataTransfer.getData("application/x-size-unit")) || 1;
      const targetU = Number(slot.dataset.unit);

      // Check if placement is valid
      if (!_canPlaceAt(slotMap, targetU, sizeUnit, totalU, assetId)) {
        showToast("해당 위치에 배치할 수 없습니다. (" + sizeUnit + "U 연속 빈 공간 필요)", "warning");
        return;
      }

      try {
        await apiFetch("/api/v1/assets/" + assetId, {
          method: "PATCH",
          body: {
            rack_start_unit: targetU,
            rack_end_unit: targetU + sizeUnit - 1,
          },
        });
        showToast("장비 배치 완료");
        // Re-render
        const content = document.getElementById("layout-content");
        content.textContent = "";
        renderRackView(content, rack);
      } catch (err) { showToast(err.message, "error"); }
    });

    slot.appendChild(contentEl);
    diagram.appendChild(slot);
  });

  // Unplaced section
  if (unplaced.length) {
    const section = document.createElement("div");
    section.className = "unplaced-section";
    const title = document.createElement("div");
    title.className = "unplaced-title";
    title.textContent = "미배치 장비 (" + unplaced.length + ")";
    section.appendChild(title);

    unplaced.forEach(a => {
      const item = document.createElement("div");
      item.className = "unplaced-item";
      item.draggable = true;
      item.dataset.assetId = a.id;
      item.dataset.sizeUnit = a.size_unit || 1;
      item.textContent = a.asset_name + (a.size_unit ? " (" + a.size_unit + "U)" : "");

      item.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("application/x-asset-id", String(a.id));
        e.dataTransfer.setData("application/x-size-unit", String(a.size_unit || 1));
        e.dataTransfer.effectAllowed = "move";
        item.classList.add("is-dragging");
      });
      item.addEventListener("dragend", () => item.classList.remove("is-dragging"));

      section.appendChild(item);
    });

    // Drop zone for "unplace" — drag back to unplaced
    section.addEventListener("dragover", (e) => { e.preventDefault(); section.classList.add("drop-target"); });
    section.addEventListener("dragleave", () => section.classList.remove("drop-target"));
    section.addEventListener("drop", async (e) => {
      e.preventDefault();
      section.classList.remove("drop-target");
      const assetId = Number(e.dataTransfer.getData("application/x-asset-id"));
      if (!assetId) return;
      try {
        await apiFetch("/api/v1/assets/" + assetId, {
          method: "PATCH",
          body: { rack_start_unit: null, rack_end_unit: null },
        });
        showToast("장비 배치 해제");
        const content = document.getElementById("layout-content");
        content.textContent = "";
        renderRackView(content, rack);
      } catch (err) { showToast(err.message, "error"); }
    });

    container.appendChild(section);
  }
}

async function getRoomRackLines(roomId) {
  if (!roomId) return [];
  try {
    return await apiFetch("/api/v1/rooms/" + roomId + "/rack-lines");
  } catch {
    return [];
  }
}

function getLineSlotCount(line, room = null) {
  return Math.max(1, Number(line?.slot_count || room?.grid_rows || 1));
}

function getFirstEmptyLinePosition(line, roomRacks = [], room = null, excludeRackId = null) {
  const used = new Set(
    (roomRacks || [])
      .filter((rack) => Number(rack.rack_line_id) === Number(line.id) && rack.line_position != null && Number(rack.id) !== Number(excludeRackId))
      .map((rack) => Number(rack.line_position))
      .filter(Number.isFinite)
  );
  const slotCount = getLineSlotCount(line, room);
  for (let pos = 0; pos < slotCount; pos++) {
    if (!used.has(pos)) return pos;
  }
  return slotCount;
}

async function populateRackPlacementFields(rack = null) {
  const lineSelect = document.getElementById("rack-line-id");
  const posInput = document.getElementById("rack-line-position");
  if (!lineSelect || !posInput || !_selectedRoomId) return;
  const room = _findRoomData(_selectedRoomId);
  const roomLines = await getRoomRackLines(_selectedRoomId);
  const assignableLines = roomLines.filter((line) => !isUnassignedLine(line));
  lineSelect.innerHTML = '<option value="">미할당</option>';
  assignableLines.forEach((line) => {
    const opt = document.createElement("option");
    opt.value = String(line.id);
    opt.textContent = line.line_name;
    lineSelect.appendChild(opt);
  });

  let selectedLineId = rack?.rack_line_id ?? _selectedSlotContext?.line?.id ?? "";
  if (selectedLineId && !assignableLines.some((line) => String(line.id) === String(selectedLineId))) selectedLineId = "";
  lineSelect.value = selectedLineId ? String(selectedLineId) : "";

  const syncPosition = () => {
    const currentLine = assignableLines.find((line) => String(line.id) === String(lineSelect.value));
    if (!currentLine) {
      posInput.value = "";
      posInput.placeholder = "미할당";
      return;
    }
    if (posInput.dataset.manual === "1") return;
    const fallback = rack && Number(rack.rack_line_id) === Number(currentLine.id) && rack.line_position != null
      ? Number(rack.line_position)
      : (_selectedSlotContext?.line && Number(_selectedSlotContext.line.id) === Number(currentLine.id) && _selectedSlotContext.position != null
          ? Number(_selectedSlotContext.position)
          : getFirstEmptyLinePosition(currentLine, _racks[_selectedRoomId] || [], room, rack?.id));
    posInput.value = String(Number(fallback) + 1);
    posInput.placeholder = `자동 추천: ${Number(fallback) + 1}`;
  };

  posInput.dataset.manual = rack?.line_position != null ? "1" : "0";
  posInput.value = rack?.line_position != null ? String(Number(rack.line_position) + 1) : "";
  posInput.oninput = () => {
    posInput.dataset.manual = posInput.value.trim() ? "1" : "0";
  };
  lineSelect.onchange = () => {
    posInput.dataset.manual = "0";
    posInput.value = "";
    syncPosition();
  };
  syncPosition();
}

function _canPlaceAt(slotMap, startU, sizeUnit, totalU, excludeAssetId) {
  for (let u = startU; u < startU + sizeUnit; u++) {
    if (u < 1 || u > totalU) return false;
    const occupant = slotMap[u];
    if (occupant && occupant.id !== excludeAssetId) return false;
  }
  return true;
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
  document.getElementById("center-main").checked = !!center?.is_main;
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
  document.getElementById("room-grid-cols").value = room?.grid_cols ?? 10;
  document.getElementById("room-grid-rows").value = room?.grid_rows ?? 12;
  document.getElementById("room-active").value = String(room?.is_active ?? true);
  document.getElementById("room-main").checked = !!room?.is_main;
  document.getElementById("room-note").value = room?.note ?? "";
  document.getElementById("modal-room").showModal();
}

async function openRackModal(rack) {
  if (!_selectedRoomId) {
    showToast("전산실을 먼저 선택하세요.", "warning");
    return;
  }
  document.getElementById("modal-rack-title").textContent = rack ? "랙 수정" : "랙 등록";
  document.getElementById("rack-id").value = rack?.id ?? "";
  _rackCodeSuggestionLocked = !!rack;
  document.getElementById("rack-code").value = rack?.rack_code ?? "";
  if (!rack) applySuggestedRackCode({ force: true });
  document.getElementById("rack-name").value = rack?.rack_name ?? "";
  document.getElementById("rack-total-units").value = rack?.total_units ?? 42;
  document.getElementById("rack-location-detail").value = rack?.location_detail ?? "";
  document.getElementById("rack-active").value = String(rack?.is_active ?? true);
  document.getElementById("rack-note").value = rack?.note ?? "";
  await populateRackPlacementFields(rack);
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
    is_main: document.getElementById("center-main").checked,
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
    grid_cols: Number(document.getElementById("room-grid-cols").value) || 10,
    grid_rows: Number(document.getElementById("room-grid-rows").value) || 12,
    is_active: document.getElementById("room-active").value === "true",
    is_main: document.getElementById("room-main").checked,
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
  const lineSelectValue = document.getElementById("rack-line-id").value;
  const linePositionValue = document.getElementById("rack-line-position").value.trim();
  const payload = {
    room_id: _selectedRoomId,
    rack_code: document.getElementById("rack-code").value.trim() || null,
    rack_name: document.getElementById("rack-name").value.trim() || null,
    total_units: Number(document.getElementById("rack-total-units").value || 42),
    location_detail: document.getElementById("rack-location-detail").value.trim() || null,
    is_active: document.getElementById("rack-active").value === "true",
    note: document.getElementById("rack-note").value.trim() || null,
    rack_line_id: lineSelectValue ? Number(lineSelectValue) : null,
    line_position: lineSelectValue && linePositionValue ? Math.max(0, Number(linePositionValue) - 1) : null,
  };
  if (lineSelectValue && !linePositionValue) {
    showToast("좌표 순번을 입력하세요.", "warning");
    return;
  }
  if (_selectedSlotContext && !rackId && !_selectedSlotContext.isExcluded && !lineSelectValue && _selectedSlotContext.line) {
    payload.rack_line_id = _selectedSlotContext.line.id;
    payload.line_position = _selectedSlotContext.position;
  }
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

/* ── Label Base Setting ── */

async function loadLabelBaseSetting() {
  const pid = getCtxProjectId();
  if (!pid) return;
  try {
    const period = await apiFetch("/api/v1/contract-periods/" + pid);
    if (period.rack_label_base) {
      document.getElementById("rack-label-base").value = period.rack_label_base;
    }
  } catch { /* default */ }
}

/* ── Event Listeners ── */

document.addEventListener("DOMContentLoaded", () => {
  initTreeSplitter();
  updateLayoutAutoCollapseBtn();
  updateLayoutTreeModeBtn();
  setLayoutTreeCollapsed(false);
  loadTree()
    .then(() => loadLabelBaseSetting())
    .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-toggle-layout-tree")?.addEventListener("click", () => {
  const shell = document.getElementById("layout-shell");
  const isCollapsed = shell?.classList.contains("layout-tree-collapsed");
  setLayoutTreeCollapsed(!isCollapsed);
});

document.getElementById("btn-layout-auto-collapse")?.addEventListener("click", () => {
  _layoutAutoCollapse = !_layoutAutoCollapse;
  localStorage.setItem(LAYOUT_AUTO_COLLAPSE_KEY, _layoutAutoCollapse ? "1" : "0");
  updateLayoutAutoCollapseBtn();
  if (_selectedNode && window.innerWidth > 960) setLayoutTreeCollapsed(_layoutAutoCollapse);
});

document.getElementById("btn-layout-tree-mode")?.addEventListener("click", () => {
  _layoutTreeActionMode = _layoutTreeActionMode === "detail" ? "compact" : "detail";
  localStorage.setItem(LAYOUT_TREE_ACTION_MODE_KEY, _layoutTreeActionMode);
  if (_layoutTreeActionMode === "detail") _expandedTreeActions.clear();
  updateLayoutTreeModeBtn();
  renderTree();
});

document.getElementById("btn-layout-tree-save")?.addEventListener("click", () => {
  loadTree().catch(err => showToast(err.message, "error"));
});

document.getElementById("rack-label-base").addEventListener("change", () => {
  if (_selectedNode && _selectedNode.type === "rack") {
    const content = document.getElementById("layout-content");
    content.textContent = "";
    renderRackView(content, _selectedNode.data);
  }
});

window.addEventListener("resize", () => {
  applyPhysicalLayoutResponsiveSizing();
});

window.addEventListener("ctx-changed", () => {
  _selectedNode = null;
  _selectedCenterId = null;
  _selectedRoomId = null;
  _treeCollapsed.clear();
  _expandedTreeActions.clear();
  updateLayoutTreeModeBtn();
  loadTree()
    .then(() => loadLabelBaseSetting())
    .catch(err => showToast(err.message, "error"));
});

document.getElementById("btn-add-center").addEventListener("click", () => openCenterModal());
document.getElementById("btn-add-room")?.addEventListener("click", () => openRoomModal());
document.getElementById("btn-add-rack")?.addEventListener("click", () => openRackModal());
document.getElementById("btn-cancel-center").addEventListener("click", () => document.getElementById("modal-center").close());
document.getElementById("btn-save-center").addEventListener("click", () => saveCenter().catch(err => showToast(err.message, "error")));
document.getElementById("btn-cancel-room").addEventListener("click", () => document.getElementById("modal-room").close());
document.getElementById("btn-save-room").addEventListener("click", () => saveRoom().catch(err => showToast(err.message, "error")));
document.getElementById("btn-cancel-rack").addEventListener("click", () => document.getElementById("modal-rack").close());
document.getElementById("btn-save-rack").addEventListener("click", () => saveRack().catch(err => showToast(err.message, "error")));
document.getElementById("btn-save-line")?.addEventListener("click", () => saveLineModal().catch(err => showToast(err.message, "error")));
document.getElementById("btn-cancel-line")?.addEventListener("click", () => document.getElementById("modal-line")?.close());
document.getElementById("btn-line-reposition")?.addEventListener("click", async () => {
  const lineId = Number(document.getElementById('line-id')?.value || 0);
  const roomId = Number(document.getElementById('line-room-id')?.value || 0);
  if (!lineId || !roomId) return;
  const line = (_rackLines[roomId] || []).find((item) => Number(item.id) === lineId);
  if (!line) {
    showToast('라인 정보를 다시 불러와 주세요.', 'warning');
    return;
  }
  beginLineReposition(line);
});
