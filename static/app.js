/* Mimir MVP — the four gates.
 *
 * Live slider response: every `input` event fires a request, debounced to 30 ms
 * and cancelled if a newer one arrives. The server holds the fitted
 * coefficients, so a forecast is a matrix multiply; the round trip on localhost
 * is a couple of milliseconds, which the interface shows rather than claims.
 *
 * The page holds no model. It never computes a forecast itself, so there is
 * nothing here that can drift out of parity with the round.
 */

const NS = "http://www.w3.org/2000/svg";
let LANG = localStorage.getItem("mimir.lang") || "en";
let t = T[LANG];
let PANEL = null, SEGMENT = "Flats", OVERRIDES = {}, PENDING = null;
let GATE = "1", SOURCES = null, REJECTED = [], CHAPTER = null;

const $ = (id) => document.getElementById(id);
const nf = () => LANG === "sv" ? "sv-SE" : "en-GB";
const fmt = (v, d = 0) => v == null ? "–" :
  v.toLocaleString(nf(), { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (v, d = 2) => (v >= 0 ? "+" : "−") +
  Math.abs(v).toLocaleString(nf(), { minimumFractionDigits: d, maximumFractionDigits: d });
const esc = (s) => String(s ?? "").replace(/[&<>]/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

/* Round axis ticks. A gridline every ymax/5 gave 0,2k,3k,5k,7k,8k — even
 * lines with uneven labels, which looks like a bug even when the data is
 * right. This picks a 1 / 2 / 2.5 / 5 x 10^n step so every label is round. */
function niceTicks(max, target = 5) {
  if (!(max > 0)) return { ticks: [0], top: 1 };
  const raw = max / target;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].find(m => raw <= m * mag) * mag;
  const top = Math.ceil(max / step) * step;
  const ticks = [];
  for (let v = 0; v <= top + step / 2; v += step) ticks.push(+v.toFixed(10));
  return { ticks, top };
}

function axisLabel(v) {
  const a = Math.abs(v);
  if (a >= 1e6) return (v / 1e6).toLocaleString(nf(), { maximumFractionDigits: 1 }) + "M";
  if (a >= 1000) return (v / 1000).toLocaleString(nf(), { maximumFractionDigits: 1 }) + "k";
  return v.toLocaleString(nf(), { maximumFractionDigits: 1 });
}

/* Slider ends were printed at full precision — "-1.6822 .. 12.3364". */
const tidy = (v) => v == null ? "" :
  (Math.abs(v) >= 100 ? Math.round(v)
   : Math.abs(v) >= 10 ? +v.toFixed(1)
   : +v.toFixed(2)).toLocaleString(nf());

/* ── boot & language ────────────────────────────────────── */
async function boot() {
  PANEL = await (await fetch(`/api/panel?lang=${LANG}`)).json();
  document.documentElement.lang = LANG;
  $("roundLabel").textContent = PANEL.round;
  $("sourcesAsOf").textContent = `· ${t.sources_as_of} ${PANEL.sources_as_of}`;
  paintStatic();
  renderGateNav();
  renderDrivers();
  renderInert();
  renderSegTabs();
  renderDiagnostics();
  renderConfigRows();
  refreshJournal();
  await loadSources();
  if (typeof loadRoles === "function") await loadRoles();
  const allowed = (typeof rolePages === "function" && rolePages()) || null;
  if (allowed && !allowed.includes(GATE)) GATE = allowed[0];
  show(GATE);
  run();
}

function paintStatic() {
  const set = (id, key, html) => {
    const el = $(id); if (!el) return;
    if (html) el.innerHTML = t[key]; else el.textContent = t[key];
  };
  set("g0h", "g0_h"); set("g0lede", "g0_lede"); set("g0empty", "g0_empty");
  set("g1h", "g1_h"); set("g1lede", "g1_lede");
  set("g1inerth", "g1_inert_h"); set("g1inertlede", "g1_inert_lede");
  set("vh", "v_h"); set("vlede", "v_lede");
  set("approveAllBtn", "v_approve_all");
  set("runh", "run_h"); set("runlede", "run_lede");
  set("newRunBtn", "run_new"); set("logh", "run_log");
  set("g1bh", "g1b_h"); set("g1blede", "g1b_lede"); set("g1bwarn", "g1b_warn");
  set("ovChartH", "ov_chart_h"); set("ovChartSub", "ov_chart_sub");
  set("g2h", "g2_h"); set("g2lede", "g2_lede");
  set("g3h", "g3_h"); set("g3lede", "g3_lede"); set("g3editlabel", "g3_edit");
  set("pubh", "pub_h"); set("publede", "pub_lede");
  set("movedh", "moved_h"); set("movedlede", "moved_lede");
  set("diagh", "diag_h"); set("diaglede", "diag_lede");
  set("jh", "journal_h"); set("jlede", "journal_lede");
  set("honesth", "honest_h");
  set("honest1", "honest_1", true); set("honest2", "honest_2", true);
  set("honest3", "honest_3", true);
  set("resetBtn", "reset"); set("openRoundBtn", "g0_open");
  set("signoffBtn", "g2_signoff"); set("publishBtn", "pub_do");
  set("recheckBtn", "g3_recheck"); set("saveEditBtn", "g3_save");
  set("qClose", "close"); set("oCancel", "cancel"); set("oCommit", "ov_commit");
  set("ovCancel", "cancel"); set("ovCommit", "ov_commit2");
  set("ovSub", "ov_modal_sub"); set("ovKeep", "ov_keep2");
  set("ovModelL", "ov_model"); set("ovYoursL", "ov_yours_h");
  $("ovReason").placeholder = t.ov_ph2;
  set("rCancel", "cancel"); set("rConfirm", "g0_reject");
  set("oSub", "ov_sub"); set("oKeep", "ov_keep");
  set("oAgentL", "ov_agent"); set("oValueL", "ov_yours");
  $("oReason").placeholder = t.ov_ph;
  $("signoffReason").placeholder = t.g2_signoff_reason;
  $("editReason").placeholder = t.g3_reason;
  $("rReason").placeholder = t.g0_reason;
  $("rTitle").textContent = t.g0_reject;
  $("rSub").textContent = t.g0_lede;
}

document.querySelectorAll(".langsel button").forEach(b =>
  b.addEventListener("click", async () => {
    LANG = b.dataset.lang; t = T[LANG];
    localStorage.setItem("mimir.lang", LANG);
    document.querySelectorAll(".langsel button")
      .forEach(x => x.classList.toggle("on", x.dataset.lang === LANG));
    await boot();
  }));

/* ── gate router ────────────────────────────────────────── */
const GATES = [["0", "gate0"], ["verify", "verify"], ["1", "gate1"],
               ["1b", "gate1b"], ["2", "gate2"], ["3", "gate3"],
               ["pub", "pub"], ["run", "run"]];

function renderGateNav() {
  const allowed = (typeof rolePages === "function" && rolePages()) || null;
  $("gateNav").innerHTML = GATES
    .filter(([g]) => !allowed || allowed.includes(g))
    .map(([g, key]) =>
      `<span class="gate ${g === GATE ? "active" : ""}" data-gate="${g}">${t[key]}</span>`)
    .join("");
  $("gateNav").querySelectorAll(".gate").forEach(el =>
    el.addEventListener("click", () => show(el.dataset.gate)));
}

function show(g) {
  GATE = g;
  GATES.forEach(([x]) => { const v = $("view-" + x); if (v) v.hidden = x !== g; });
  renderGateNav();
  if (g === "verify") loadVerify();
  if (g === "run") loadRun();
  if (g === "1b") loadOverlay();
  if (g === "3") loadChapter();
  if (g === "pub") $("published").innerHTML = "";
}

/* ── gate 0 · sources ───────────────────────────────────── */
async function loadSources() {
  SOURCES = await (await fetch("/api/sources")).json();
  $("g0status").textContent = SOURCES.opened ? t.g0_opened : "";
  $("openRoundBtn").disabled = SOURCES.opened;
  // Rebuilt against the register the API actually returns. The previous
  // version still read cadence/latest/fetchable, which sources.py stopped
  // emitting when the register became derived — so two columns rendered empty
  // and every row falsely showed "upload task".
  $("sourceTable").innerHTML =
    `<tr>
       <th>${t.source}</th>
       <th data-tip="${esc(t.tip_tier)}">tier</th>
       <th>cluster</th>
       <th data-tip="${esc(t.tip_consensus)}">consensus</th>
       <th class="num" data-tip="${esc(t.tip_claims)}">claims</th>
       <th class="num">drivers</th>
       <th data-tip="${esc(t.tip_latest)}">latest</th>
       <th></th>
     </tr>` +
    SOURCES.sources.map(s => {
      const out = REJECTED.includes(s.key);
      const stale = s.age_days != null && s.age_days > 180;
      return `<tr style="${out ? "opacity:.45;text-decoration:line-through" : ""}">
        <td><b>${esc(s.name)}</b>
          ${s.reports && s.reports.length
            ? `<div class="prov">${esc(s.reports[0])}</div>` : ""}
          ${s.note ? `<div class="prov" style="color:var(--warn)">${esc(s.note)}</div>` : ""}</td>
        <td class="num">${s.tier == null ? "—" : s.tier}</td>
        <td class="num">${esc(s.cluster || "—")}</td>
        <td><span class="consb ${s.in_consensus ? "yes" : "no"}">${
          s.in_consensus ? "in" : "out"}</span></td>
        <td class="num">${s.claims}</td>
        <td class="num">${s.drivers_covered}</td>
        <td class="num">${esc(s.latest_published || "—")}
          ${s.age_days != null
            ? `<div class="age ${stale ? "stale" : ""}"${stale
                ? ` data-tip="${esc(t.tip_stale)}"` : ""}>${s.age_days} d</div>` : ""}</td>
        <td>${SOURCES.opened ? "" : out
          ? `<span class="pill no">${t.g0_rejected}</span>`
          : `<button class="ghost" style="padding:4px 9px;font-size:11.5px"
                     onclick="askReject('${s.key}')">${t.g0_reject}</button>`}</td>
      </tr>`;
    }).join("");

  const silent = $("g0silent");
  if (silent) {
    silent.innerHTML = SOURCES.silent.length
      ? `<b>${SOURCES.silent.length}</b> ${t.g0_silent}: ${
          SOURCES.silent.map(esc).join(", ")}<br>
         <span style="color:var(--muted)">${esc(SOURCES.silent_note)}</span>`
      : "";
  }
}

let REJECT_KEY = null;
function askReject(key) {
  REJECT_KEY = key;
  $("rReason").value = "";
  $("rTitle").textContent = `${t.g0_reject} · ${SOURCES.sources.find(s => s.key === key).name}`;
  $("rejectVeil").classList.add("on");
  $("rReason").focus();
}
$("rConfirm").addEventListener("click", () => {
  const reason = $("rReason").value.trim();
  if (!reason) { toast(t.need_reason, true); return; }
  REJECTED.push(REJECT_KEY);
  window._rejectReason = reason;
  $("rejectVeil").classList.remove("on");
  loadSources();
});
$("rCancel").addEventListener("click", () => $("rejectVeil").classList.remove("on"));

$("openRoundBtn").addEventListener("click", async () => {
  const res = await fetch("/api/open-round", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rejected: REJECTED, reason: window._rejectReason || "" }),
  });
  const out = await res.json();
  if (!res.ok) { toast(out.reason || out.error, true); return; }
  await loadSources(); refreshJournal();
  toast(t.g0_opened);
  show("1");
});

