/* "Nuevos desde tu última visita" for the Valencia Events tab (T-143).
 *
 * Same shape as kg_state.js (T-085), with one difference that matters: a visit
 * is an opening of THIS tab, not a page load. The moment the tab was last
 * opened lives in localStorage ("wt_valencia_last_visit"). When the tab is
 * rendered, the script reads that stamp, hands it to the server through the
 * store #valencia-last-visit (window.dash_clientside.set_props) and records
 * this opening as the new stamp. The server answers with the events first
 * detected after the previous visit: the notice in #valencia-new-notice. A
 * dashboard reloaded ten times in between therefore changes nothing.
 *
 * Rows carry data-valencia-detected (the ISO first detection, emitted by
 * valencia_events_new_tab.py); those newer than the previous visit get a small
 * violet "NUEVO" pill before the title.
 *
 * #valencia-mark-seen hands "now" to the server, which answers with an empty
 * notice, and moves the baseline of this page, which removes the pills.
 *
 * Purely client-side glue; re-applied after Dash re-renders (tab switches,
 * filters, pagination) through a debounced MutationObserver on the tab
 * content, see read_state.js for the same pattern.
 */
(function () {
  var LAST_VISIT_KEY = "wt_valencia_last_visit";
  var ANCHOR_ID = "valencia-new-box";
  var STORE_ID = "valencia-last-visit";
  var MARK_SEEN_ID = "valencia-mark-seen";
  var ROW_SEL = "[data-valencia-detected]";
  var BADGE_CLASS = "wt-valencia-new-badge";
  // The fill and the text are !important: the blanket rules of style.css are too, and an inline
  // style they outrank leaves the pill as bare text.
  var BADGE_CSS =
    "display:inline-block;background:#A37FFF !important;color:#fff !important;font-size:0.62rem;" +
    "font-weight:700;letter-spacing:.03em;padding:1px 8px;border-radius:999px;" +
    "text-transform:uppercase;margin-right:6px;vertical-align:middle;" +
    "pointer-events:none;";

  var scheduled = false;
  // The stamp of the previous visit, for the tab rendering now.
  var baseline = null;
  var pushes = 0;

  function readStamp() {
    try {
      var raw = localStorage.getItem(LAST_VISIT_KEY);
      var parsed = raw ? Date.parse(raw) : NaN;
      return isNaN(parsed) ? null : parsed;
    } catch (e) {
      return null;
    }
  }

  function writeStamp(moment) {
    try {
      localStorage.setItem(LAST_VISIT_KEY, new Date(moment).toISOString());
    } catch (e) {
      /* No storage (private mode): this visit cannot be remembered. */
    }
  }

  function push(moment) {
    var setProps = window.dash_clientside && window.dash_clientside.set_props;
    if (!setProps) return;
    pushes += 1; // a value the server has not seen yet, even when the stamp repeats
    setProps(STORE_ID, { data: { stamp: new Date(moment).toISOString(), n: pushes } });
  }

  // The tab was rendered (or rendered again): its anchor node is new. Compare
  // with the previous visit, then record this one.
  function openVisit() {
    var anchor = document.getElementById(ANCHOR_ID);
    if (!anchor || anchor.dataset.wtValenciaOpened) return;
    anchor.dataset.wtValenciaOpened = "1";
    baseline = readStamp();
    if (baseline === null) {
      writeStamp(Date.now()); // First visit ever: nothing to compare with.
      return;
    }
    push(baseline);
    writeStamp(Date.now());
  }

  function makePill() {
    var pill = document.createElement("span");
    pill.className = BADGE_CLASS;
    pill.textContent = "NUEVO";
    pill.title = "Detectado después de tu última visita";
    pill.style.cssText = BADGE_CSS;
    return pill;
  }

  function applyNewBadges() {
    document.querySelectorAll(ROW_SEL).forEach(function (row) {
      var detected = Date.parse(row.getAttribute("data-valencia-detected") || "");
      var isNew = baseline !== null && !isNaN(detected) && detected > baseline;
      var pill = row.querySelector("." + BADGE_CLASS);
      if (isNew && !pill) {
        var host = row.querySelector("a") || row.firstChild;
        if (host && host.parentElement) host.parentElement.insertBefore(makePill(), host);
      } else if (!isNew && pill && pill.parentNode) {
        pill.parentNode.removeChild(pill);
      }
    });
  }

  // "Marcar como vistos": nothing was detected after "now", so the server
  // empties the notice; the pills of this page go with the moved baseline.
  function onMarkSeen(event) {
    var target = event.target;
    var btn = target && target.closest ? target.closest("#" + MARK_SEEN_ID) : null;
    if (!btn) return;
    event.preventDefault();
    baseline = Date.now();
    writeStamp(baseline);
    push(baseline);
    applyNewBadges();
  }

  function refresh() {
    openVisit();
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
    // Delegated at the document: the button is inside the tab, re-created on every render.
    document.addEventListener("click", onMarkSeen);
    refresh();
    var target = document.getElementById("tab-content") || document.body;
    if (!target.dataset.wtValenciaObserved) {
      target.dataset.wtValenciaObserved = "1";
      new MutationObserver(scheduleRefresh).observe(target, { childList: true, subtree: true });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
