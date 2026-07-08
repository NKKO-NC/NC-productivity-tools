const state = {
  asOfDate: "",
  graph: { nodes: [], edges: [] },
  summary: null,
  selectedNodeId: null,
  selectedEdgeId: null,
  zoom: 1,
  searchResults: [],
  importPreview: null,
};

const elements = {
  asOfDate: document.getElementById("asOfDate"),
  searchInput: document.getElementById("searchInput"),
  statsGrid: document.getElementById("statsGrid"),
  searchResults: document.getElementById("searchResults"),
  graphStage: document.getElementById("graphStage"),
  edgeLayer: document.getElementById("edgeLayer"),
  nodeLayer: document.getElementById("nodeLayer"),
  detailPanel: document.getElementById("detailPanel"),
  importText: document.getElementById("importText"),
  importPreview: document.getElementById("importPreview"),
  companyForm: document.getElementById("companyForm"),
  edgeForm: document.getElementById("edgeForm"),
  zoomRange: document.getElementById("zoomRange"),
  exportCsvButton: document.getElementById("exportCsvButton"),
  exportTxtButton: document.getElementById("exportTxtButton"),
  exportDbButton: document.getElementById("exportDbButton"),
  resetDemoButton: document.getElementById("resetDemoButton"),
};

async function boot() {
  const summary = await fetchJson(`/api/summary`);
  state.summary = summary;
  state.asOfDate = summary.as_of_date;
  elements.asOfDate.value = state.asOfDate;
  await refreshGraph();
  bindEvents();
  render();
}

function bindEvents() {
  elements.asOfDate.addEventListener("change", async () => {
    state.asOfDate = elements.asOfDate.value;
    await refreshGraph();
    render();
  });

  elements.searchInput.addEventListener("input", debounce(async () => {
    const q = elements.searchInput.value.trim();
    if (!q) {
      state.searchResults = [];
      renderSearchResults();
      return;
    }
    const payload = await fetchJson(`/api/search?q=${encodeURIComponent(q)}&as_of=${state.asOfDate}`);
    state.searchResults = payload.results;
    renderSearchResults();
  }, 250));

  document.getElementById("previewImportButton").addEventListener("click", previewImport);
  document.getElementById("applyImportButton").addEventListener("click", applyImport);

  elements.companyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(elements.companyForm).entries());
    await postJson("/api/company", payload);
    await refreshGraph();
    elements.companyForm.reset();
    elements.companyForm.company_id.value = "";
    elements.companyForm.valid_from.value = state.asOfDate;
  });

  elements.edgeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(elements.edgeForm).entries());
    await postJson("/api/edge", payload);
    await refreshGraph();
    elements.edgeForm.reset();
    elements.edgeForm.change_date.value = state.asOfDate;
  });

  elements.zoomRange.addEventListener("input", () => {
    state.zoom = Number(elements.zoomRange.value);
    elements.graphStage.style.transform = `scale(${state.zoom})`;
  });

  elements.exportCsvButton.addEventListener("click", () => {
    window.location.href = "/api/export/csv";
  });
  elements.exportTxtButton.addEventListener("click", () => {
    window.location.href = "/api/export/txt";
  });
  elements.exportDbButton.addEventListener("click", () => {
    window.location.href = "/api/export/db";
  });
  elements.resetDemoButton.addEventListener("click", async () => {
    if (!confirm("這會重設目前 DB 為內建 demo 資料，是否繼續？")) {
      return;
    }
    await postJson("/api/reset-demo", {});
    elements.searchInput.value = "";
    state.searchResults = [];
    await refreshGraph();
    render();
  });
}

async function refreshGraph() {
  state.summary = await fetchJson(`/api/summary?as_of=${state.asOfDate}`);
  state.graph = await fetchJson(`/api/graph?as_of=${state.asOfDate}`);
  elements.companyForm.valid_from.value = state.asOfDate;
  elements.edgeForm.change_date.value = state.asOfDate;
}

