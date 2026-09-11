/* Gate 1 — market-driver verification, and the run monitor.
 *
 * Three things this page does that the first pilot did not:
 *
 *   · an assumption per forecast year, because the evidence differs by year
 *   · every source behind each assumption — institution, tier, value, weight,
 *     publication date, report title, page, verbatim quote and a link
 *   · NO forecast anywhere on it. Approving a driver should not be steered by
 *     watching a forecast line move while you do it.
 *
 * Excluded claims are shown, not hidden. A source carried at weight zero with
 * a stated reason is information; a source quietly dropped is a black box.
 */

let VIX = null, VSEL = null, VCARD = null, RUN = null;

/* ── the driver list ────────────────────────────────────── */
async function loadVerify() {
  VIX = await (await fetch(`/api/research?lang=${LANG}`)).json();
  if (VIX.error) { $("driverList").textContent = VIX.error; return; }
  paintProgress();

  const byGroup = {};
  VIX.drivers.forEach(d => (byGroup[d.group] = byGroup[d.group] || []).push(d));
  $("driverList").innerHTML = VIX.groups.map(g => `
    <div class="ghead">${esc(g.label)} · ${g.n}</div>
    ${(byGroup[g.id] || []).map(d => `
      <div class="drow ${d.id === VSEL ? "on" : ""}" data-id="${esc(d.id)}">
        <span class="nm">${esc(d.label)}
          <div class="prov">${esc(d.provenance)}${
            d.in_model ? " · " + t.v_in_model : " · " + t.v_report_only}</div></span>
        <span class="st ${d.state}" data-tip="${esc(t["tip_state_" + d.state] || "")}"
              >${esc((d.state || "").replace("_", " "))}</span>
      </div>`).join("")}`).join("");

  $("driverList").querySelectorAll(".drow").forEach(r =>
    r.addEventListener("click", () => selectDriver(r.dataset.id)));

  if (!VSEL && VIX.drivers.length) selectDriver(VIX.drivers[0].id);
}

function paintProgress() {
  const p = VIX.progress;
  $("vProgress").innerHTML =
    `<span><b>${p.drivers_approved}</b> ${t.v_of} ${p.drivers_total} ${t.v_drivers} ${t.v_approved}</span>
     <span><b>${p.cells_approved}</b> ${t.v_of} ${p.cells_total} ${t.v_cells}</span>
     <span><b>${p.moved}</b> ${t.v_moved}</span>
     ${p.carried_by_hand ? `<span><b>${p.carried_by_hand}</b> ${t.v_carried}</span>` : ""}
     ${p.no_estimate.length ? `<span style="color:var(--bad)"><b>${p.no_estimate.length}</b> ${t.v_no_estimate}</span>` : ""}`;
}

async function selectDriver(id) {
  VSEL = id;
  $("driverList").querySelectorAll(".drow").forEach(r =>
    r.classList.toggle("on", r.dataset.id === id));
  VCARD = await (await fetch(
    `/api/research/driver?driver_id=${encodeURIComponent(id)}&lang=${LANG}`)).json();
  paintDriver();
}

/* ── one driver: its definition, then a block per year ──── */
function paintDriver() {
  const c = VCARD;
  if (!c || c.error) { $("driverPane").innerHTML = t.v_pick; return; }
  const la = c.last_actual || {};

  $("driverPane").innerHTML = `
    <div class="card">
      <h2>${esc(c.label)}</h2>
      <p class="lede">${esc(c.unit)} · ${esc(c.layer)} driver
        ${c.in_model ? `<span class="pill">${t.v_in_model} · ${esc(c.engine_column || "")}</span>`
                     : `<span class="pill">${t.v_report_only}</span>`}</p>
      <div class="meta-grid">
        ${c.definition ? `<b>${esc(c.definition)}</b><br>` : ""}
        ${la.period ? `${t.v_latest_actual}: <b>${la.period} · ${la.value}</b><br>` : ""}
        ${c.derived_from.length ? `${t.v_derived}: ${c.derived_from.map(esc).join(", ")}<br>` : ""}
        ${c.used_by_segments.length ? `${t.v_used_by}: ${c.used_by_segments.length}<br>` : ""}
        ${c.cited_in_sections.length ? `${t.v_cited_in}: ${c.cited_in_sections.map(esc).join(", ")}` : ""}
      </div>
    </div>
    ${c.years.map(y => yearBlock(c, y)).join("")}`;

  c.years.forEach(y => {
    const inp = $(`ov-${y.year}`);
    if (inp) inp.addEventListener("input", () => {
      const me = $(`me-${y.year}`);
      if (me && y.slider && y.slider.min != null) {
        const f = (parseFloat(inp.value) - y.slider.min) /
                  (y.slider.max - y.slider.min);
        me.style.left = `${Math.max(0, Math.min(1, f)) * 100}%`;
      }
    });
  });
}

