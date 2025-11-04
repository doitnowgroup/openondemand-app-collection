(() => {
  const grid = document.getElementById("dash-grid");
  const errBox = document.getElementById("error-box");
  const filterInput = document.getElementById("filter-input");
  const refreshSelect = document.getElementById("refresh-select");
  const fromInput = document.getElementById("from-input");
  const toInput = document.getElementById("to-input");
  const userBadge = document.getElementById("user-badge");
  const modeBadge = document.getElementById("mode-badge");

  // Subpath-aware endpoints (from data-* in index.html)
  const meta = document.getElementById("app-meta");
  const ROOT = meta?.dataset.root || "";
  const API_DASHBOARDS = meta?.dataset.apiDashboards || (ROOT + "/api/dashboards"); //
  const GRAFANA_BASE = (meta?.dataset.grafanaBase || "").replace(/\/+$/, "");

  // Defaults
  const defaultsEl = document.getElementById("defaults");
  const defaults = {
    refresh: defaultsEl?.dataset.refresh || "10s",
    from: defaultsEl?.dataset.from || "now-1h",
    to: defaultsEl?.dataset.to || "now",
  };

  if (refreshSelect) refreshSelect.value = defaults.refresh;
  if (fromInput) fromInput.value = defaults.from;
  if (toInput) toInput.value = defaults.to;

  let mode = "images"; // "dashboards" | "images"
  const modeRadios = document.querySelectorAll('input[name="mode"]');

  // Local caches
  let dashboards = [];
  let imagesDashboards = [];

  // Helpers
  const gfUrl = (pathAndQuery) => `${GRAFANA_BASE}${pathAndQuery}`;

  const mapSearchItem = (it) => ({
    uid: it.uid,
    title: it.title,
    folderUid: it.folderUid,
    tags: it.tags || [],
    url: it.url, // relative to grafana
  });

  function showSkeleton(count = 6) {
    if (!grid) return;
    grid.innerHTML = "";
    for (let i = 0; i < count; i++) {
      const col = document.createElement("div");
      col.className = "col-12 col-md-6 col-lg-4";
      col.innerHTML = `<div class="skeleton w-100"></div>`;
      grid.appendChild(col);
    }
  }

  function setError(msg) {
    if (!errBox) return;
    errBox.textContent = msg;
    errBox.classList.remove("d-none");
  }

  function clearError() {
    if (!errBox) return;
    errBox.textContent = "";
    errBox.classList.add("d-none");
  }

  function updateModeBadge() {
    if (!modeBadge) return;
    modeBadge.textContent = mode === "dashboards" ? "Dashboards mode" : "Images mode";
    modeBadge.classList.remove("d-none");
  }

  function makeEmbedHrefForDashboard(uid) {
    const refresh = encodeURIComponent(refreshSelect?.value || "10s");
    const from = encodeURIComponent(fromInput?.value || "now-1h");
    const to = encodeURIComponent(toInput?.value || "now");
    return `${ROOT}/embed/${encodeURIComponent(uid)}?refresh=${refresh}&from=${from}&to=${to}`;
  }

  // ----- Fetch panel ids from Grafana (front-end, user session) -----
  async function fetchPanelIds(uid) {
    const res = await fetch(`${gfUrl("/api/dashboards/uid/")}${encodeURIComponent(uid)}`, {
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error(`Grafana /api/dashboards/uid/${uid} -> ${res.status}`);
    const data = await res.json();
    const dash = data?.dashboard || {};
    const ids = [];
    (function collect(panels) {
      if (!Array.isArray(panels)) return;
      for (const p of panels) {
        if (p?.type === "row" && Array.isArray(p.panels)) collect(p.panels);
        else if (Number.isInteger(p?.id)) ids.push(p.id);
      }
    })(dash.panels || []);
    return ids;
  }

  // ----- Rendering -----
  function renderDashboards(items) {
    grid.innerHTML = "";
    if (!items.length) {
      const div = document.createElement("div");
      div.className = "col-12";
      div.innerHTML = `<div class="alert alert-info">No dashboards to display.</div>`;
      grid.appendChild(div);
      return;
    }

    const frag = document.createDocumentFragment();
    for (const d of items) {
      const col = document.createElement("div");
      col.className = "col-12 col-md-6 col-lg-4";
      const tags = (d.tags || [])
        .map((t) => `<span class="badge text-bg-light border tag-badge">${t}</span>`)
        .join(" ");
      const embedHref = `${makeEmbedHrefForDashboard(d.uid)}&title=${encodeURIComponent(d.title || d.uid)}`;
      const grafanaHref = d.url && GRAFANA_BASE ? `${GRAFANA_BASE}${d.url}` : "";

      col.innerHTML = `
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <h2 class="h6 card-title mb-2 text-truncate" title="${d.title || d.uid}">${d.title || d.uid}</h2>
            <div class="mb-3 small text-muted">
              <div class="text-truncate" title="UID: ${d.uid}">UID: <code>${d.uid}</code></div>
              ${d.folderUid ? `<div class="text-truncate" title="Folder UID: ${d.folderUid}">Folder: <code>${d.folderUid}</code></div>` : ""}
              ${tags ? `<div class="mt-2">${tags}</div>` : ""}
            </div>
            <div class="mt-auto d-flex gap-2">
              <a class="btn btn-primary btn-sm" href="${embedHref}">Open</a>
              ${grafanaHref ? `<a class="btn btn-outline-secondary btn-sm" href="${grafanaHref}" target="_blank" rel="noreferrer noopener">Open in Grafana</a>` : ""}
              <button class="btn btn-success btn-sm btn-open-images" data-uid="${d.uid}" data-title="${(d.title || d.uid).replace(/"/g, '&quot;')}">Open (Images)</button>
	      <!-- button class="btn btn-success btn-sm btn-open-images" data-uid="${d.uid}">Open (Images)</button -->
            </div>
          </div>
        </div>
      `;
      frag.appendChild(col);
    }
    grid.appendChild(frag);

    // Wire "Open (Images)" to fetch panelIds then navigate
    grid.querySelectorAll(".btn-open-images").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const uid = btn.getAttribute("data-uid");
        try {
          const ids = await fetchPanelIds(uid);
          const q = new URLSearchParams();
          if (ids.length) q.set("panelIds", ids.join(","));
		//q.set("title", d.title || d.uid);
	  const name = btn.getAttribute("data-title") || uid;
          q.set("title", name);
          location.href = `${ROOT}/embed/img/${encodeURIComponent(uid)}?${q.toString()}`;
        } catch (err) {
          console.error(err);
          // fallback: full dashboard image
          location.href = `${ROOT}/embed/img/${encodeURIComponent(uid)}`;
        }
      });
    });
  }

  function renderImages(items) {
    grid.innerHTML = "";
    if (!items.length) {
      const div = document.createElement("div");
      div.className = "col-12";
      div.innerHTML = `<div class="alert alert-info">No dashboards available for images mode.</div>`;
      grid.appendChild(div);
      return;
    }

    const frag = document.createDocumentFragment();
    for (const d of items) {
      const col = document.createElement("div");
      col.className = "col-12 col-md-6 col-lg-4";

      const tags = (d.tags || [])
        .map((t) => `<span class="badge text-bg-light border tag-badge">${t}</span>`)
        .join(" ");
      const grafanaHref = d.url && GRAFANA_BASE ? `${GRAFANA_BASE}${d.url}` : "";

      col.innerHTML = `
        <div class="card h-100">
          <div class="card-body d-flex flex-column">
            <h2 class="h6 card-title mb-2 text-truncate" title="${d.title || d.uid}">${d.title || d.uid}</h2>
            <div class="mb-3 small text-muted">
              <div class="text-truncate" title="UID: ${d.uid}">UID: <code>${d.uid}</code></div>
              ${d.folderUid ? `<div class="text-truncate" title="Folder UID: ${d.folderUid}">Folder: <code>${d.folderUid}</code></div>` : ""}
              ${tags ? `<div class="mt-2">${tags}</div>` : ""}
            </div>
            <div class="mt-auto d-flex gap-2">
              <button class="btn btn-success btn-sm btn-open-images" data-uid="${d.uid}">Open (Images)</button>
              ${grafanaHref ? `<a class="btn btn-outline-secondary btn-sm" href="${grafanaHref}" target="_blank" rel="noreferrer noopener">Open in Grafana</a>` : ""}
            </div>
          </div>
        </div>
      `;
      frag.appendChild(col);
    }
    grid.appendChild(frag);

    // Wire "Open (Images)"
    grid.querySelectorAll(".btn-open-images").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const uid = btn.getAttribute("data-uid");
        try {
          const ids = await fetchPanelIds(uid);
          const q = new URLSearchParams();
          if (ids.length) q.set("panelIds", ids.join(","));
          //q.set("title", d.title || d.uid);
          const name = btn.getAttribute("data-title") || uid;
          q.set("title", name);

          location.href = `${ROOT}/embed/img/${encodeURIComponent(uid)}?${q.toString()}`;
        } catch (err) {
          console.error(err);
          location.href = `${ROOT}/embed/img/${encodeURIComponent(uid)}`;
        }
      });
    });
  }

  // ----- Loaders -----
  async function loadDashboards() {
    try {
      clearError();
      showSkeleton();

      const res = await fetch(gfUrl("/api/search?type=dash-db"), { credentials: "same-origin" });
      if (!res.ok) throw new Error(`Grafana API ${res.status}`);
      const items = await res.json();

      dashboards = Array.isArray(items) ? items.map(mapSearchItem) : [];

      if (userBadge) {
        try {
          const who = await fetch(ROOT + "/debug/env", { credentials: "same-origin" }).then((r) => r.json());
          const name = who?.REMOTE_USER || who?.hdr_X-Forwarded-User || "unknown";
          userBadge.textContent = `User: ${name}`;
          userBadge.classList.remove("d-none");
        } catch {}
      }

      applyFilter();
    } catch (e) {
      console.error(e);
      setError("Failed to fetch dashboards (Grafana API).");
      grid.innerHTML = "";
    }
  }

  async function loadImages() {
    try {
      clearError();
      showSkeleton();

      const res = await fetch(gfUrl("/api/search?type=dash-db"), { credentials: "same-origin" });
      if (!res.ok) throw new Error(`Grafana API ${res.status}`);
      const items = await res.json();

      imagesDashboards = Array.isArray(items) ? items.map(mapSearchItem) : [];

      if (userBadge) {
        try {
          const who = await fetch(ROOT + "/debug/env", { credentials: "same-origin" }).then((r) => r.json());
          const name = who?.REMOTE_USER || who?.hdr_X-Forwarded-User || "unknown";
          userBadge.textContent = `User: ${name}`;
          userBadge.classList.remove("d-none");
        } catch {}
      }

      applyFilter();
    } catch (e) {
      console.error(e);
      setError("Failed to fetch dashboards for images mode.");
      grid.innerHTML = "";
    }
  }

  // ----- Filtering -----
  function applyFilter() {
    try {
      const q = (filterInput?.value || "").trim().toLowerCase();
      const words = q.split(/\s+/).filter(Boolean);

      const filterList = (list) => {
        if (!words.length) return list;
        return list.filter((d) => {
          const hay = [
            d.title || "",
            d.uid || "",
            ...(d.tags || []),
            d.folderUid || "",
          ]
            .join(" ")
            .toLowerCase();
          return words.every((w) => hay.includes(w));
        });
      };

      if (mode === "dashboards") {
        return renderDashboards(filterList(dashboards));
      } else {
        return renderImages(filterList(imagesDashboards));
      }
    } catch (e) {
      console.error("[applyFilter] error:", e);
      setError("Client-side rendering error.");
    }
  }

  // ----- Mode wiring -----
  function onModeChange(nextMode) {
    if (mode === nextMode) return;
    mode = nextMode;
    updateModeBadge();

    if (mode === "dashboards") {
      if (!dashboards.length) loadDashboards();
      else applyFilter();
    } else {
      if (!imagesDashboards.length) loadImages();
      else applyFilter();
    }

    try {
      localStorage.setItem("grafana-viewer-mode", mode);
    } catch {}
  }

  // Events
  filterInput?.addEventListener("input", applyFilter);
  refreshSelect?.addEventListener("change", applyFilter);
  fromInput?.addEventListener("change", applyFilter);
  toInput?.addEventListener("change", applyFilter);
  modeRadios.forEach((r) => {
    r.addEventListener("change", (e) => {
      if (e.target?.checked) onModeChange(e.target.value);
    });
  });

  // Init
  function initMode() {
    try {
      const saved = localStorage.getItem("grafana-viewer-mode");
      if (saved === "dashboards" || saved === "images") mode = saved;
    } catch {}
    const radio = document.getElementById(mode === "dashboards" ? "mode-dashboards" : "mode-images");
    if (radio) radio.checked = true;
    updateModeBadge();
  }

  async function bootstrap() {
    initMode();
    if (mode === "dashboards") await loadDashboards();
    else await loadImages();
  }

  if (grid) bootstrap();
})();