/* ── gate 1 · drivers ───────────────────────────────────── */
function renderDrivers() {
  $("drivers").innerHTML = PANEL.drivers.map(d => {
    const inst = d.institutions.filter(i => i.value != null)
      .map(i => `${esc(i.name)} <b>${i.value}</b>`).join(" · ");
    return `
    <div class="driver" data-key="${d.key}">
      <div class="d-head">
        <div><span class="d-label">${esc(d.label)}</span>
          <span class="d-unit">${d.year} · ${esc(d.unit)}</span>
          ${d.in_model ? "" : `<span class="pill no">${t.not_in_model}</span>`}</div>
        <span class="d-val" id="val-${d.key}">${d.agent}</span>
      </div>
      <div class="d-agent">${t.agent} <b>${d.agent}</b>${inst ? " · " + inst : ""}
        <button class="q-btn" onclick="showQuote('${d.key}')">${t.source}</button></div>
      <input type="range" id="sl-${d.key}" min="${d.lo}" max="${d.hi}"
             step="${d.step}" value="${d.agent}">
      <div class="d-scale"><span>${tidy(d.lo)}</span><span>${tidy(d.hi)}</span></div>
      ${d.effect ? `<div class="d-effect">${esc(d.effect)}</div>` : ""}
      ${d.warning ? `<div class="flag warn">${esc(d.warning)}</div>` : ""}
      ${d.efterproev && d.efterproev.length ? `<div class="flag efter">
        <b>efterprøv</b> · ${t.efter_note}
        ${d.efterproev.map(x => `<br>· ${esc(x)}`).join("")}</div>` : ""}
      <div class="row-btns" id="btns-${d.key}" style="display:none">
        <button class="primary" onclick="openOverride('${d.key}')">${t.commit}</button>
        <button class="ghost" onclick="resetOne('${d.key}')">${t.undo}</button>
      </div>
    </div>`;
  }).join("");

  PANEL.drivers.forEach(d => {
    const sl = $("sl-" + d.key);
    if (OVERRIDES[d.key] != null) sl.value = OVERRIDES[d.key];
    sl.addEventListener("input", (e) => {
      const v = parseFloat(e.target.value);
      OVERRIDES[d.key] = v;
      const changed = Math.abs(v - d.agent) > 1e-9;
      $("val-" + d.key).textContent = v.toFixed(d.step < 1 ? 2 : 0);
      $("val-" + d.key).classList.toggle("changed", changed);
      $("btns-" + d.key).style.display = changed ? "flex" : "none";
      schedule();
    });
  });
}

