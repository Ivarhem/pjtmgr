(() => {
  const ICONS = {
    menu: [
      ["line", { x1: "4", y1: "12", x2: "20", y2: "12" }],
      ["line", { x1: "4", y1: "6", x2: "20", y2: "6" }],
      ["line", { x1: "4", y1: "18", x2: "20", y2: "18" }],
    ],
    x: [
      ["line", { x1: "18", y1: "6", x2: "6", y2: "18" }],
      ["line", { x1: "6", y1: "6", x2: "18", y2: "18" }],
    ],
    sun: [
      ["circle", { cx: "12", cy: "12", r: "4" }],
      ["line", { x1: "12", y1: "2", x2: "12", y2: "4" }],
      ["line", { x1: "12", y1: "20", x2: "12", y2: "22" }],
      ["line", { x1: "4.93", y1: "4.93", x2: "6.34", y2: "6.34" }],
      ["line", { x1: "17.66", y1: "17.66", x2: "19.07", y2: "19.07" }],
      ["line", { x1: "2", y1: "12", x2: "4", y2: "12" }],
      ["line", { x1: "20", y1: "12", x2: "22", y2: "12" }],
      ["line", { x1: "4.93", y1: "19.07", x2: "6.34", y2: "17.66" }],
      ["line", { x1: "17.66", y1: "6.34", x2: "19.07", y2: "4.93" }],
    ],
    moon: [
      ["path", { d: "M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z" }],
    ],
    "help-circle": [
      ["circle", { cx: "12", cy: "12", r: "10" }],
      ["path", { d: "M9.09 9a3 3 0 1 1 5.82 1c0 2-3 3-3 3" }],
      ["line", { x1: "12", y1: "17", x2: "12.01", y2: "17" }],
    ],
    "layout-grid": [
      ["rect", { x: "3", y: "3", width: "7", height: "7", rx: "1" }],
      ["rect", { x: "14", y: "3", width: "7", height: "7", rx: "1" }],
      ["rect", { x: "14", y: "14", width: "7", height: "7", rx: "1" }],
      ["rect", { x: "3", y: "14", width: "7", height: "7", rx: "1" }],
    ],
    "user-check": [
      ["path", { d: "M16 21v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" }],
      ["circle", { cx: "9.5", cy: "7", r: "4" }],
      ["path", { d: "m16 11 2 2 4-4" }],
    ],
    "file-stack": [
      ["path", { d: "M21 7h-3a2 2 0 0 1-2-2V2" }],
      ["path", { d: "M18 21H8a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8l5 5v11a2 2 0 0 1-2 2z" }],
      ["path", { d: "M8 7h8" }],
      ["path", { d: "M8 11h8" }],
      ["path", { d: "M8 15h5" }],
    ],
    "building-2": [
      ["path", { d: "M6 22V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v18" }],
      ["path", { d: "M6 12H4a1 1 0 0 0-1 1v9" }],
      ["path", { d: "M18 9h2a1 1 0 0 1 1 1v12" }],
      ["path", { d: "M10 6h4" }],
      ["path", { d: "M10 10h4" }],
      ["path", { d: "M10 14h4" }],
      ["path", { d: "M10 18h4" }],
    ],
    "bar-chart-3": [
      ["path", { d: "M3 3v18h18" }],
      ["path", { d: "M18 17V9" }],
      ["path", { d: "M13 17V5" }],
      ["path", { d: "M8 17v-3" }],
    ],
    users: [
      ["path", { d: "M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" }],
      ["circle", { cx: "9", cy: "7", r: "4" }],
      ["path", { d: "M22 21v-2a4 4 0 0 0-3-3.87" }],
      ["path", { d: "M16 3.13a4 4 0 0 1 0 7.75" }],
    ],
    "sliders-horizontal": [
      ["line", { x1: "21", y1: "4", x2: "14", y2: "4" }],
      ["line", { x1: "10", y1: "4", x2: "3", y2: "4" }],
      ["line", { x1: "21", y1: "12", x2: "12", y2: "12" }],
      ["line", { x1: "8", y1: "12", x2: "3", y2: "12" }],
      ["line", { x1: "21", y1: "20", x2: "16", y2: "20" }],
      ["line", { x1: "12", y1: "20", x2: "3", y2: "20" }],
      ["line", { x1: "14", y1: "2", x2: "14", y2: "6" }],
      ["line", { x1: "8", y1: "10", x2: "8", y2: "14" }],
      ["line", { x1: "16", y1: "18", x2: "16", y2: "22" }],
    ],
  };

  function buildIcon(name, attrs = {}) {
    const nodes = ICONS[name];
    if (!nodes) {
      return null;
    }

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    const className = attrs.class || attrs.className || "";
    const baseAttrs = {
      xmlns: "http://www.w3.org/2000/svg",
      width: attrs.width || "24",
      height: attrs.height || "24",
      viewBox: "0 0 24 24",
      fill: "none",
      stroke: "currentColor",
      "stroke-width": attrs["stroke-width"] || attrs.strokeWidth || "2",
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      class: className,
      "data-lucide": name,
      "aria-hidden": "true",
    };

    Object.entries(baseAttrs).forEach(([key, value]) => {
      if (value) {
        svg.setAttribute(key, value);
      }
    });

    nodes.forEach(([tagName, tagAttrs]) => {
      const node = document.createElementNS("http://www.w3.org/2000/svg", tagName);
      Object.entries(tagAttrs).forEach(([key, value]) => node.setAttribute(key, value));
      svg.appendChild(node);
    });

    return svg;
  }

  function createIcons(root = document) {
    root.querySelectorAll("[data-lucide]").forEach((el) => {
      if (el.tagName.toLowerCase() === "svg") {
        return;
      }
      const name = el.getAttribute("data-lucide");
      const svg = buildIcon(name, {
        class: el.getAttribute("class") || "",
        width: el.getAttribute("width") || undefined,
        height: el.getAttribute("height") || undefined,
        strokeWidth: el.getAttribute("stroke-width") || undefined,
      });
      if (!svg) {
        return;
      }
      [...el.attributes].forEach((attr) => {
        if (attr.name === "data-lucide" || attr.name === "class") {
          return;
        }
        if (!svg.hasAttribute(attr.name)) {
          svg.setAttribute(attr.name, attr.value);
        }
      });
      el.replaceWith(svg);
    });
  }

  window.lucide = {
    createIcons,
  };
})();
