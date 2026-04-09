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
    "clipboard-list": [
      ["rect", { x: "8", y: "2", width: "8", height: "4", rx: "1", ry: "1" }],
      ["path", { d: "M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" }],
      ["path", { d: "M12 11h4" }],
      ["path", { d: "M12 16h4" }],
      ["path", { d: "M8 11h.01" }],
      ["path", { d: "M8 16h.01" }],
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
    briefcase: [
      ["path", { d: "M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" }],
      ["rect", { width: "20", height: "14", x: "2", y: "6", rx: "2" }],
    ],
    "chevron-down": [
      ["path", { d: "m6 9 6 6 6-6" }],
    ],
    server: [
      ["rect", { width: "20", height: "8", x: "2", y: "2", rx: "2", ry: "2" }],
      ["rect", { width: "20", height: "8", x: "2", y: "14", rx: "2", ry: "2" }],
      ["line", { x1: "6", x2: "6.01", y1: "6", y2: "6" }],
      ["line", { x1: "6", x2: "6.01", y1: "18", y2: "18" }],
    ],
    "folder-kanban": [
      ["path", { d: "M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" }],
      ["path", { d: "M8 10v4" }],
      ["path", { d: "M12 10v2" }],
      ["path", { d: "M16 10v6" }],
    ],
    network: [
      ["rect", { x: "16", y: "16", width: "6", height: "6", rx: "1" }],
      ["rect", { x: "2", y: "16", width: "6", height: "6", rx: "1" }],
      ["rect", { x: "9", y: "2", width: "6", height: "6", rx: "1" }],
      ["path", { d: "M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3" }],
      ["path", { d: "M12 12V8" }],
    ],
    cable: [
      ["path", { d: "M17 19a1 1 0 0 1-1-1v-2a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2a1 1 0 0 1-1 1z" }],
      ["path", { d: "M17 21v-2" }],
      ["path", { d: "M19 14V6.5a1 1 0 0 0-7 0v11a1 1 0 0 1-7 0V10" }],
      ["path", { d: "M21 21v-2" }],
      ["path", { d: "M3 5V3" }],
      ["path", { d: "M4 10a2 2 0 0 1-2-2V6a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2a2 2 0 0 1-2 2z" }],
      ["path", { d: "M7 5V3" }],
    ],
    "shield-check": [
      ["path", { d: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" }],
      ["path", { d: "m9 12 2 2 4-4" }],
    ],
    "shield-alert": [
      ["path", { d: "M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" }],
      ["path", { d: "M12 8v4" }],
      ["path", { d: "M12 16h.01" }],
    ],
    history: [
      ["path", { d: "M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" }],
      ["path", { d: "M3 3v5h5" }],
      ["path", { d: "M12 7v5l4 2" }],
    ],
    "monitor-check": [
      ["path", { d: "m9 10 2 2 4-4" }],
      ["rect", { width: "20", height: "14", x: "2", y: "3", rx: "2" }],
      ["path", { d: "M12 17v4" }],
      ["path", { d: "M8 21h8" }],
    ],
    "user-cog": [
      ["path", { d: "M10 15H6a4 4 0 0 0-4 4v2" }],
      ["path", { d: "m14.305 16.53.923-.382" }],
      ["path", { d: "m15.228 13.852-.923-.383" }],
      ["path", { d: "m16.852 12.228-.383-.923" }],
      ["path", { d: "m16.852 17.772-.383.924" }],
      ["path", { d: "m19.148 12.228.383-.923" }],
      ["path", { d: "m19.53 18.696-.382-.924" }],
      ["path", { d: "m20.772 13.852.924-.383" }],
      ["path", { d: "m20.772 16.148.924.383" }],
      ["circle", { cx: "18", cy: "15", r: "3" }],
      ["circle", { cx: "9", cy: "7", r: "4" }],
    ],
    "package": [
      ["path", { d: "M16.5 9.4 7.55 4.24" }],
      ["path", { d: "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" }],
      ["polyline", { points: "3.29 7 12 12 20.71 7" }],
      ["line", { x1: "12", y1: "22", x2: "12", y2: "12" }],
    ],
    settings: [
      ["path", { d: "M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915" }],
      ["circle", { cx: "12", cy: "12", r: "3" }],
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