function render() {
  renderStats();
  renderSearchResults();
  renderGraph();
  renderDetail();
}

function renderStats() {
  const stats = state.summary;
  const boxes = [
    ["公司數", stats.company_count],
    ["投資線數", stats.edge_count],
    ["缺地區", stats.missing_region_count],
    ["可切換日期", stats.available_dates.length],
  ];
  elements.statsGrid.innerHTML = boxes.map(([label, value]) => `
    <div class="stat-box">
      <span>${label}</span>
      <strong>${value}</strong>
    </div>
  `).join("");
}

function renderSearchResults() {
  if (!state.searchResults.length) {
    elements.searchResults.className = "search-results empty";
    elements.searchResults.textContent = elements.searchInput.value.trim()
      ? "沒有命中結果。"
      : "輸入關鍵字後顯示結果。";
    return;
  }
  elements.searchResults.className = "search-results";
  elements.searchResults.innerHTML = state.searchResults.map((item) => `
    <div class="search-item">
      <button type="button" data-company-id="${item.company_id}">
        <strong>${escapeHtml(item.short_name || item.full_name || item.company_code || item.company_id)}</strong><br>
        <span>${escapeHtml(item.company_code || item.company_id)} · ${escapeHtml(item.region || "未填地區")}</span>
      </button>
    </div>
  `).join("");
  elements.searchResults.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      selectNode(button.dataset.companyId);
      scrollNodeIntoView(button.dataset.companyId);
    });
  });
}

function renderGraph() {
  const nodesById = Object.fromEntries(state.graph.nodes.map((node) => [node.company_id, node]));
  elements.edgeLayer.innerHTML = "";
  elements.nodeLayer.innerHTML = "";
  for (const edge of state.graph.edges) {
    const parent = nodesById[edge.parent_company_id];
    const child = nodesById[edge.child_company_id];
    if (!parent || !child) continue;
    const x1 = parent.x + 210;
    const y1 = parent.y + 54;
    const x2 = child.x;
    const y2 = child.y + 54;
    const midX = (x1 + x2) / 2;
    const midY = (y1 + y2) / 2 - 10;
    const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
    const visibleLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    visibleLine.setAttribute("x1", x1);
    visibleLine.setAttribute("y1", y1);
    visibleLine.setAttribute("x2", x2);
    visibleLine.setAttribute("y2", y2);
    visibleLine.setAttribute("class", `edge-line ${state.selectedEdgeId === edge.edge_id ? "selected" : ""}`);
    const hitLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
    hitLine.setAttribute("x1", x1);
    hitLine.setAttribute("y1", y1);
    hitLine.setAttribute("x2", x2);
    hitLine.setAttribute("y2", y2);
    hitLine.setAttribute("class", "edge-hit");
    hitLine.addEventListener("click", () => selectEdge(edge.edge_id));
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", midX);
    label.setAttribute("y", midY);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("class", "edge-label");
    label.textContent = edge.ownership_pct_label;
    group.appendChild(visibleLine);
    group.appendChild(hitLine);
    group.appendChild(label);
    elements.edgeLayer.appendChild(group);
  }
  for (const node of state.graph.nodes) {
    const el = document.createElement("button");
    el.type = "button";
    el.className = `node ${state.selectedNodeId === node.company_id ? "selected" : ""}`;
    el.style.left = `${node.x}px`;
    el.style.top = `${node.y}px`;
    el.dataset.companyId = node.company_id;
    el.innerHTML = `
      <div class="node-header">
        <div>
          <div class="node-title">${escapeHtml(node.label)}</div>
          <div class="node-code">${escapeHtml(node.company_code || node.company_id)}</div>
        </div>
        <span class="badge" style="background:${node.color}">${escapeHtml(node.region || "未填地區")}</span>
      </div>
      <div class="node-meta">
        <span>${escapeHtml(node.full_name || "未填全稱")}</span>
        <span>${escapeHtml(node.main_business || "未填主營項目")}</span>
        <span>${escapeHtml(node.currency || "未填幣別")}</span>
      </div>
      ${node.missing_fields.length ? `<div class="node-warning">缺少：${node.missing_fields.join("、")}</div>` : ""}
    `;
    el.addEventListener("click", () => selectNode(node.company_id));
    makeNodeDraggable(el, node);
    elements.nodeLayer.appendChild(el);
  }
}

