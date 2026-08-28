/* Seen / watch-later state for video cards (spec 04 F1) + NUEVO badges
 * (spec 04 F5).
 *
 * Cards carry data-video-hash attributes; this script keeps two Sets in
 * localStorage ("wt_video_seen", "wt_video_later"), dims seen cards,
 * highlights watch-later ones, and fills the #videos-state-toolbar with a
 * "▶ Ver más tarde" filter and a hide-seen toggle. Purely client-side;
 * re-binds after Dash re-renders via a debounced MutationObserver.
 *
 * NUEVO (F5): cards also carry data-published-at (ISO 8601). On load the
 * script compares it with localStorage "wt_videos_last_visit": cards newer
 * than the previous visit get a small "NUEVO" pill and the toolbar counts
 * them. The stored timestamp is then bumped (debounced) so the next visit
 * only badges what arrived since. First visit ever: just record, no badges.
 */
(function () {
  var SEEN_KEY = "wt_video_seen";
  var LATER_KEY = "wt_video_later";
  var FILTER_KEY = "wt_video_filter_later";
  var HIDE_SEEN_KEY = "wt_video_hide_seen";
  var LAST_VISIT_KEY = "wt_videos_last_visit";
  var scheduled = false;

  /* ---- NUEVO badges (spec 04 F5) ---- */

  // Read once per page load: badges for this whole session (pagination,
  // filters, tab switches) compare against the PREVIOUS visit's stamp.
  var sessionBaseline = null;
  var visitStampScheduled = false;

  function stampLastVisit() {
    var raw = parseInt(localStorage.getItem(LAST_VISIT_KEY) || "", 10);
    if (isNaN(raw)) {
      // First visit ever: set the baseline and show no badges.
      sessionBaseline = Date.now();
      localStorage.setItem(LAST_VISIT_KEY, String(sessionBaseline));
      return;
    }
    sessionBaseline = raw;
    // Debounced bump: keep showing this session's badges while the user
    // browses, but the next page load sees "now" as the last visit.
    if (!visitStampScheduled) {
      visitStampScheduled = true;
      setTimeout(function () {
        localStorage.setItem(LAST_VISIT_KEY, String(Date.now()));
      }, 2500);
    }
  }

  function isNewCard(card) {
    var attr = card.getAttribute("data-published-at");
    if (!attr) return false;
    var published = Date.parse(attr);
    return !isNaN(published) && published > sessionBaseline;
  }

  function applyNewBadges() {
    var fresh = 0;
    document.querySelectorAll("[data-video-hash]").forEach(function (card) {
      // Compute once per card so the badge survives container re-renders of
      // the same page (last_visit has been bumped by then).
      if (card.dataset.wtNew === undefined) {
        card.dataset.wtNew = sessionBaseline !== null && isNewCard(card) ? "1" : "0";
      }
      if (card.dataset.wtNew !== "1") return;
      fresh++;
      if (card.querySelector(".wt-video-new-badge")) return;
      card.style.position = card.style.position || "relative";
      var pill = document.createElement("span");
      pill.className = "wt-video-new-badge";
      pill.textContent = "NUEVO";
      pill.style.cssText =
        "position:absolute;top:8px;left:8px;z-index:6;background:#A37FFF;color:#fff;" +
        "font-size:0.62rem;font-weight:700;letter-spacing:.03em;padding:1px 8px;" +
        "border-radius:999px;text-transform:uppercase;box-shadow:0 1px 4px rgba(0,0,0,.35);";
      card.insertBefore(pill, card.firstChild);
    });
    var counts = document.getElementById("wt-video-counts");
    if (counts) {
      counts.textContent = fresh > 0 ? fresh + " NUEVO" : "";
      counts.style.color = fresh > 0 ? "#A37FFF" : "";
      counts.style.fontWeight = fresh > 0 ? "600" : "";
    }
  }

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
    applyNewBadges();
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
  stampLastVisit();
  refresh();
})();
