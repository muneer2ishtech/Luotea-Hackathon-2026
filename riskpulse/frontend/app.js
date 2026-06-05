let chartInstance = null;
let currentBuilding = null;
let currentRole = "owner";
let cachedPayload = null;

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const ROLE_META = {
  owner: { label: "Owner / Investor", focus: "Value growth, returns, ESG — portfolio visibility" },
  manager: { label: "Property Manager", focus: "Efficiency, situational awareness, cost control" },
  technician: { label: "Field Technician", focus: "Task prioritization, clear instructions, fast response" },
};

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function severityClass(sev) {
  return `severity-${sev || "low"}`;
}

function levelClass(level) {
  return `level-${level || "normal"}`;
}

function setRole(role) {
  currentRole = role;
  $$(".role-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.role === role);
  });
  $$(".role-view").forEach((view) => {
    view.hidden = view.id !== `view-${role}`;
  });
  const meta = ROLE_META[role];
  $("#role-label").textContent = meta.label;
  $("#role-focus").textContent = meta.focus;
  document.body.dataset.role = role;
}

function renderOwner(aud) {
  const o = aud.owner;
  $("#owner-headline").textContent = o.headline;
  $("#owner-subtitle").textContent = o.subtitle;

  const pm = o.primary_metric;
  $("#reliability-grade").textContent = pm.grade;
  $("#reliability-index").textContent = pm.value;
  $("#reliability-expl").textContent = pm.explanation;
  $("#reliability-card").className = `reliability-card grade-${pm.grade.toLowerCase()}`;

  $("#owner-kpis").innerHTML = o.kpis
    .map(
      (k) => `
    <div class="kpi-tile ${k.bad ? "alert" : ""}">
      <div class="kpi-value">${k.value}</div>
      <div class="kpi-label">${k.label}</div>
      <div class="kpi-context">${k.context}</div>
    </div>`
    )
    .join("");

  const tbody = $("#portfolio-table tbody");
  tbody.innerHTML = o.portfolio
    .map(
      (p) => `
    <tr class="${p.id === currentBuilding ? "current-asset" : ""}">
      <td><strong>${p.name}</strong></td>
      <td>${p.reliability_index ?? "—"}</td>
      <td><span class="grade-badge grade-${(p.grade || "b").toLowerCase()}">${p.grade || "—"}</span></td>
      <td>${p.risk_score ?? "—"}</td>
      <td><span class="status-pill ${levelClass(p.level)}">${p.label || p.level}</span></td>
    </tr>`
    )
    .join("");

  $("#esg-list").innerHTML = o.esg_summary
    .map(
      (e) => `
    <li>
      <span class="esg-status ${e.status === "on track" ? "ok" : "warn"}">${e.status}</span>
      <strong>${e.metric}</strong>
      <span class="esg-note">${e.note}</span>
    </li>`
    )
    .join("");

  $("#owner-decisions").innerHTML = o.decisions
    .map(
      (d) => `
    <article class="decision-card">
      <h3>${d.title}</h3>
      <p>${d.summary}</p>
      <p class="impact"><strong>Impact:</strong> ${d.impact}</p>
    </article>`
    )
    .join("");
}

function renderManager(aud, analysis, buildingId) {
  const m = aud.manager;
  $("#manager-headline").textContent = m.headline;
  $("#manager-subtitle").textContent = m.subtitle;
  $("#situation-bar").textContent = m.situation_summary;

  const card = $("#score-card");
  card.className = `score-card level-${analysis.level}`;
  $("#risk-score").textContent = Math.round(analysis.score);
  $("#risk-label").textContent = analysis.label;

  $("#efficiency-card").innerHTML =
    m.efficiency.length > 0
      ? `<h3>Efficiency snapshot</h3><ul>${m.efficiency
          .map(
            (e) =>
              `<li class="${e.alert ? "alert" : ""}"><strong>${e.value}</strong> ${e.label}</li>`
          )
          .join("")}</ul>`
      : `<h3>Efficiency snapshot</h3><p class="muted">Work order metrics available for industrial sites.</p>`;

  const ul = $("#signals");
  ul.innerHTML = m.signals
    .map(
      (s) => `
    <li>
      <div class="signal-title">
        <span class="${severityClass(s.severity)}">${s.severity}</span>
        ${s.title}
      </div>
      <div class="signal-detail">${s.detail}</div>
    </li>`
    )
    .join("");

  if (m.calendar) {
    $("#calendar-panel").hidden = false;
    $("#calendar-desc").textContent = m.calendar.recommendation;
    $("#calendar-sample").innerHTML = m.calendar.sample
      .map((c) => `<li>${c}</li>`)
      .join("");
  } else {
    $("#calendar-panel").hidden = true;
  }

  $("#manager-actions").innerHTML = m.actions
    .map(
      (a) => `
    <article class="action-card">
      <div class="priority">${a.priority}</div>
      <h3>${a.title}</h3>
      <p class="reason">${a.reason}</p>
      <ol>${(a.steps || []).map((s) => `<li>${s}</li>`).join("")}</ol>
      <p class="vs"><strong>Why now:</strong> ${a.vs_reactive || a.impact || ""}</p>
    </article>`
    )
    .join("");

  renderChart(m.chart || analysis.weekly_chart, buildingId);
}