async function selectNode(companyId) {
  state.selectedNodeId = companyId;
  state.selectedEdgeId = null;
  renderGraph();
  await renderDetail();
  fillCompanyForm(companyId);
}

async function selectEdge(edgeId) {
  state.selectedEdgeId = edgeId;
  state.selectedNodeId = null;
  renderGraph();
  await renderDetail();
}

async function renderDetail() {
  if (state.selectedNodeId) {
    const detail = await fetchJson(`/api/company/${state.selectedNodeId}?as_of=${state.asOfDate}`);
    const profile = detail.profile;
    elements.detailPanel.className = "detail-panel";
    elements.detailPanel.innerHTML = `
      <h3>${escapeHtml(profile.short_name || profile.full_name || profile.company_code || profile.company_id)}</h3>
      <div class="detail-grid">
        <div>公司 ID</div><div>${escapeHtml(profile.company_id)}</div>
        <div>公司代碼</div><div>${escapeHtml(profile.company_code || "")}</div>
        <div>公司全稱</div><div>${escapeHtml(profile.full_name || "")}</div>
        <div>主營項目</div><div>${escapeHtml(profile.main_business || "")}</div>
        <div>所在地區</div><div>${escapeHtml(profile.region || "")}</div>
        <div>使用幣別</div><div>${escapeHtml(profile.currency || "")}</div>
        <div>有效期間</div><div>${escapeHtml(profile.valid_from)} ~ ${escapeHtml(profile.valid_to || "現在")}</div>
      </div>
      <div class="section-title">Alias 歷史</div>
      ${detail.aliases.map((alias) => `
        <div class="history-item">${escapeHtml(alias.alias_type)} · ${escapeHtml(alias.alias_value)}<br><span class="muted">${escapeHtml(alias.valid_from)} ~ ${escapeHtml(alias.valid_to || "現在")}</span></div>
      `).join("")}
      <div class="section-title">Profile 版本</div>
      ${detail.history.map((item) => `
        <div class="history-item">${escapeHtml(item.valid_from)} ~ ${escapeHtml(item.valid_to || "現在")} · ${escapeHtml(item.short_name || item.full_name || item.company_code)}</div>
      `).join("")}
    `;
    return;
  }
  if (state.selectedEdgeId) {
    const edge = await fetchJson(`/api/edge/${state.selectedEdgeId}`);
    elements.detailPanel.className = "detail-panel";
    elements.detailPanel.innerHTML = `
      <h3>投資關係</h3>
      <div class="detail-grid">
        <div>Edge ID</div><div>${escapeHtml(edge.edge_id)}</div>
        <div>母公司</div><div>${escapeHtml(edge.parent_company_id)}</div>
        <div>子公司</div><div>${escapeHtml(edge.child_company_id)}</div>
        <div>變更日期</div><div>${escapeHtml(edge.change_date)}</div>
        <div>持股比</div><div>${edge.ownership_pct == null ? "" : `${(edge.ownership_pct * 100).toFixed(1)}%`}</div>
        <div>投資股數</div><div>${escapeHtml(edge.investment_shares ?? "")}</div>
        <div>總股數</div><div>${escapeHtml(edge.child_total_shares ?? "")}</div>
        <div>備註</div><div>${escapeHtml(edge.note || "")}</div>
      </div>
    `;
    return;
  }
  elements.detailPanel.className = "detail-panel empty";
  elements.detailPanel.textContent = "點選公司卡或投資線後，在這裡查看資料與版本歷史。";
}

