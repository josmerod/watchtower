/* Command palette (spec 02 F1): Ctrl/Cmd+K opens a searchable launcher.
 *
 * The shortcuts list is embedded in the layout as JSON inside a hidden div
 * with id "palette-data" ({"name","url","category"} records). Navigation is
 * purely clientside: filter, arrows, Enter opens in a new tab.
 *
 * T-057 — global content search: typing also debounces (~250ms) a query to
 * the keyless API endpoint GET /api/v1/search, rendering hits under a
 * "Resultados" group (click/Enter navigates in the SAME tab). The API runs on
 * a different port than the dashboard, so the base URL is probed: same-origin
 * first (works when a reverse proxy routes /api), then the LAN port-swap
 * (dashboard :7780 -> API :45714). Every failure path is silent: if the API
 * is unreachable, blocked by CORS or returns garbage, the palette behaves
 * exactly as the shortcuts-only version.
 */
(function () {
  var overlay = null;
  var input = null;
  var listEl = null;
  var items = [];
  var filtered = [];
  var selected = 0;

  /* --- T-057: remote content-search state -------------------------------- */
  var remoteResults = [];
  var selectable = []; // rendered rows in nav order: shortcuts first, then remote hits
  var rowEls = []; // DOM element per selectable row (group headers excluded)
  var remoteSeq = 0; // guards against stale fetch responses
  var debounceTimer = null;
  var apiBase = null; // cached working API base URL
  var apiDeadUntil = 0; // epoch ms; skip probing after total failure
  var API_PORT = "45714";
  var API_SEARCH_PATH = "/api/v1/search?q=";
  var REMOTE_LIMIT = 10;
  var DEBOUNCE_MS = 250;
  var API_BACKOFF_MS = 30000;

  function apiCandidates() {
    var loc = window.location;
    var same = loc.origin;
    var swapped = loc.protocol + "//" + loc.hostname + ":" + API_PORT;
    return same === swapped ? [same] : [same, swapped];
  }

  function fetchRemote(term) {
    if (Date.now() < apiDeadUntil) return;
    var seq = ++remoteSeq;
    var candidates = apiBase ? [apiBase] : apiCandidates();
    tryNext(0);

    function tryNext(i) {
      if (i >= candidates.length) {
        apiBase = null;
        apiDeadUntil = Date.now() + API_BACKOFF_MS;
        if (remoteResults.length) {
          remoteResults = [];
          renderList();
        }
        return;
      }
      fetch(candidates[i] + API_SEARCH_PATH + encodeURIComponent(term) + "&limit=" + REMOTE_LIMIT)
        .then(function (res) {
          if (!res.ok) throw new Error("http " + res.status);
          var ct = res.headers.get("content-type") || "";
          if (ct.indexOf("json") === -1) throw new Error("not json");
          return res.json();
        })
        .then(function (body) {
          if (seq !== remoteSeq) return;
          apiBase = candidates[i];
          remoteResults = (body && body.items) || [];
          renderList();
        })
        .catch(function () {
          if (seq !== remoteSeq) return;
          tryNext(i + 1);
        });
    }
  }

  function scheduleRemote() {
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () {
      var term = (input.value || "").trim();
      if (term.length < 2) {
        remoteSeq++;
        remoteResults = [];
        renderList();
        return;
      }
      fetchRemote(term);
    }, DEBOUNCE_MS);
  }

  function openEntry(entry) {
    if (entry.remote) {
      window.location.assign(entry.url); // T-057: content hits navigate in the same tab
    } else {
      window.open(entry.url, "_blank");
    }
    hide();
  }

  function loadItems() {
    var holder = document.getElementById("palette-data");
    if (!holder) return;
    try {
      items = JSON.parse(holder.textContent || "[]");
    } catch (e) {
      items = [];
    }
  }

  function ensureOverlay() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.id = "wt-palette-overlay";
    overlay.style.cssText = "position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:9999;display:none;align-items:flex-start;justify-content:center;padding-top:12vh;";
    var box = document.createElement("div");
    box.style.cssText = "background:#1e1e2e;border:1px solid #45475a;border-radius:12px;width:min(640px,90vw);box-shadow:0 18px 50px rgba(0,0,0,0.6);overflow:hidden;";
    input = document.createElement("input");
    input.id = "wt-palette-input";
    input.placeholder = "Buscar atajo o contenido… (flechas para navegar, Enter para abrir, Esc para cerrar)";
    input.style.cssText = "width:100%;padding:14px 18px;font-size:15px;background:#11111b;color:#cdd6f4;border:none;border-bottom:1px solid #45475a;outline:none;box-sizing:border-box;";
    listEl = document.createElement("div");
    listEl.id = "wt-palette-list";
    listEl.style.cssText = "max-height:50vh;overflow-y:auto;";
    box.appendChild(input);
    box.appendChild(listEl);
    overlay.appendChild(box);
    overlay.addEventListener("mousedown", function (e) {
      if (e.target === overlay) hide();
    });
    input.addEventListener("input", function () {
      renderList();
      scheduleRemote();
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        selected = Math.min(selected + 1, selectable.length - 1);
        highlight();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selected = Math.max(selected - 1, 0);
        highlight();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (selectable[selected]) {
          openEntry(selectable[selected]);
        }
      } else if (e.key === "Escape") {
        hide();
      }
    });
    document.body.appendChild(overlay);
  }

  function highlight() {
    rowEls.forEach(function (li, i) {
      li.style.background = i === selected ? "#45475a" : "transparent";
    });
    if (rowEls[selected]) {
      rowEls[selected].scrollIntoView({ block: "nearest" });
    }
  }

  function appendGroupHeader(label) {
    var header = document.createElement("div");
    header.textContent = label;
    header.style.cssText = "padding:8px 18px 4px;color:#89b4fa;font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;";
    listEl.appendChild(header);
  }

  function appendRow(entry) {
    var li = document.createElement("div");
    li.style.cssText = "display:flex;justify-content:space-between;gap:12px;padding:10px 18px;cursor:pointer;color:#cdd6f4;font-size:14px;";
    var name = document.createElement("span");
    name.textContent = entry.name;
    var cat = document.createElement("span");
    cat.textContent = entry.category;
    cat.style.cssText = "color:#7f849c;font-size:12px;white-space:nowrap;";
    li.appendChild(name);
    li.appendChild(cat);
    li.addEventListener("click", function () {
      openEntry(entry);
    });
    listEl.appendChild(li);
    rowEls.push(li);
    selectable.push(entry);
  }

  function renderList() {
    var term = (input.value || "").trim().toLowerCase();
    filtered = items.filter(function (s) {
      return !term || (s.name || "").toLowerCase().indexOf(term) !== -1 || (s.category || "").toLowerCase().indexOf(term) !== -1;
    });
    selected = 0;
    listEl.innerHTML = "";
    rowEls = [];
    selectable = [];
    var shortcutRows = filtered.slice(0, 30);
    var remoteRows = remoteResults.slice(0, REMOTE_LIMIT);
    var grouped = remoteRows.length > 0;
    if (grouped && shortcutRows.length) appendGroupHeader("Atajos");
    shortcutRows.forEach(function (s) {
      appendRow({ name: s.name || s.url, url: s.url, category: s.category || "", remote: false });
    });
    if (grouped) {
      appendGroupHeader("Resultados");
      remoteRows.forEach(function (r) {
        appendRow({ name: r.title, url: r.url, category: (r.kind ? r.kind + " · " : "") + (r.source || ""), remote: true });
      });
    }
    if (!selectable.length) {
      var empty = document.createElement("div");
      empty.textContent = "Sin atajos que coincidan.";
      empty.style.cssText = "padding:12px 18px;color:#7f849c;font-size:13px;";
      listEl.appendChild(empty);
    }
    highlight();
  }

  function show() {
    ensureOverlay();
    loadItems();
    overlay.style.display = "flex";
    input.value = "";
    remoteSeq++;
    remoteResults = [];
    renderList();
    setTimeout(function () {
      input.focus();
    }, 30);
  }

  function hide() {
    if (overlay) overlay.style.display = "none";
  }

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      if (overlay && overlay.style.display === "flex") {
        hide();
      } else {
        show();
      }
    }
  });
})();