function renderInert() {
  $("inert").innerHTML = PANEL.inert.map(d => `
    <div class="driver inert">
      <div class="d-head">
        <div><span class="d-label">${esc(d.label)}</span>
          <span class="d-unit">${d.year} · ${esc(d.unit)}</span>
          <span class="pill no">${t.not_wired}</span></div>
        <span class="d-val">${d.agent}</span>
      </div>
      <div class="d-agent">${d.institutions.map(i =>
        `${esc(i.name)} <b>${i.value == null ? "–" : i.value}</b>
         <span style="opacity:.7">(${esc(i.published)})</span>`).join("<br>")}
        <button class="q-btn" onclick="showQuote('${d.key}')">${t.source}</button></div>
      <div class="d-effect">${esc(d.effect)}</div>
      <div class="flag bad">${esc(d.warning)}</div>
    </div>`).join("");
}

function renderSegTabs() {
  $("segTabs").innerHTML = Object.entries(PANEL.meta.segments).map(([k, label]) =>
    `<button data-seg="${esc(k)}" class="${k === SEGMENT ? "on" : ""}">${esc(label)}</button>`).join("");
  $("segTabs").querySelectorAll("button").forEach(b =>
    b.addEventListener("click", () => { SEGMENT = b.dataset.seg; renderSegTabs(); run(); }));
}

/* ── live forecast ──────────────────────────────────────── */
let timer = null;
function schedule() { clearTimeout(timer); timer = setTimeout(run, 30); }

async function run() {
  if (PENDING) PENDING.abort();
  PENDING = new AbortController();
  const t0 = performance.now();
  try {
    const res = await fetch("/api/forecast", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segment: SEGMENT, overrides: OVERRIDES, lang: LANG }),
      signal: PENDING.signal,
    });
    const d = await res.json();
    if (!res.ok) { toast(d.reason || d.error, true); return; }
    renderKpis(d); draw(d); drawAnnual(d); renderDecomp(d); renderAnnualTable(d);
    const rt = (performance.now() - t0).toFixed(1);
    $("liveInfo").innerHTML =
      `${t.live} <b>${d.compute_ms} ms</b> · ${t.roundtrip} <b>${rt} ms</b>
       · Tobin's Q 2026 ${d.tobins_q_2026} (${t.agent} ${d.tobins_q_2026_agent})
       · ${t.driver}: ${esc(d.fit.tobins_q_driver)}`;
  } catch (e) { if (e.name !== "AbortError") toast(e.message, true); }
}

function renderKpis(d) {
  const years = Object.keys(d.annual_forecast).map(Number).sort();
  const byYear = {};
  d.quarters.forEach((q, i) => {
    if (d.actual[i] == null) return;
    const y = +q.slice(0, 4); byYear[y] = (byYear[y] || 0) + d.actual[i];
  });
  $("kpis").innerHTML = years.map((yr, i) => {
    const v = d.annual_forecast[yr];
    const prev = i === 0 ? byYear[yr - 1] : d.annual_forecast[yr - 1];
    const yoy = prev ? (v / prev - 1) * 100 : null;
    const base = d.annual_baseline[yr];
    const vs = base ? (v / base - 1) * 100 : 0;
    return `<div class="kpi" data-tip="${esc(t.tip_kpi)}">
      <div class="yr">${yr} · ${t.forecast}</div>
      <div class="big"><span class="arrow" style="color:${yoy >= 0 ? "var(--ok)" : "var(--bad)"}">${
        yoy == null ? "" : (yoy >= 0 ? "▲" : "▼")}</span>${fmt(v)}</div>
      <div class="yoy ${yoy >= 0 ? "up" : "down"}">${yoy == null ? "" : sgn(yoy, 1) + "% y/y"}</div>
      <div class="vs">${Math.abs(vs) < 0.05 ? t.as_agent
        : `<span class="${vs > 0 ? "up" : "down"}">${sgn(vs, 1)}%</span> ${t.vs_agent}`}</div>
    </div>`;
  }).join("");
}

/* ── legend and hover, shared by both charts ────────────────────────────── */
function drawKey(id, items) {
  const host = $(id);
  if (!host) return;
  host.innerHTML = items.map(it => {
    const tip = it.tip ? ` data-tip="${esc(it.tip)}"` : "";
    if (it.kind === "swatch") {
      return `<span${tip}><i class="swatch"></i>${esc(it.label)}</span>`;
    }
    return `<span${tip}><svg viewBox="0 0 22 10" aria-hidden="true">
      <line x1="1" y1="5" x2="21" y2="5" stroke="${it.colour}"
        stroke-width="${it.width || 2}"
        ${it.dash ? `stroke-dasharray="${it.dash}"` : ""} /></svg>${esc(it.label)}</span>`;
  }).join("");
}

/* A crosshair and a readout. Without it the only way to read a quarter off
 * the chart was to estimate it against the gridlines. */
function attachChartHover(svg, d, g) {
  const ns = "http://www.w3.org/2000/svg";
  const layer = document.createElementNS(ns, "g");
  layer.setAttribute("pointer-events", "none");
  layer.style.opacity = "0";
  const rule = el("line", { y1: g.TT, y2: g.TT + g.ih, stroke: "#191a2e",
    "stroke-width": 1, "stroke-dasharray": "2 3", opacity: .5 });
  const dot = el("circle", { r: 3.5, fill: "#c2185b", stroke: "#fff",
    "stroke-width": 1.5 });
  const box = el("rect", { rx: 3, fill: "#191a2e", opacity: .96 });
  const l1 = el("text", { "font-size": 10.5, fill: "#fff",
    "font-family": "monospace" });
  const l2 = el("text", { "font-size": 10.5, fill: "#c9cade",
    "font-family": "monospace" });
  [rule, dot, box, l1, l2].forEach(n => layer.appendChild(n));
  svg.appendChild(layer);

  const hit = el("rect", { x: g.L, y: g.TT, width: g.W - g.L - g.R,
    height: g.ih, fill: "transparent" });
  svg.appendChild(hit);

  hit.addEventListener("mouseleave", () => { layer.style.opacity = "0"; });
  hit.addEventListener("mousemove", (ev) => {
    const r = svg.getBoundingClientRect();
    const px = (ev.clientX - r.left) / r.width * g.W;
    let i = Math.round((px - g.L) / (g.W - g.L - g.R) * (g.n - 1));
    i = Math.max(0, Math.min(g.n - 1, i));
    const v = d.forecast[i] != null ? d.forecast[i]
            : (d.actual[i] != null ? d.actual[i] : d.fitted[i]);
    if (v == null) { layer.style.opacity = "0"; return; }

    const isFc = d.forecast[i] != null;
    rule.setAttribute("x1", g.x(i)); rule.setAttribute("x2", g.x(i));
    dot.setAttribute("cx", g.x(i)); dot.setAttribute("cy", g.y(v));
    dot.setAttribute("fill", isFc ? "#c2185b" : "#191a2e");
    l1.textContent = `${d.quarters[i]}   ${fmt(v)}`;
    l2.textContent = isFc
      ? `${t.forecast}  ·  ${fmt(d.lo[i])} – ${fmt(d.hi[i])}`
      : (d.actual[i] != null ? t.actual : t.fitted);
    const w = Math.max(l1.textContent.length, l2.textContent.length) * 6.1 + 16;
    const flip = g.x(i) + w + 12 > g.W - g.R;
    const bx = flip ? g.x(i) - w - 10 : g.x(i) + 10;
    const by = Math.max(g.TT + 2, Math.min(g.y(v) - 30, g.TT + g.ih - 40));
    box.setAttribute("x", bx); box.setAttribute("y", by);
    box.setAttribute("width", w); box.setAttribute("height", 36);
    l1.setAttribute("x", bx + 8); l1.setAttribute("y", by + 15);
    l2.setAttribute("x", bx + 8); l2.setAttribute("y", by + 28);
    layer.style.opacity = "1";
  });
}