function yearBlock(c, y) {
  const a = y.approval;
  const noEst = y.central === null || y.central === undefined;
  const sl = y.slider || {};
  const span = (sl.max != null && sl.min != null) ? (sl.max - sl.min) : 0;
  const pos = v => span ? Math.max(0, Math.min(1, (v - sl.min) / span)) * 100 : 50;

  const chips = (y.claims || []).filter(cl => !cl.excluded && cl.value != null);

  return `
  <div class="card">
    <div class="yhead">
      <span class="yr">${y.year}</span>
      ${noEst ? `<span class="qual C">${t.v_no_estimate}</span>`
              : `<span class="central">${fmt(y.central, 2)}</span>
                 <span class="qual ${esc(y.quality_grade || "")}"
                       data-tip="${esc(y.quality_reason || t.tip_quality)}">${t.v_quality} ${
                   esc(y.quality_grade || "?")} · ${esc(y.quality_label || "")}</span>
                 <span class="prov">${y.n_sources} ${y.n_sources === 1 ? "source" : "sources"}</span>`}
      ${a ? `<span class="st ${a.moved ? "moved" : "approved"}">${
        a.moved ? t.v_moved : t.v_approved}</span>` : ""}
    </div>

    ${y.quality_reason ? `<p class="lede" style="margin:6px 0 0">${esc(y.quality_reason)}</p>` : ""}
    ${y.coverage_note ? `<div class="flag warn">${esc(y.coverage_note)}</div>` : ""}
    ${noEst ? `<div class="flag bad">${t.v_no_est_help}</div>` : ""}

    ${!noEst && span ? `
    <div class="band">
      <div class="track"></div>
      ${y.p10 != null && y.p90 != null
        ? `<div class="p" style="left:${pos(y.p10)}%;width:${pos(y.p90) - pos(y.p10)}%"></div>` : ""}
      ${chips.map(cl => `<div class="tick" style="left:${pos(cl.value)}%"
             title="${esc(cl.source_name)}: ${fmt(cl.value, 2)}"></div>`).join("")}
      <div class="tick" style="left:${pos(y.central)}%;background:var(--magenta);width:3px"
           title="${t.v_agent_est}: ${fmt(y.central, 2)}"></div>
      <div class="me" id="me-${y.year}" style="left:${pos(a ? a.analyst_value : y.central)}%"
           title="${t.ov_yours_h}"></div>
      <div class="chip lo">${fmt(sl.min, 2)}</div>
      <div class="chip hi">${fmt(sl.max, 2)}</div>
    </div>
    <div class="bandkey">
      ${y.p10 != null ? `<span data-tip="${esc(t.tip_band_p)}"><i class="p10"></i>p10–p90</span>` : ""}
      <span data-tip="${esc(t.tip_band_inst)}"><i class="inst"></i>${
        chips.length} ${chips.length === 1 ? "institution" : "institutions"}</span>
      <span data-tip="${esc(t.tip_band_agent)}"><i class="agent"></i>${t.v_agent_est}</span>
      <span data-tip="${esc(t.tip_band_mine)}"><i class="mine"></i>${t.ov_yours_h}</span>
      <span style="margin-left:auto;font-family:var(--mono)">${esc(sl.basis || "")}</span>
    </div>` : ""}

    <div class="estrow">
      <div class="fld">
        <label for="ov-${y.year}">${y.year} · ${esc(c.unit)}</label>
        <input type="number" id="ov-${y.year}" class="wide" style="max-width:130px"
               step="0.01" value="${a ? a.analyst_value : (noEst ? "" : y.central)}">
      </div>
      <div class="fld grow">
        <label for="rs-${y.year}">${t.v_reason_label}</label>
        <input type="text" id="rs-${y.year}" class="wide" placeholder="${t.v_reason_ph}"
               value="${a ? esc(a.reason) : ""}">
      </div>
      <div class="acts">
        ${noEst ? "" : `<button class="ghost" onclick="acceptYear(${y.year})"
            data-tip="${esc(t.v_no_reason_needed)}">${t.v_accept}</button>`}
        <button class="primary" onclick="moveYear(${y.year})">${t.v_move}</button>
        ${a ? `<button class="ghost" onclick="clearYear(${y.year})">${t.v_clear}</button>` : ""}
      </div>
    </div>
    <div class="flag note" id="msg-${y.year}" style="display:none"></div>

    <h2 style="margin-top:16px">${t.v_sources} · ${y.year} · ${(y.claims || []).length}</h2>
    ${sourceTable(y)}
  </div>`;
}