async function fillCompanyForm(companyId) {
  const detail = await fetchJson(`/api/company/${companyId}?as_of=${state.asOfDate}`);
  const profile = detail.profile;
  for (const [key, value] of Object.entries(profile)) {
    const field = elements.companyForm.elements.namedItem(key);
    if (field) field.value = value || "";
  }
  elements.companyForm.elements.namedItem("valid_from").value = state.asOfDate;
}

async function previewImport() {
  const payload = await postJson("/api/import/preview", { text: elements.importText.value });
  state.importPreview = payload;
  renderImportPreview();
}

async function applyImport() {
  const payload = await postJson("/api/import/apply", { text: elements.importText.value }, true);
  state.importPreview = payload.preview;
  renderImportPreview();
  if (payload.status === "applied") {
    elements.importText.value = "";
    await refreshGraph();
    render();
  }
}

function renderImportPreview() {
  const preview = state.importPreview;
  if (!preview) {
    elements.importPreview.className = "import-preview empty";
    elements.importPreview.textContent = "尚未建立預覽。";
    return;
  }
  const newCompanies = preview.changes?.new_companies?.length || 0;
  const newEdges = preview.changes?.edge_records?.length || 0;
  const newProfiles = preview.changes?.company_records?.length || 0;
  elements.importPreview.className = "import-preview";
  elements.importPreview.innerHTML = `
    <div class="preview-line"><strong>模式</strong> ${escapeHtml(preview.mode)}</div>
    <div class="preview-line"><strong>列數</strong> ${preview.row_count}</div>
    <div class="preview-line"><strong>即將新增公司</strong> ${newCompanies}</div>
    <div class="preview-line"><strong>即將新增投資線</strong> ${newEdges}</div>
    <div class="preview-line"><strong>即將新增/更新公司版本</strong> ${newProfiles}</div>
    ${preview.errors.map((item) => `<div class="preview-line message-error">${escapeHtml(item)}</div>`).join("")}
    ${preview.warnings.map((item) => `<div class="preview-line message-warning">${escapeHtml(item)}</div>`).join("")}
    ${preview.infos.map((item) => `<div class="preview-line message-info">${escapeHtml(item)}</div>`).join("")}
  `;
}

function makeNodeDraggable(element, node) {
  let pointerId = null;
  let startX = 0;
  let startY = 0;
  let originX = node.x;
  let originY = node.y;
  element.addEventListener("pointerdown", (event) => {
    pointerId = event.pointerId;
    startX = event.clientX;
    startY = event.clientY;
    originX = node.x;
    originY = node.y;
    element.setPointerCapture(pointerId);
  });
  element.addEventListener("pointermove", (event) => {
    if (pointerId !== event.pointerId) return;
    const dx = (event.clientX - startX) / state.zoom;
    const dy = (event.clientY - startY) / state.zoom;
    node.x = Math.max(20, originX + dx);
    node.y = Math.max(20, originY + dy);
    renderGraph();
  });
  const finish = async (event) => {
    if (pointerId !== event.pointerId) return;
    element.releasePointerCapture(pointerId);
    pointerId = null;
    await postJson("/api/layout", {
      positions: [{ company_id: node.company_id, x: node.x, y: node.y, pinned: true }],
    });
  };
  element.addEventListener("pointerup", finish);
  element.addEventListener("pointercancel", finish);
}

function scrollNodeIntoView(companyId) {
  const node = elements.nodeLayer.querySelector(`[data-company-id="${companyId}"]`);
  if (node) {
    node.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

async function postJson(url, payload, allowFailure = false) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok && !allowFailure) {
    alert(data.error || "操作失敗");
    throw new Error(data.error || "Request failed");
  }
  if (!response.ok && allowFailure && data.preview?.errors?.length) {
    renderImportPreview();
  }
  return data;
}

function debounce(fn, wait) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

boot().catch((error) => {
  console.error(error);
  alert("載入失敗，請查看終端機訊息。");
});