/* ── charts ─────────────────────────────────────────────── */
function el(name, attrs, text) {
  const n = document.createElementNS(NS, name);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (text != null) n.textContent = text;
  return n;
}

function draw(d) {
  const svg = $("chart"); svg.innerHTML = "";
  const W = 860, H = 340, L = 62, R = 14, TT = 16, B = 44;
  const iw = W - L - R, ih = H - TT - B;
  const n = d.quarters.length;
  const vals = [d.actual, d.fitted, d.forecast, d.lo, d.hi, d.baseline]
    .flat().filter(v => v != null);
  const scale = niceTicks(Math.max(...vals) * 1.04);
  const ymax = scale.top;
  const x = i => L + (i / (n - 1)) * iw;
  const y = v => TT + ih - (v / ymax) * ih;

  $("chartTitle").textContent = `${d.label} · ${t.chart_starts}`;
  $("chartSub").innerHTML =
    `<span class="chartsub">
       <span>${esc(d.unit)}</span><span class="sep">|</span>
       <span data-tip="${esc(t.tip_holdout)}">OLS ${t.holdout}
         <b>${d.fit.holdout_mape}%</b> · R² ${d.fit.r2}</span>
       <span class="sep">|</span>
       <span class="demo" data-tip="${esc(t.tip_demo)}">demo model</span>
     </span>
     <span class="prodnote">${t.v_production || "Production"}: ${esc(d.production)}</span>`;

  scale.ticks.forEach(v => {
    svg.appendChild(el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v),
      stroke: v === 0 ? "#dcdce6" : "#ecedf3", "stroke-width": 1 }));
    svg.appendChild(el("text", { x: L - 10, y: y(v) + 3.5, "text-anchor": "end",
      "font-size": 10.5, fill: "#6b6b7b", "font-family": "monospace" },
      axisLabel(v)));
  });
  let lastYear = null;
  d.quarters.forEach((q, i) => {
    const yr = q.slice(0, 4);
    if (yr !== lastYear && (+yr) % 2 === 0) {
      svg.appendChild(el("line", { x1: x(i), x2: x(i), y1: TT, y2: TT + ih,
        stroke: "#f4f4f8" }));
      svg.appendChild(el("text", { x: x(i), y: H - B + 17, "text-anchor": "middle",
        "font-size": 10.5, fill: "#6b6b7b", "font-family": "monospace" }, yr));
      lastYear = yr;
    }
  });
  const firstFc = d.forecast.findIndex(v => v != null);
  if (firstFc > 0) {
    svg.appendChild(el("line", { x1: x(firstFc), x2: x(firstFc), y1: TT, y2: TT + ih,
      stroke: "#b9bad0", "stroke-dasharray": "3 3" }));
    svg.appendChild(el("text", { x: x(firstFc) + 5, y: TT + 12, "font-size": 10.5,
      fill: "#6b6b7b" }, t.forecast + " →"));
  }
  const band = [];
  for (let i = 0; i < n; i++) if (d.hi[i] != null) band.push([x(i), y(d.hi[i])]);
  for (let i = n - 1; i >= 0; i--) if (d.lo[i] != null) band.push([x(i), y(d.lo[i])]);
  if (band.length) svg.appendChild(el("polygon",
    { points: band.map(p => p.join(",")).join(" "), fill: "#c2185b", opacity: .13 }));

  const line = (arr, stroke, width, dash) => {
    const pts = [];
    arr.forEach((v, i) => { if (v != null) pts.push(`${x(i)},${y(v)}`); });
    if (pts.length < 2) return;
    const p = el("polyline", { points: pts.join(" "), fill: "none", stroke,
      "stroke-width": width, "stroke-linejoin": "round" });
    if (dash) p.setAttribute("stroke-dasharray", dash);
    svg.appendChild(p);
  };
  line(d.fitted, "#b9bad0", 1.4);
  line(d.actual, "#191a2e", 1.9);
  line(d.baseline, "#8d8fa8", 1.6, "5 4");
  if (d.has_overlay) line(d.model_line, "#00897b", 1.8, "2 3");   // pre-overlay
  line(d.forecast, "#c2185b", 2.4);

  // The legend lives in HTML rather than inside the SVG. Laid out in the SVG
  // it was positioned by a character-count guess (32 + label.length * 6.1),
  // so gaps were uneven, it collided with the axis labels, and it could not
  // wrap on a narrow window.
  drawKey("chartKey", [
    { kind: "line", colour: "#191a2e", width: 2.4, label: t.actual,
      tip: t.tip_actual },
    { kind: "line", colour: "#b9bad0", width: 1.6, label: t.fitted,
      tip: t.tip_fitted },
    { kind: "line", colour: "#8d8fa8", width: 1.8, dash: "5 4", label: t.agent_line,
      tip: t.tip_agent_line },
    ...(d.has_overlay ? [{ kind: "line", colour: "#00897b", width: 1.8,
      dash: "2 3", label: t.ov_model, tip: t.tip_model_line }] : []),
    { kind: "line", colour: "#c2185b", width: 2.6, label: t.your_line,
      tip: t.tip_your_line },
    { kind: "swatch", label: t.band, tip: t.tip_band },
  ]);
  attachChartHover(svg, d, { L, R, TT, ih, W, x, y, n });
}

