/* Seen / watch-later state for video cards (spec 04 F1).
 *
 * Cards carry data-video-hash attributes; this script keeps two Sets in
 * localStorage ("wt_video_seen", "wt_video_later"), dims seen cards,
 * highlights watch-later ones, and fills the #videos-state-toolbar with a
 * "▶ Ver más tarde" filter and a hide-seen toggle. Purely client-side;
 * re-binds after Dash re-renders via a debounced MutationObserver.
 */
(function () {
  var SEEN_KEY = "wt_video_seen";
  var LATER_KEY = "wt_video_later";
  var FILTER_KEY = "wt_video_filter_later";
  var HIDE_SEEN_KEY = "wt_video_hide_seen";
  var scheduled = false;

  function readSet(key) {
    try {
      return new Set(JSON.parse(localStorage.getItem(key) || "[]"));
    } catch (e) {
      return new Set();
    }
  }

  function writeSet(key, set) {
    localStorage.setItem(key, JSON.stringify(Array.from(set).slice(-5000)));
  }

  function updateToolbar() {
    var later = readSet(LATER_KEY);
    var seen = readSet(SEEN_KEY);
    var filterOn = localStorage.getItem(FILTER_KEY) === "1";
    var hideOn = localStorage.getItem(HIDE_SEEN_KEY) === "1";
    var f = document.getElementById("wt-video-filter-btn");
    var h = document.getElementById("wt-video-hide-seen-btn");
    if (f) {
      f.classList.toggle("btn-secondary", filterOn);
      f.classList.toggle("btn-outline-secondary", !filterOn);
      f.textContent = (filterOn ? "▶ Solo ver más tarde (" : "▶ Ver más tarde (") + later.size + ")";
    }
    if (h) {
      h.classList.toggle("btn-secondary", hideOn);
      h.classList.toggle("btn-outline-secondary", !hideOn);
      h.textContent = hideOn ? "👁 Mostrando vistos (" + seen.size + ")" : "👁 Ocultar vistos (" + seen.size + ")";
    }
  }

  function buildToolbar() {
    var slot = document.getElementById("videos-state-toolbar");
    if (!slot) return;
    if (!slot.childElementCount) {
      slot.innerHTML =
        '<button type="button" id="wt-video-filter-btn" class="btn btn-sm btn-outline-secondary me-2 mb-2">' +
        "▶ Ver más tarde</button>" +
        '<button type="button" id="wt-video-hide-seen-btn" class="btn btn-sm btn-outline-secondary mb-2">' +
        "👁 Ocultar vistos</button>" +
        '<span id="wt-video-counts" class="text-muted small ms-2"></span>';
      document.getElementById("wt-video-filter-btn").addEventListener("click", function () {
        localStorage.setItem(FILTER_KEY, localStorage.getItem(FILTER_KEY) === "1" ? "0" : "1");
        updateToolbar();
        apply();
      });
      document.getElementById("wt-video-hide-seen-btn").addEventListener("click", function () {
        localStorage.setItem(HIDE_SEEN_KEY, localStorage.getItem(HIDE_SEEN_KEY) === "1" ? "0" : "1");
        updateToolbar();
        apply();
      });
    }
    updateToolbar();
  }

  function apply() {
    var seen = readSet(SEEN_KEY);
    var later = readSet(LATER_KEY);
    var filterLater = localStorage.getItem(FILTER_KEY) === "1";
    var hideSeen = localStorage.getItem(HIDE_SEEN_KEY) === "1";
    document.querySelectorAll("[data-video-hash]").forEach(function (card) {
      var hash = card.getAttribute("data-video-hash");
      var isSeen = seen.has(hash);
      var isLater = later.has(hash);
      card.classList.toggle("wt-item-read", isSeen); // reuses the news dim style
      card.classList.toggle("border-warning", isLater);
      var show = true;
      if (filterLater && !isLater) show = false;
      if (hideSeen && isSeen) show = false;
      card.style.display = show ? "" : "none";
      card.querySelectorAll(".wt-video-seen-btn").forEach(function (b) {
        b.classList.toggle("btn-success", isSeen);
        b.classList.toggle("btn-outline-secondary", !isSeen);
      });
      card.querySelectorAll(".wt-video-later-btn").forEach(function (b) {
        b.classList.toggle("btn-warning", isLater);
        b.classList.toggle("btn-outline-secondary", !isLater);
      });
    });
  }

  function bindCards() {
    document.querySelectorAll("[data-video-hash]").forEach(function (card) {
      var hash = card.getAttribute("data-video-hash");
      var seenBtn = card.querySelector(".wt-video-seen-btn");
      var laterBtn = card.querySelector(".wt-video-later-btn");
      if (seenBtn && !seenBtn.dataset.bound) {
        seenBtn.dataset.bound = "1";
        seenBtn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          var set = readSet(SEEN_KEY);
          if (set.has(hash)) set.delete(hash);
          else set.add(hash);
          writeSet(SEEN_KEY, set);
          buildToolbar();
          apply();
        });
      }
      if (laterBtn && !laterBtn.dataset.bound) {
        laterBtn.dataset.bound = "1";
        laterBtn.addEventListener("click", function (e) {
          e.preventDefault();
          e.stopPropagation();
          var set = readSet(LATER_KEY);
          if (set.has(hash)) set.delete(hash);
          else set.add(hash);
          writeSet(LATER_KEY, set);
          buildToolbar();
          apply();
        });
      }
    });
  }

  function refresh() {
    buildToolbar();
    bindCards();
    apply();
  }

  function scheduleRefresh() {
    if (scheduled) return;
    scheduled = true;
    setTimeout(function () {
      scheduled = false;
      refresh();
    }, 150);
  }

  var observer = new MutationObserver(scheduleRefresh);
  observer.observe(document.body, { childList: true, subtree: true });
  document.addEventListener("DOMContentLoaded", refresh);
  refresh();
})();