function sourceTable(y) {
  if (!(y.claims || []).length) return `<p class="lede">—</p>`;
  const maxW = Math.max(...y.claims.map(c => c.weight || 0), 0.0001);
  return `<table class="srctab">
    <tr>
      <th class="c-inst">${t.v_institution}</th>
      <th class="c-val">${t.v_value}</th>
      <th class="c-wt" data-tip="${esc(t.tip_weight)}">${t.v_weight}</th>
      <th class="c-pub" data-tip="${esc(t.tip_latest)}">${t.v_published}</th>
      <th class="c-rep">${t.v_report}</th>
    </tr>
    ${y.claims.map(c => {
      const stale = c.age_days != null && c.age_days > 180;
      const loc = [c.page ? `p. ${c.page}` : "", c.table_ref ? esc(c.table_ref) : ""]
                    .filter(Boolean).join(" · ");
      return `
      <tr class="${c.excluded ? "ex" : ""}">
        <td class="c-inst">${esc(c.source_name)}<span class="tierb"
              data-tip="${esc(t.tip_tier)}">T${c.tier}</span>
          ${c.excluded ? `<div class="prov" style="color:var(--bad)">${t.v_excluded}${
            c.excluded_reason ? " — " + esc(String(c.excluded_reason).slice(0, 150)) : ""}</div>` : ""}</td>
        <td class="c-val">${fmt(c.value, 2)}</td>
        <td class="c-wt"><span class="wwrap">
            <span class="wtrack"><i style="width:${
              Math.round(100 * (c.weight || 0) / maxW)}%"></i></span>
            <span class="wpct">${((c.weight || 0) * 100).toFixed(1)}%</span></span></td>
        <td class="c-pub"><span class="pub">${esc(c.published_at || "—")}</span>
          ${c.age_days != null ? `<div class="age ${stale ? "stale" : ""}"${
            stale ? ` data-tip="${esc(t.tip_stale)}"` : ""}>${c.age_days} d</div>` : ""}</td>
        <td class="c-rep"><span class="rep">${c.report_url
              ? `<a href="${esc(c.report_url)}" target="_blank" rel="noopener"
                    >${esc(c.report_title || "report")}</a>`
              : esc(c.report_title || "—")}</span>
            ${loc ? `<span class="loc"> · ${loc}</span>` : ""}
            ${c.quote ? `<div class="q tip-left" data-tip="${esc(t.tip_quote)}"
                 ><b>${t.v_quote}</b>${esc(String(c.quote).slice(0, 200))}</div>` : ""}</td>
      </tr>`;
    }).join("")}
  </table>`;
}