function drawAnnual(d) {
  const svg = $("annualChart"); svg.innerHTML = "";
  const years = Object.keys(d.annual_forecast).map(Number).sort();
  if (!years.length) return;
  const W = 860, H = 190, L = 62, R = 14, TT = 14, B = 32;
  const iw = W - L - R, ih = H - TT - B;
  const scale = niceTicks(Math.max(...years.flatMap(y =>
    [d.annual_forecast[y], d.annual_baseline[y]])) * 1.12, 4);
  const ymax = scale.top;
  const bw = iw / years.length;
  const y = v => TT + ih - (v / ymax) * ih;
  scale.ticks.forEach(v => {
    svg.appendChild(el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v),
      stroke: v === 0 ? "#dcdce6" : "#f2f2f7" }));
    svg.appendChild(el("text", { x: L - 10, y: y(v) + 3.5, "text-anchor": "end",
      "font-size": 10, fill: "#8a8a9a", "font-family": "monospace" },
      axisLabel(v)));
  });
  years.forEach((yr, i) => {
    const cx = L + bw * i + bw / 2, w = Math.min(46, bw * 0.3);
    const bl = d.annual_baseline[yr], fc = d.annual_forecast[yr];
    svg.appendChild(el("rect", { x: cx - w - 3, y: y(bl), width: w,
      height: TT + ih - y(bl), fill: "#8d8fa8", rx: 2 }));
    svg.appendChild(el("rect", { x: cx + 3, y: y(fc), width: w,
      height: TT + ih - y(fc), fill: "#c2185b", rx: 2 }));
    const pct = bl ? (fc / bl - 1) * 100 : 0;
    svg.appendChild(el("text", { x: cx, y: Math.min(y(bl), y(fc)) - 6,
      "text-anchor": "middle", "font-size": 11, "font-weight": 600,
      fill: Math.abs(pct) < 0.05 ? "#6b6b7b" : (pct > 0 ? "#1f6f43" : "#b3261e"),
      "font-family": "monospace" }, Math.abs(pct) < 0.05 ? "—" : sgn(pct, 1) + "%"));
    svg.appendChild(el("text", { x: cx, y: H - B + 17, "text-anchor": "middle",
      "font-size": 11, fill: "#6b6b7b", "font-family": "monospace" }, yr));
  });
  svg.appendChild(el("line", { x1: L, x2: W - R, y1: TT + ih, y2: TT + ih,
    stroke: "#e2e2ea" }));
  drawKey("annualKey", [
    { kind: "line", colour: "#8d8fa8", width: 8, label: t.agent_fc,
      tip: t.tip_agent_bar },
    { kind: "line", colour: "#c2185b", width: 8, label: t.your_fc,
      tip: t.tip_your_bar },
  ]);
}

function renderDecomp(d) {
  const rows = [["Tobin's Q", d.decomposition.tobins_q, ""],
                [t.gate1.includes("granskning") ? "Realränta" : "Real mortgage rate",
                 d.decomposition.rate, "pp"]];
  const maxAbs = Math.max(2, ...rows.map(r => Math.abs(r[1].effect_pct)));
  $("decomp").innerHTML = rows.map(([nm, r, u]) => {
    const half = 50 * Math.abs(r.effect_pct) / maxAbs, neg = r.effect_pct < 0;
    return `<div class="decomp-row">
      <div class="nm">${nm}<div class="dl">b = ${r.coef.toFixed(4)}</div></div>
      <div class="dl">${sgn(r.delta, 3)} ${u}</div>
      <div class="bar-track"><div class="zero"></div>
        <div class="bar ${neg ? "neg" : ""}" style="left:${neg ? 50 - half : 50}%;width:${half}%"></div></div>
      <div class="ef ${r.effect_pct > 0 ? "up" : (r.effect_pct < 0 ? "down" : "")}">${sgn(r.effect_pct, 2)}%</div>
    </div>`;
  }).join("") + (d.decomposition.overlay && d.decomposition.overlay.years.length ? `
    <div class="decomp-row" style="border-top:1px dashed var(--line);margin-top:4px;padding-top:8px">
      <div class="nm">${t.ov_yours_h}<div class="dl">${t.ov_judgement}</div></div>
      <div class="dl">${d.decomposition.overlay.years.join(", ")}</div>
      <div class="bar-track"><div class="zero"></div>
        <div class="bar" style="background:#00897b;left:${
          d.decomposition.overlay.effect_pct < 0
            ? 50 - Math.min(50, Math.abs(d.decomposition.overlay.effect_pct) * 2) : 50
        }%;width:${Math.min(50, Math.abs(d.decomposition.overlay.effect_pct) * 2)}%"></div></div>
      <div class="ef ${d.decomposition.overlay.effect_pct > 0 ? "up" : "down"}">${
        sgn(d.decomposition.overlay.effect_pct, 2)}%</div>
    </div>` : "") + `
    <div class="decomp-row decomp-net">
      <div class="nm"><b>${t.net}</b></div><div></div><div></div>
      <div class="ef ${d.decomposition.net_with_overlay_pct > 0 ? "up"
        : (d.decomposition.net_with_overlay_pct < 0 ? "down" : "")}">
        ${sgn(d.decomposition.net_with_overlay_pct, 2)}%</div></div>`;
}

function renderAnnualTable(d) {
  const years = Object.keys(d.annual_forecast).map(Number).sort();
  $("annualTable").innerHTML =
    `<tr><th>${t.annual_total}</th>${years.map(y => `<th>${y}</th>`).join("")}</tr>
     <tr><td>${t.agent_fc}</td>${years.map(y => `<td class="num">${fmt(d.annual_baseline[y])}</td>`).join("")}</tr>
     <tr><td>${t.your_fc}</td>${years.map(y => `<td class="num"><b>${fmt(d.annual_forecast[y])}</b></td>`).join("")}</tr>
     <tr><td>${t.diff}</td>${years.map(y => {
        const p = (d.annual_forecast[y] / d.annual_baseline[y] - 1) * 100;
        return `<td class="num ${Math.abs(p) < 0.05 ? "" : (p > 0 ? "up" : "down")}">${
          Math.abs(p) < 0.05 ? "—" : sgn(p, 1) + "%"}</td>`;
      }).join("")}</tr>`;
}

/* ── gate 1b · the analyst overlay ──────────────────────── */
let OV = null;