function renderTechnician(aud) {
  const t = aud.technician;
  $("#tech-headline").textContent = t.headline;
  $("#tech-subtitle").textContent = t.subtitle;
  $("#tech-risk-context").textContent = t.risk_context;

  const ctx = $("#field-context");
  if (t.field_context?.length) {
    ctx.innerHTML = t.field_context
      .map(
        (c) => `
      <div class="context-card">
        <span class="context-type">${c.type}</span>
        <span class="context-loc">${c.location}</span>
        <p>${c.text}</p>
        <time>${c.time}</time>
      </div>`
      )
      .join("");
    ctx.hidden = false;
  } else {
    ctx.hidden = true;
  }

  $("#task-list").innerHTML = t.tasks
    .map(
      (task) => `
    <article class="task-card">
      <div class="task-header">
        <span class="task-rank">#${task.rank}</span>
        <span class="task-priority">${task.priority}</span>
      </div>
      <h3>${task.title}</h3>
      <p class="task-location">📍 ${task.location}</p>
      <p class="task-why"><strong>Why now:</strong> ${task.why_now}</p>
      <ol class="task-checklist">${task.checklist.map((s) => `<li>${s}</li>`).join("")}</ol>
      <p class="task-done"><strong>Done when:</strong> ${task.done_when}</p>
    </article>`
    )
    .join("");
}

function renderChart(chartData, buildingId) {
  if (!chartData?.weeks?.length) return;

  const isCo2 = buildingId === "aurora_house";
  $("#chart-desc").textContent = isCo2
    ? "Daily average CO₂ vs baseline — act before comfort complaints."
    : "Weekly alarms vs baseline — spikes mean reallocate capacity this week.";

  const ctx = $("#risk-chart").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  const labels = chartData.weeks.map((w) => w.slice(5));
  const baseline = chartData.baseline_median;
  const upper = chartData.upper_band;

  chartInstance = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: isCo2 ? "Avg CO₂ (ppm)" : "Alarms / week",
          data: chartData.counts,
          borderColor: "#2d6a4f",
          backgroundColor: "rgba(45, 106, 79, 0.12)",
          fill: true,
          tension: 0.3,
          pointRadius: 3,
        },
        {
          label: "Baseline",
          data: labels.map(() => baseline),
          borderColor: "#95a5a6",
          borderDash: [6, 4],
          pointRadius: 0,
        },
        {
          label: "Elevated",
          data: labels.map(() => upper),
          borderColor: "#e76f51",
          borderDash: [2, 2],
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: !isCo2,
          title: { display: true, text: isCo2 ? "ppm" : "Count" },
        },
      },
    },
  });

  $("#chart-legend").innerHTML = `
    <span><i style="background:#2d6a4f"></i> Actual</span>
    <span><i style="background:#95a5a6"></i> Baseline (~${baseline})</span>
    <span><i style="background:#e76f51"></i> Elevated (~${upper})</span>
  `;
}

function renderAll(payload) {
  cachedPayload = payload;
  const { analysis, audiences } = payload;
  renderOwner(audiences);
  renderManager(audiences, analysis, currentBuilding);
  renderTechnician(audiences);
}

async function loadBuilding(buildingId) {
  document.body.classList.add("loading");
  try {
    const data = await fetchJson(`/api/buildings/${buildingId}/analysis`);
    currentBuilding = buildingId;
    renderAll(data);
  } catch (err) {
    console.error(err);
    $("#risk-label").textContent = "Error — run preprocess.py first";
  } finally {
    document.body.classList.remove("loading");
  }
}

async function init() {
  $$(".role-tab").forEach((btn) => {
    btn.addEventListener("click", () => setRole(btn.dataset.role));
  });
  setRole("owner");

  try {
    const index = await fetchJson("/api/buildings");
    const select = $("#building");
    (index.buildings || []).forEach((b) => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.name;
      select.appendChild(opt);
    });

    select.addEventListener("change", () => loadBuilding(select.value));

    const defaultId = index.buildings?.[0]?.id || "lentokentankatu_11";
    select.value = defaultId;
    await loadBuilding(defaultId);
  } catch (err) {
    console.error(err);
  }
}

init();
