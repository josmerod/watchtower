/* Command palette (spec 02 F1): Ctrl/Cmd+K opens a searchable launcher.
 *
 * The shortcuts list is embedded in the layout as JSON inside a hidden div
 * with id "palette-data" ({"name","url","category"} records). Navigation is
 * purely clientside: filter, arrows, Enter opens in a new tab.
 */
(function () {
  var overlay = null;
  var input = null;
  var listEl = null;
  var items = [];
  var filtered = [];
  var selected = 0;

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
    input.placeholder = "Buscar atajo… (flechas para navegar, Enter para abrir, Esc para cerrar)";
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
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        selected = Math.min(selected + 1, filtered.length - 1);
        highlight();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selected = Math.max(selected - 1, 0);
        highlight();
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (filtered[selected]) {
          window.open(filtered[selected].url, "_blank");
          hide();
        }
      } else if (e.key === "Escape") {
        hide();
      }
    });
    document.body.appendChild(overlay);
  }

  function highlight() {
    Array.from(listEl.children).forEach(function (li, i) {
      li.style.background = i === selected ? "#45475a" : "transparent";
    });
    if (listEl.children[selected]) {
      listEl.children[selected].scrollIntoView({ block: "nearest" });
    }
  }

  function renderList() {
    var term = (input.value || "").trim().toLowerCase();
    filtered = items.filter(function (s) {
      return !term || (s.name || "").toLowerCase().indexOf(term) !== -1 || (s.category || "").toLowerCase().indexOf(term) !== -1;
    });
    selected = 0;
    listEl.innerHTML = "";
    filtered.slice(0, 30).forEach(function (s) {
      var li = document.createElement("div");
      li.style.cssText = "display:flex;justify-content:space-between;gap:12px;padding:10px 18px;cursor:pointer;color:#cdd6f4;font-size:14px;";
      var name = document.createElement("span");
      name.textContent = s.name || s.url;
      var cat = document.createElement("span");
      cat.textContent = s.category || "";
      cat.style.cssText = "color:#7f849c;font-size:12px;white-space:nowrap;";
      li.appendChild(name);
      li.appendChild(cat);
      li.addEventListener("click", function () {
        window.open(s.url, "_blank");
        hide();
      });
      listEl.appendChild(li);
    });
    if (!filtered.length) {
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