/* ── approving ──────────────────────────────────────────── */
async function sendApproval(year, value, reason) {
  const body = { driver_id: VSEL, year, reason: reason || "" };
  if (value !== null) body.value = value;
  const res = await fetch("/api/research/approve", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const out = await res.json();
  const msg = $(`msg-${year}`);
  if (!res.ok) {
    if (msg) { msg.style.display = "block"; msg.className = "flag bad";
               msg.textContent = "✗ " + (out.reason || out.error); }
    return false;
  }
  await loadVerify(); await selectDriver(VSEL); refreshJournal();
  return true;
}

const acceptYear = (year) => sendApproval(year, null, "");
const moveYear = (year) => sendApproval(
  year, parseFloat($(`ov-${year}`).value), $(`rs-${year}`).value);

async function clearYear(year) {
  await fetch(`/api/research/approve?driver_id=${encodeURIComponent(VSEL)}&year=${year}`,
              { method: "DELETE" });
  await loadVerify(); await selectDriver(VSEL);
}

/* ── the run monitor ────────────────────────────────────── */
async function loadRun() {
  RUN = await (await fetch("/api/run")).json();
  const tt = RUN.totals;
  $("runKpis").innerHTML = `
    <div class="kpi"><div class="yr">${t.run_status}</div>
      <div class="big" style="font-size:17px">${esc(RUN.current || t.run_done)}</div></div>
    <div class="kpi"><div class="yr">steps</div>
      <div class="big">${tt.done}<span style="font-size:14px;color:var(--muted)">/${tt.steps}</span></div></div>
    <div class="kpi"><div class="yr">elapsed</div>
      <div class="big">${tt.elapsed_ms}<span style="font-size:13px;color:var(--muted)"> ms</span></div></div>
    <div class="kpi"><div class="yr">${t.run_cost}</div>
      <div class="big">$${tt.cost_usd.toFixed(2)}</div>
      <div class="vs">${tt.tokens} tokens</div></div>`;
  $("runNote").textContent = RUN.durability;

  $("stepTable").innerHTML =
    `<tr><th></th><th>${t.run_step_col}</th><th>owner</th><th>${t.run_ms}</th>
        <th>${t.run_attempts}</th><th>log</th><th></th></tr>` +
    RUN.steps.map(s => `<tr>
      <td class="st-cell"><span class="sdot ${s.status}"></span></td>
      <td>${esc(s.title)}<div class="prov">${esc(s.id)} · ${esc(s.kind)}${
        s.reads.length ? " · reads " + s.reads.map(esc).join(", ") : ""}</div></td>
      <td class="num">${esc(s.owner)}</td>
      <td class="num">${s.ms == null ? "—" : s.ms}</td>
      <td class="num">${s.attempts || "—"}</td>
      <td class="prov">${s.error ? `<span style="color:var(--bad)">${esc(s.error)}</span>`
        : esc(s.logs.length ? s.logs[s.logs.length - 1].msg.slice(0, 90) : "")}</td>
      <td style="white-space:nowrap">
        ${s.kind === "gate" && s.status !== "done"
          ? `<button class="ghost" style="padding:3px 8px;font-size:11px"
                     onclick="passGate('${s.id}')">${t.run_pass}</button>`
          : `<button class="ghost" style="padding:3px 8px;font-size:11px"
                     onclick="runStep('${s.id}')">${t.run_step}</button>`}
        <button class="ghost" style="padding:3px 8px;font-size:11px"
                onclick="resetFrom('${s.id}')">↺</button>
      </td></tr>`).join("");

  $("runEvents").innerHTML = RUN.events.length
    ? RUN.events.slice().reverse().map(e =>
        `<div style="padding:4px 0;border-top:1px solid var(--line)">
          <span style="font-family:var(--mono);font-size:11px;color:var(--muted)">${e.ts}</span>
          ${e.level === "error" ? `<span style="color:var(--bad)"> ${esc(e.msg)}</span>`
                                : " " + esc(e.msg)}</div>`).join("")
    : "—";
  $("runNote").textContent = RUN.cost_note;
}

async function runStep(id) {
  await fetch("/api/run/step", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ step_id: id }) });
  loadRun();
}
async function passGate(id) {
  await fetch("/api/run/step", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ step_id: id, note: "__pass__" }) });
  loadRun();
}
async function resetFrom(id) {
  await fetch("/api/run/reset", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ step_id: id }) });
  loadRun();
}

/* ── roles ──────────────────────────────────────────────── */
let ROLE = "analyst", ROLEDEF = null;

async function loadRoles() {
  ROLEDEF = await (await fetch(`/api/roles?lang=${LANG}`)).json();
  ROLE = ROLEDEF.current;
  $("roleSel").innerHTML = ROLEDEF.roles.map(r =>
    `<button data-role="${r.id}" class="${r.id === ROLE ? "on" : ""}"
             title="${esc(r.may.join(" · "))}">${esc(r.label)}</button>`).join("");
  $("roleSel").querySelectorAll("button").forEach(b =>
    b.addEventListener("click", async () => {
      await fetch("/api/role", { method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: b.dataset.role }) });
      await loadRoles();
      renderGateNav();
      const allowed = ROLEDEF.roles.find(r => r.id === ROLE).pages;
      if (!allowed.includes(GATE)) show(allowed[0]);
    }));
}

function rolePages() {
  if (!ROLEDEF) return null;
  const r = ROLEDEF.roles.find(x => x.id === ROLE);
  return r ? r.pages : null;
}