async function loadOverlay() {
  const q = new URLSearchParams({ segment: SEGMENT, lang: LANG });
  OV = await (await fetch("/api/overlay?" + q)).json();

  $("ovSegTabs").innerHTML = Object.entries(PANEL.meta.segments).map(([k, label]) =>
    `<button data-seg="${esc(k)}" class="${k === SEGMENT ? "on" : ""}">${esc(label)}</button>`).join("");
  $("ovSegTabs").querySelectorAll("button").forEach(b =>
    b.addEventListener("click", () => {
      SEGMENT = b.dataset.seg; renderSegTabs(); loadOverlay(); run();
    }));

  const byYear = {};
  OV.adjustments.forEach(a => { byYear[a.year] = a; });
  const years = Object.keys(OV.model).map(Number).sort();

  $("overlayTable").innerHTML =
    `<tr><th>${esc(OV.unit)}</th>${years.map(y => `<th>${y}</th>`).join("")}</tr>
     <tr><td>${t.ov_model}</td>${years.map(y =>
        `<td class="num">${fmt(OV.model[y])}</td>`).join("")}</tr>
     <tr><td>${t.ov_yours_h}</td>${years.map(y => `<td class="num">${
        byYear[y] ? `<b style="color:var(--magenta)">${fmt(byYear[y].analyst_value)}</b>` : "—"
     }</td>`).join("")}</tr>
     <tr><td>${t.diff}</td>${years.map(y => `<td class="num ${
        byYear[y] ? (byYear[y].delta_pct > 0 ? "up" : "down") : ""}">${
        byYear[y] ? sgn(byYear[y].delta_pct, 1) + "%" : "—"}</td>`).join("")}</tr>
     <tr><td></td>${years.map(y => `<td class="num">
        <button class="ghost" style="padding:4px 8px;font-size:11px"
                onclick="askOverlay(${y})">${t.ov_set}</button>${
        byYear[y] ? `<br><button class="ghost"
                style="padding:3px 7px;font-size:10.5px;margin-top:3px"
                onclick="clearOverlay(${y})">${t.ov_clear}</button>` : ""}</td>`).join("")}</tr>`;

  $("overlayList").innerHTML = OV.adjustments.length
    ? OV.adjustments.map(a => `<div style="padding:8px 0;border-top:1px solid var(--line)">
        <b>${a.year}</b> <span style="font-family:var(--mono)">${fmt(a.model_value)} → ${
          fmt(a.analyst_value)} (${sgn(a.delta_pct, 1)}%)</span>
        <span class="pill no">${t.ov_judgement}</span>
        <br><span style="color:var(--muted)">&ldquo;${esc(a.reason)}&rdquo;</span>
        <br><span style="font-size:11px;color:var(--muted)">${a.ts}</span></div>`).join("")
    : t.ov_none;

  drawOverlayChart();
}

async function drawOverlayChart() {
  const res = await fetch("/api/forecast", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment: SEGMENT, overrides: OVERRIDES, lang: LANG }),
  });
  const d = await res.json();
  if (!res.ok) return;

  const svg = $("ovChart"); svg.innerHTML = "";
  const W = 860, H = 300, L = 62, R = 14, TT = 16, B = 40;
  const iw = W - L - R, ih = H - TT - B;
  const pts = d.quarters.map((q, i) => i).filter(i => d.forecast[i] != null);
  if (pts.length < 2) return;
  const vals = pts.flatMap(i => [d.forecast[i], d.model_line[i]]).filter(v => v != null);
  const ymax = Math.max(...vals) * 1.12, ymin = Math.min(...vals) * 0.88;
  const x = k => L + ((k - pts[0]) / (pts[pts.length - 1] - pts[0])) * iw;
  const y = v => TT + ih - ((v - ymin) / (ymax - ymin)) * ih;

  for (let k = 0; k <= 4; k++) {
    const v = ymin + (ymax - ymin) * k / 4;
    svg.appendChild(el("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), stroke: "#ecedf3" }));
    svg.appendChild(el("text", { x: L - 8, y: y(v) + 4, "text-anchor": "end",
      "font-size": 10.5, fill: "#6b6b7b", "font-family": "monospace" },
      v >= 1000 ? (v / 1000).toFixed(1) + "k" : v.toFixed(0)));
  }
  let lastYear = null;
  pts.forEach(i => {
    const yr = d.quarters[i].slice(0, 4);
    if (yr !== lastYear) {
      svg.appendChild(el("text", { x: x(i), y: H - B + 17, "text-anchor": "middle",
        "font-size": 11, fill: "#6b6b7b", "font-family": "monospace" }, yr));
      lastYear = yr;
    }
  });
  const line = (key, stroke, width, dash) => {
    const pp = pts.filter(i => d[key][i] != null).map(i => `${x(i)},${y(d[key][i])}`);
    if (pp.length < 2) return;
    const e = el("polyline", { points: pp.join(" "), fill: "none", stroke,
      "stroke-width": width, "stroke-linejoin": "round" });
    if (dash) e.setAttribute("stroke-dasharray", dash);
    svg.appendChild(e);
  };
  line("model_line", "#8d8fa8", 1.8, "5 4");
  line("forecast", "#c2185b", 2.6);

  let lx = L;
  [["#8d8fa8", t.ov_model, "5 4"], ["#c2185b", t.ov_yours_h, ""]].forEach(([c, lb, dash]) => {
    const ln = el("line", { x1: lx, x2: lx + 20, y1: H - 8, y2: H - 8,
      stroke: c, "stroke-width": 2.4 });
    if (dash) ln.setAttribute("stroke-dasharray", dash);
    svg.appendChild(ln);
    svg.appendChild(el("text", { x: lx + 25, y: H - 4.5, "font-size": 10.5,
      fill: "#6b6b7b" }, lb));
    lx += 34 + lb.length * 6.2;
  });
}

let OV_YEAR = null;
async function askOverlay(year) {
  OV_YEAR = year;
  const cur = OV.adjustments.find(a => a.year === year);
  const mv = OV.model[year];
  $("ovTitle").textContent = `${t.ov_title} · ${OV.segment} · ${year}`;
  $("ovModel").textContent = fmt(mv);
  $("ovValue").value = cur ? cur.analyst_value : Math.round(mv);
  $("ovYours").textContent = fmt(parseFloat($("ovValue").value));
  $("ovReason").value = cur ? cur.reason : "";
  $("ovGuard").className = "flag note";
  $("ovGuard").textContent = "";
  $("ovValue").oninput = () => {
    $("ovYours").textContent = fmt(parseFloat($("ovValue").value) || 0);
  };
  $("overlayVeil").classList.add("on");
  $("ovValue").focus();
}
$("ovCancel").addEventListener("click", () => $("overlayVeil").classList.remove("on"));

$("ovCommit").addEventListener("click", async () => {
  const res = await fetch("/api/overlay", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment: SEGMENT, year: OV_YEAR,
                           value: parseFloat($("ovValue").value),
                           reason: $("ovReason").value, overrides: OVERRIDES }),
  });
  const out = await res.json();
  if (!res.ok) {
    $("ovGuard").className = "flag bad";
    $("ovGuard").textContent = "✗ " + (out.reason || out.error);
    return;
  }
  $("overlayVeil").classList.remove("on");
  toast(t.committed);
  await loadOverlay(); refreshJournal(); run();
});

async function clearOverlay(year) {
  await fetch("/api/overlay", {
    method: "DELETE", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment: SEGMENT, year }),
  });
  await loadOverlay(); refreshJournal(); run();
}

