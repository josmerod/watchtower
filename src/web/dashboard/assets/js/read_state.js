/* Read/unread state for news rows (spec 01 F2).
 *
 * Rows carry data-item-hash attributes; this script keeps a Set of read
 * hashes in localStorage ("wt_read_hashes"), dims read rows and can hide
 * them entirely when the toggle is active. Works across Dash re-renders
 * via a debounced MutationObserver on the tab content.
 */
(function () {
  var STORE_KEY = "wt_read_hashes";
  var TOGGLE_KEY = "wt_hide_read";
  var scheduled = false;

  function readSet() {
    try {
      return new Set(JSON.parse(localStorage.getItem(STORE_KEY) || "[]"));
    } catch (e) {
      return new Set();
    }
  }

  function writeSet(set) {
    localStorage.setItem(STORE_KEY, JSON.stringify(Array.from(set).slice(-5000)));
  }

  function apply() {
    var hide = localStorage.getItem(TOGGLE_KEY) === "1";
    var set = readSet();
    var rows = document.querySelectorAll("tr[data-item-hash]");
    rows.forEach(function (row) {
      var isRead = set.has(row.getAttribute("data-item-hash"));
      row.classList.toggle("wt-item-read", isRead);
      row.style.display = hide && isRead ? "none" : "";
    });
    var badge = document.getElementById("news-read-count");
    if (badge) {
      var text = set.size ? set.size + " leidos" : "";
      if (badge.textContent !== text) {
        badge.textContent = text;
      }
    }
  }

  function scheduleApply() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(function () {
      scheduled = false;
      bindControls();
      apply();
    }, 150);
  }

  function markAllVisible() {
    var set = readSet();
    document.querySelectorAll("tr[data-item-hash]").forEach(function (row) {
      set.add(row.getAttribute("data-item-hash"));
    });
    writeSet(set);
    localStorage.setItem("wt_last_mark_all", new Date().toISOString());
    apply();
  }

  function toggleHide() {
    var current = localStorage.getItem(TOGGLE_KEY) === "1";
    localStorage.setItem(TOGGLE_KEY, current ? "0" : "1");
    var btn = document.getElementById("news-toggle-hide-read");
    if (btn) btn.textContent = current ? "Ocultar leidos: OFF" : "Ocultar leidos: ON";
    apply();
  }

  function bindControls() {
    var mark = document.getElementById("news-mark-all-read");
    if (mark && !mark.dataset.bound) {
      mark.dataset.bound = "1";
      mark.addEventListener("click", markAllVisible);
    }
    var toggle = document.getElementById("news-toggle-hide-read");
    if (toggle && !toggle.dataset.bound) {
      toggle.dataset.bound = "1";
      toggle.addEventListener("click", toggleHide);
      if (localStorage.getItem(TOGGLE_KEY) === "1") {
        toggle.textContent = "Ocultar leidos: ON";
      }
    }
  }

  function init() {
    bindControls();
    apply();
    var target = document.getElementById("tab-content") || document.body;
    if (!target.dataset.wtReadObserved) {
      target.dataset.wtReadObserved = "1";
      new MutationObserver(scheduleApply).observe(target, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
