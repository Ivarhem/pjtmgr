/* ── Modal Combobox (검색 가능 드롭다운) ── */

class ModalCombobox {
  constructor({ inputId, hiddenId, dropdownId, onSelect, maxDisplay = 0, footerAction = null }) {
    this.input = document.getElementById(inputId);
    this.hidden = document.getElementById(hiddenId);
    this.dropdown = document.getElementById(dropdownId);
    this.onSelect = onSelect || (() => {});
    this.maxDisplay = maxDisplay;
    this.footerAction = footerAction;   // { label, onClick } or null
    this.items = [];           /* { value, label, hint? } */
    this._focusIdx = -1;
    this._bound = false;
  }

  bind() {
    if (this._bound) return;
    this._bound = true;
    this.input.addEventListener("input", () => this._filter());
    this.input.addEventListener("focus", () => this._filter());
    this.input.addEventListener("keydown", (e) => this._onKey(e));
    /* 드롭다운 외부 클릭 시 닫기 */
    document.addEventListener("mousedown", (e) => {
      if (!this.dropdown.contains(e.target) && e.target !== this.input) {
        this._close();
      }
    });
  }

  setItems(items) { this.items = items; }

  setValue(value, label) {
    this.hidden.value = value || "";
    this.input.value = label || "";
  }

  getValue() { return this.hidden.value; }
  getDisplayText() { return this.input.value; }

  _filter() {
    const q = this.input.value.trim().toLowerCase();
    const filtered = q
      ? this.items.filter((item) =>
          item.label.toLowerCase().includes(q)
          || (item.hint || "").toLowerCase().includes(q)
          || (item.aliases || []).some((a) => a.toLowerCase().includes(q)))
      : this.items;
    this._render(filtered);
  }

  _render(items) {
    this.dropdown.textContent = "";
    this._focusIdx = -1;
    if (!items.length) {
      const empty = document.createElement("div");
      empty.className = "modal-combobox-empty";
      empty.textContent = "검색 결과 없음";
      this.dropdown.appendChild(empty);
      if (this.footerAction) {
        const footer = document.createElement("div");
        footer.className = "modal-combobox-footer-action";
        footer.textContent = this.footerAction.label;
        footer.addEventListener("mousedown", (e) => {
          e.preventDefault();
          this._close();
          this.footerAction.onClick();
        });
        this.dropdown.appendChild(footer);
      }
      setElementHidden(this.dropdown, false);
      return;
    }
    const totalCount = items.length;
    const display = this.maxDisplay > 0 ? items.slice(0, this.maxDisplay) : items;
    display.forEach((item, idx) => {
      const div = document.createElement("div");
      div.className = "modal-combobox-option";
      div.dataset.value = item.value;
      div.dataset.idx = idx;
      div.textContent = item.label;
      if (item.hint) {
        const span = document.createElement("span");
        span.className = "combobox-hint";
        span.textContent = item.hint;
        div.appendChild(span);
      }
      div.addEventListener("mousedown", (e) => {
        e.preventDefault();
        this._select(item);
      });
      this.dropdown.appendChild(div);
    });
    if (this.maxDisplay > 0 && totalCount > this.maxDisplay) {
      const more = document.createElement("div");
      more.className = "modal-combobox-empty";
      more.textContent = `외 ${totalCount - this.maxDisplay}건 — 검색어를 더 입력하세요`;
      this.dropdown.appendChild(more);
    }
    if (this.footerAction) {
      const footer = document.createElement("div");
      footer.className = "modal-combobox-footer-action";
      footer.textContent = this.footerAction.label;
      footer.addEventListener("mousedown", (e) => {
        e.preventDefault();
        this._close();
        this.footerAction.onClick();
      });
      this.dropdown.appendChild(footer);
    }
    setElementHidden(this.dropdown, false);
  }

  _select(item) {
    this.hidden.value = item.value;
    this.input.value = item.label;
    this._close();
    this.onSelect(item);
  }

  _close() {
    setElementHidden(this.dropdown, true);
    this._focusIdx = -1;
  }

  _onKey(e) {
    const opts = this.dropdown.querySelectorAll(".modal-combobox-option");
    if (e.key === "ArrowDown") {
      e.preventDefault();
      this._focusIdx = Math.min(this._focusIdx + 1, opts.length - 1);
      this._highlightIdx(opts);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      this._focusIdx = Math.max(this._focusIdx - 1, 0);
      this._highlightIdx(opts);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (this._focusIdx >= 0 && opts[this._focusIdx]) {
        const val = opts[this._focusIdx].dataset.value;
        const item = this.items.find((i) => i.value === val);
        if (item) this._select(item);
      }
    } else if (e.key === "Escape") {
      this._close();
    }
  }

  _highlightIdx(opts) {
    opts.forEach((o) => o.classList.remove("is-focused"));
    if (opts[this._focusIdx]) {
      opts[this._focusIdx].classList.add("is-focused");
      opts[this._focusIdx].scrollIntoView({ block: "nearest" });
    }
  }

  reset() {
    this.hidden.value = "";
    this.input.value = "";
    this._close();
  }
}