/* ── gate 2 · config rows ───────────────────────────────── */
function renderConfigRows() {
  $("configRows").innerHTML = PANEL.diagnostics.map(d => `
    <div class="cfg" data-seg="${esc(d.segment)}">
      <div class="nm">${esc(d.label)}</div>
      <div class="fields">
        <label>${t.g2_driver}
          <select data-f="tobins_q">${PANEL.tq_choices.map(c =>
            `<option ${c === d.spec.tobins_q ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></label>
        <label>${t.g2_transform}
          <select data-f="tq_transform">
            <option value="level" ${d.spec.tq_transform === "level" ? "selected" : ""}>level</option>
            <option value="sq" ${d.spec.tq_transform === "sq" ? "selected" : ""}>sq</option>
          </select></label>
        <label><input type="checkbox" data-f="use_rate" ${d.spec.use_rate ? "checked" : ""}> ${t.g2_rate}</label>
        <label><input type="checkbox" data-f="seasonals" ${d.spec.seasonals ? "checked" : ""}> ${t.g2_seasonals}</label>
        <span class="mape">${t.holdout} ${d.holdout_mape}% · R² ${d.r2}</span>
        <button class="primary" style="padding:6px 12px;font-size:12px"
                onclick="applyConfig('${esc(d.segment)}')">${t.g2_apply}</button>
      </div>
    </div>`).join("");
}

async function applyConfig(seg) {
  const row = $("configRows").querySelector(`.cfg[data-seg="${seg}"]`);
  const body = { segment: seg };
  row.querySelectorAll("[data-f]").forEach(el => {
    body[el.dataset.f] = el.type === "checkbox" ? el.checked : el.value;
  });
  const res = await fetch("/api/config", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const out = await res.json();
  if (!res.ok) { toast(out.error, true); return; }
  PANEL.diagnostics = out.diagnostics;
  renderConfigRows(); renderDiagnostics(); refreshJournal();
  const better = out.after.holdout_mape < out.before.holdout_mape;
  toast(`${t.holdout} ${out.before.holdout_mape}% → ${out.after.holdout_mape}%` +
        (better ? " ✓" : " —") + (out.signs_ok ? "" : "  ⚠ signs wrong"), !out.signs_ok);
  if (SEGMENT === seg) run();
}

function renderDiagnostics() {
  $("diagTable").innerHTML =
    `<tr><th>${t.segment}</th><th>n</th><th>${t.sample}</th><th>R²</th>
        <th>${t.holdout}</th><th>b Tobin's Q</th><th>b rate</th><th>${t.signs}</th></tr>` +
    PANEL.diagnostics.map(d => `<tr>
      <td>${esc(d.label)}</td><td class="num">${d.n}</td><td class="num">${d.sample}</td>
      <td class="num">${d.r2}</td><td class="num">${d.holdout_mape}%</td>
      <td class="num">${sgn(d.b_tobins_q, 3)}</td>
      <td class="num">${sgn(d.b_rate, 3)}</td>
      <td>${d.sign_tobins_q_ok && d.sign_rate_ok
        ? `<span style="color:var(--ok)">${t.signs_ok}</span>`
        : `<span style="color:var(--bad)">${t.signs_bad}</span>`}</td></tr>`).join("");
}

$("signoffBtn").addEventListener("click", async () => {
  const res = await fetch("/api/signoff", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: $("signoffReason").value }),
  });
  const out = await res.json();
  if (!res.ok) { toast(out.reason || out.error, true); return; }
  refreshJournal(); toast(t.g2_signoff + " ✓"); show("3");
});

/* ── gate 3 · the chapter ───────────────────────────────── */
async function loadChapter() {
  const res = await fetch("/api/chapter", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment: SEGMENT, overrides: OVERRIDES, lang: LANG }),
  });
  CHAPTER = await res.json();
  paintChapter(CHAPTER);
  $("chapterEdit").value = CHAPTER.paragraphs.join("\n\n");
}

function markup(text, bounds) {
  return esc(text).replace(/\[(\d+)\]/g, (m, n) => {
    const b = bounds.find(x => x.marker === `[${n}]`);
    return `<sup title="${esc(b ? b.binding : "no binding")}">[${n}]</sup>`;
  });
}

function paintChapter(ch) {
  $("chapterBox").innerHTML =
    `<div class="chapter">${ch.paragraphs.map(p =>
      `<p>${markup(p, ch.bounds)}</p>`).join("")}</div>
     <div class="bindings">${ch.bounds.map(b =>
      `<b>${b.marker}</b> ${b.value} — ${esc(b.binding)}
       <span class="pill">${b.kind}</span>`).join("<br>")}</div>`;
  paintCheck(ch.check);
  $("styleNotes").innerHTML = `<b>${t.g3_style}</b><br>` +
    ch.style_notes.map(s => "· " + esc(s)).join("<br>") +
    `<br><br><b>${esc(ch.assembled_by)}</b>`;
}

function paintCheck(c) {
  $("checkFlag").className = "flag " + (c.ok ? "note" : "bad");
  $("checkFlag").innerHTML = (c.ok ? "✓ " : "✗ ") + esc(c.verdict) +
    (c.naked_numbers.length ? `<br>naked: ${c.naked_numbers.map(esc).join(", ")}` : "") +
    (c.unbound_markers.length ? `<br>unbound: ${c.unbound_markers.join(", ")}` : "");
}

$("recheckBtn").addEventListener("click", async () => {
  const res = await fetch("/api/chapter", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment: SEGMENT, overrides: OVERRIDES, lang: LANG,
                           edited: $("chapterEdit").value }),
  });
  const ch = await res.json();
  paintCheck(ch.check);
});

$("saveEditBtn").addEventListener("click", async () => {
  const res = await fetch("/api/edit", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ section: "house_prices",
                           original: CHAPTER.paragraphs.join("\n\n"),
                           edited: $("chapterEdit").value,
                           reason: $("editReason").value }),
  });
  const out = await res.json();
  if (!res.ok) { toast(out.reason || out.error, true); return; }
  refreshJournal();
  toast(`${t.g3_save} ✓ → style rule ${out.next_style_rule}`);
  show("pub");
});

