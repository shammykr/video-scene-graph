// Frame browser: draws detections on the frame and the scene graph as an SVG.
const slider = document.getElementById("slider");
const info = document.getElementById("info");
const canvas = document.getElementById("frame");
const ctx = canvas.getContext("2d");
const svg = document.getElementById("graph");
const edgesEl = document.getElementById("edges");
const SVG_NS = "http://www.w3.org/2000/svg";

let frames = [];

function color(id) {
  return `hsl(${(id * 137.5) % 360}, 70%, 45%)`;
}

function drawFrame(rec) {
  const img = new Image();
  img.onload = () => {
    canvas.width = img.width;
    canvas.height = img.height;
    ctx.drawImage(img, 0, 0);
    ctx.lineWidth = 2;
    ctx.font = "12px system-ui";
    for (const n of rec.nodes) {
      const [x1, y1, x2, y2] = n.box;
      ctx.strokeStyle = ctx.fillStyle = color(n.id);
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.fillText(`#${n.id} ${n.label}`, x1 + 2, Math.max(12, y1 - 3));
    }
  };
  img.src = rec.image;
}

function el(tag, attrs, text) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text !== undefined) e.textContent = text;
  return e;
}

function drawGraph(rec) {
  svg.replaceChildren();
  const W = 420, H = 420, R = 150, cx = W / 2, cy = H / 2;
  const pos = {};
  rec.nodes.forEach((n, i) => {
    const a = (2 * Math.PI * i) / Math.max(rec.nodes.length, 1) - Math.PI / 2;
    pos[n.id] = rec.nodes.length === 1 ? [cx, cy] : [cx + R * Math.cos(a), cy + R * Math.sin(a)];
  });
  svg.appendChild(el("defs", {})).appendChild(
    el("marker", { id: "arrow", viewBox: "0 0 10 10", refX: 22, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" })
  ).appendChild(el("path", { d: "M0,0 L10,5 L0,10 z", fill: "#888" }));

  for (const e of rec.edges) {
    const [x1, y1] = pos[e.source], [x2, y2] = pos[e.target];
    const attrs = { x1, y1, x2, y2, stroke: "#aaa" };
    if (e.relation === "overlapping") attrs["stroke-dasharray"] = "4 3";
    else attrs["marker-end"] = "url(#arrow)";
    svg.appendChild(el("line", attrs));
    // Directed labels sit nearer their source so A->B and B->A don't overlap.
    const t = e.relation === "overlapping" ? 0.5 : 0.3;
    svg.appendChild(el("text", { x: x1 + t * (x2 - x1), y: y1 + t * (y2 - y1) - 3, fill: "#666", "text-anchor": "middle" }, e.relation));
  }
  for (const n of rec.nodes) {
    const [x, y] = pos[n.id];
    svg.appendChild(el("circle", { cx: x, cy: y, r: 16, fill: color(n.id) }));
    svg.appendChild(el("text", { x, y: y + 4, fill: "#fff", "text-anchor": "middle" }, `#${n.id}`));
    svg.appendChild(el("text", { x, y: y + 30, fill: "#333", "text-anchor": "middle" }, n.label));
  }
  if (!rec.nodes.length) svg.appendChild(el("text", { x: cx, y: cy, "text-anchor": "middle" }, "no objects detected"));

  const label = Object.fromEntries(rec.nodes.map((n) => [n.id, `${n.label}#${n.id}`]));
  edgesEl.textContent = rec.edges.map((e) => `${label[e.source]} ${e.relation} ${label[e.target]}`).join("\n");
}

function show(i) {
  const rec = frames[i];
  slider.value = i;
  info.textContent = `frame ${rec.index} (${i + 1}/${frames.length}) - ${rec.nodes.length} objects, ${rec.edges.length} relations`;
  drawFrame(rec);
  drawGraph(rec);
}

document.getElementById("prev").onclick = () => show(Math.max(0, +slider.value - 1));
document.getElementById("next").onclick = () => show(Math.min(frames.length - 1, +slider.value + 1));
slider.oninput = () => show(+slider.value);
document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowLeft") document.getElementById("prev").click();
  if (e.key === "ArrowRight") document.getElementById("next").click();
});

fetch("/api/graphs")
  .then((r) => r.json())
  .then((data) => {
    frames = data.frames;
    document.getElementById("title").textContent = `- ${data.video}`;
    slider.max = frames.length - 1;
    const busiest = frames.reduce((b, f, i) => (f.nodes.length > frames[b].nodes.length ? i : b), 0);
    show(busiest);
  });
