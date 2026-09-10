/* NUEVO badges for the Knowledge Garden tab (T-085).
 *
 * Mirrors video_state.js (spec 04 F5): rows and card wrappers carry
 * data-kg-date (ISO 8601, emitted by knowledge_garden_tab.py). On load the
 * script compares it with localStorage "wt_kg_last_visit": items newer than
 * the PREVIOUS visit get a small violet "NUEVO" pill and the header chip
 * #kg-new-counter counts them across every subtab. The stored stamp is then
 * bumped (debounced) so the next visit only badges what arrived since.
 * First visit ever: just record the baseline, no badges.
 *
 * Purely client-side; re-binds after Dash re-renders (subtab switches,
 * search, pagination, list/cards toggle) via a debounced MutationObserver —
 * see read_state.js for the same pattern.
 */
(function () {
  var LAST_VISIT_KEY = "wt_kg_last_visit";
  var ROW_SEL = "[data-kg-date]";
  var BADGE_CLASS = "wt-kg-new-badge";
  var COUNTER_ID = "kg-new-counter";
  var BADGE_CSS =
    "display:inline-block;background:#A37FFF;color:#fff;font-size:0.62rem;" +
    "font-weight:700;letter-spacing:.03em;padding:1px 8px;border-radius:999px;" +
    "text-transform:uppercase;box-shadow:0 1px 4px rgba(0,0,0,.35);" +
    "pointer-events:none;";

  var scheduled = false;

  // Read once per page load: badges for this whole session (subtab switches,
  // pagination, filters) compare against the PREVIOUS visit's stamp.
  var sessionBaseline = null;
  var visitStampScheduled = false;

  function stampLastVisit() {
    var raw = localStorage.getItem(LAST_VISIT_KEY);
    var parsed = raw ? Date.parse(raw) : NaN;
    if (isNaN(parsed)) {
      // First visit ever (or corrupt value): set the baseline, no badges.
      sessionBaseline = Date.now();
      localStorage.setItem(LAST_VISIT_KEY, new Date(sessionBaseline).toISOString());
      return;
    }
    sessionBaseline = parsed;
    // Debounced bump: keep showing this session's badges while the user
    // browses, but the next page load sees "now" as the last visit.
    if (!visitStampScheduled) {
      visitStampScheduled = true;
      setTimeout(function () {
        localStorage.setItem(LAST_VISIT_KEY, new Date().toISOString());
      }, 2500);
    }
  }

  function isNewRow(row) {
    var attr = row.getAttribute("data-kg-date");
    if (!attr) return false;
    var published = Date.parse(attr);
    return !isNaN(published) && published > sessionBaseline;
  }

  function makePill() {
    var pill = document.createElement("span");
    pill.className = BADGE_CLASS;
    pill.textContent = "NUEVO";
    pill.style.cssText = BADGE_CSS;
    return pill;
  }

  function ensureBadge(row) {
    if (row.querySelector("." + BADGE_CLASS)) return;
    var pill = makePill();
    if (row.tagName === "TR") {
      // Table rows: inline pill right before the title link so it flows with
      // the text instead of breaking the first (save-button) column.
      var anchor = row.querySelector("td a");
      var host = anchor ? anchor.parentElement : row.querySelector("td");
      if (!host) return;
      pill.style.marginRight = "6px";
      pill.style.verticalAlign = "middle";
      host.insertBefore(pill, anchor || host.firstChild);
    } else {
      // Card wrappers: floating pill pinned to the card corner (videos style).
      row.style.position = row.style.position || "relative";
      pill.style.position = "absolute";
      pill.style.top = "8px";
      pill.style.right = "8px";
      pill.style.zIndex = "6";
      row.insertBefore(pill, row.firstChild);
    }
  }

  function applyNewBadges() {
    var fresh = 0;
    document.querySelectorAll(ROW_SEL).forEach(function (row) {
      // Compute once per element so the badge survives Dash re-renders of the
      // same page (last_visit has been bumped by then, like video_state.js).
      if (row.dataset.wtNew === undefined) {
        row.dataset.wtNew = sessionBaseline !== null && isNewRow(row) ? "1" : "0";
      }
      if (row.dataset.wtNew !== "1") return;
      fresh++;
      ensureBadge(row);
    });
    var counter = document.getElementById(COUNTER_ID);
    if (counter) {
      var text = fresh > 0 ? fresh + " NUEVO" : "";
      // Change-guarded so the observer loop settles (our own DOM writes
      // would re-trigger it otherwise).
      if (counter.textContent !== text) {
        counter.textContent = text;
        counter.title = fresh > 0 ? fresh + " elementos nuevos desde tu última visita" : "";
      }
      counter.style.color = fresh > 0 ? "#A37FFF" : "";
      counter.style.fontWeight = fresh > 0 ? "700" : "";
    }
  }

  function refresh() {
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

  function init() {
    refresh();
    var target = document.getElementById("tab-content") || document.body;
    if (!target.dataset.wtKgObserved) {
      target.dataset.wtKgObserved = "1";
      new MutationObserver(scheduleRefresh).observe(target, { childList: true, subtree: true });
    }
  }

  stampLastVisit();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