/* ── publish ────────────────────────────────────────────── */
$("publishBtn").addEventListener("click", async () => {
  const edited = $("chapterEdit").value.trim();
  const res = await fetch("/api/publish", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segment: SEGMENT, overrides: OVERRIDES, lang: LANG,
                           edited: edited || null }),
  });
  const p = await res.json();
  if (!res.ok) {
    $("published").innerHTML = `<div class="flag bad" style="margin-top:14px">
      <b>${t.pub_refused}</b><br>${esc(p.check.verdict)}
      ${p.check.naked_numbers.length ? `<br>naked: ${p.check.naked_numbers.map(esc).join(", ")}` : ""}
    </div>`;
    return;
  }
  $("published").innerHTML = `
    <div class="checks" style="margin:16px 0 14px">
      <span class="ok">✓</span> p3 check — ${p.check.bound} ${t.pub_bound}<br>
      <span class="ok">✓</span> 43 style rules enforced<br>
      <span class="ok">✓</span> ${t.pub_sources}
    </div>
    <div class="chapter">${p.paragraphs.map(x => `<p>${markup(x, p.bounds)}</p>`).join("")}</div>
    <h2 style="margin-top:20px">${t.pub_sources}</h2>
    <div class="srclist">${p.sources.map(s =>
      `<span class="kind">${s.kind}</span>${esc(s.binding)}`).join("<br>")}</div>`;
  refreshJournal();
});

/* ── journal ────────────────────────────────────────────── */
async function refreshJournal() {
  const j = await (await fetch("/api/journal")).json();
  if (!j.entries.length) { $("journal").textContent = t.journal_empty; return; }
  $("journal").innerHTML = j.entries.slice(-8).reverse().map(e =>
    `<div style="padding:7px 0;border-top:1px solid var(--line)">
      <b>${t.gate0.split("·")[0].trim()} ${e.gate} · ${esc(e.label || e.section || e.segment || e.event)}</b>
      ${e.agent_proposed != null
        ? ` <span style="font-family:var(--mono)">${e.agent_proposed} → ${e.analyst_value}</span>` : ""}
      ${e.holdout_mape_before != null
        ? ` <span style="font-family:var(--mono)">MAPE ${e.holdout_mape_before} → ${e.holdout_mape_after}</span>` : ""}
      ${e.reason ? `<br><span style="color:var(--muted)">&ldquo;${esc(e.reason)}&rdquo;</span>` : ""}
      <br><span style="font-size:11px;color:var(--muted)">${e.ts}</span>
    </div>`).join("") +
    (j.repeated.length ? `<div class="flag warn">${t.repeated}: ${
      j.repeated.map(r => `${esc(r.driver)} (${r.times}×)`).join(", ")}. ${t.repeated_note}</div>` : "");
}

/* ── quote & override modals ────────────────────────────── */
function showQuote(key) {
  const d = PANEL.drivers.find(x => x.key === key) || PANEL.inert.find(x => x.key === key);
  $("qTitle").textContent = `${d.label} · ${d.year} · ${d.agent} ${d.unit}`;
  $("qSub").textContent = d.in_model ? d.effect : t.not_used;
  $("qQuote").innerHTML = d.quote ? esc(d.quote)
    : `<span style="color:var(--muted)">${t.no_quote}</span>`;
  const inst = d.institutions.map(i =>
    `<b>${esc(i.name)}</b> ${i.value == null ? "–" : i.value} · ${esc(i.published)}${
      i.note ? " — " + esc(i.note) : ""}`).join("<br>");
  $("qMeta").innerHTML =
    `<b>${t.source}</b><br>${esc(d.source)}<br><br>` +
    (inst ? `<b>${t.institutions}</b><br>${inst}<br><br>` : "") +
    (d.efterproev && d.efterproev.length
      ? `<b>efterprøv</b><br>${d.efterproev.map(esc).join("<br>")}<br><br>` : "") +
    `<b>${t.guard}</b><br>` + (d.hard_lo != null || d.hard_hi != null
      ? `hard_lo ${d.hard_lo ?? "–"} · hard_hi ${d.hard_hi ?? "–"} (${t.declared_in_config})`
      : t.no_bounds);
  $("quoteVeil").classList.add("on");
}
$("qClose").addEventListener("click", () => $("quoteVeil").classList.remove("on"));

let CURRENT = null;
async function openOverride(key) {
  const d = PANEL.drivers.find(x => x.key === key);
  CURRENT = key;
  const v = OVERRIDES[key];
  $("oTitle").textContent = `${t.ov_h} · ${d.label} · ${d.year}`;
  $("oAgent").textContent = d.agent;
  $("oValue").textContent = v.toFixed(2);
  $("oReason").value = "";
  const g = await (await fetch(
    `/api/guard?driver=${key}&value=${v}&lang=${LANG}`, { method: "POST" })).json();
  $("oGuard").className = "flag " + (g.ok ? (g.kind === "warned" ? "warn" : "note") : "bad");
  $("oGuard").innerHTML = (g.ok ? "✓ " : "✗ ") + esc(g.reason);
  $("oCommit").disabled = !g.ok;
  $("overrideVeil").classList.add("on");
  $("oReason").focus();
}
$("oCancel").addEventListener("click", () => $("overrideVeil").classList.remove("on"));

$("oCommit").addEventListener("click", async () => {
  const res = await fetch("/api/decision", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gate: "1", driver: CURRENT, value: OVERRIDES[CURRENT],
                           reason: $("oReason").value.trim(), lang: LANG }),
  });
  const out = await res.json();
  if (!res.ok) { toast(out.reason || out.error, true); return; }
  $("overrideVeil").classList.remove("on");
  toast(t.committed); refreshJournal();
});

function resetOne(key) {
  const d = PANEL.drivers.find(x => x.key === key);
  $("sl-" + key).value = d.agent;
  $("sl-" + key).dispatchEvent(new Event("input"));
}
$("resetBtn").addEventListener("click", () => {
  OVERRIDES = {};
  PANEL.drivers.forEach(d => {
    $("sl-" + d.key).value = d.agent;
    $("val-" + d.key).textContent = d.agent;
    $("val-" + d.key).classList.remove("changed");
    $("btns-" + d.key).style.display = "none";
  });
  run();
});

let toastTimer = null;
function toast(msg, bad) {
  const el = $("toast");
  el.textContent = msg;
  el.className = "toast on" + (bad ? " bad" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.className = "toast", 4600);
}

document.addEventListener("keydown", e => {
  if (e.key !== "Escape") return;
  ["quoteVeil", "overrideVeil", "rejectVeil", "overlayVeil"].forEach(id => $(id).classList.remove("on"));
});

document.querySelectorAll(".langsel button")
  .forEach(x => x.classList.toggle("on", x.dataset.lang === LANG));

// verify.js loads after this file and defines the gate-1 and run views, so
// boot has to wait for it rather than run at parse time.
window.addEventListener("DOMContentLoaded", boot);


/* ── gate 1 verification & run monitor: the two page-level buttons ──────── */
$("approveAllBtn").addEventListener("click", async () => {
  const res = await fetch("/api/research/approve-all", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ only_unmoved: true }),
  });
  const out = await res.json();
  toast(`${out.approved} ${t.v_approved} · ${out.skipped_no_estimate.length} ${t.v_no_estimate}`);
  await loadVerify();
  if (VSEL) await selectDriver(VSEL);
  refreshJournal();
});

$("newRunBtn").addEventListener("click", async () => {
  await fetch("/api/run/new", { method: "POST" });
  loadRun();
});
