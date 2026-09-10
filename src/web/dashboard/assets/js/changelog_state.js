/* Changelog state (T-089): auto-open the 🆕 Novedades modal once per deploy.
 *
 * The server renders the current changelog version into the hidden div
 * #changelog-data ({"version": "..."}). On load we compare it with
 * localStorage "wt_changelog_version":
 *  - different -> show the unread dot on the 🆕 button and programmatically
 *    click it once. The click routes through the guarded Dash open/close
 *    callback (n_clicks >= 1 + prevent_initial_call), so the modal can never
 *    self-open from a callback — the known modal bug class in this repo.
 *    The version is stored BEFORE the click, so a reload does not re-open:
 *    auto-open happens at most once per deploy version.
 *  - same -> keep the dot hidden.
 * Manual clicks on the 🆕 button also mark the version as seen.
 */
(function () {
  var VERSION_KEY = "wt_changelog_version";

  function currentVersion() {
    var holder = document.getElementById("changelog-data");
    if (!holder) return null;
    try {
      return (JSON.parse(holder.textContent || "{}") || {}).version || null;
    } catch (e) {
      return null;
    }
  }

  function markSeen(version) {
    try {
      localStorage.setItem(VERSION_KEY, version);
    } catch (e) {
      /* private mode / storage full — auto-open still at most once per load */
    }
  }

  function setDot(visible) {
    var dot = document.getElementById("changelog-new-dot");
    if (dot) dot.style.display = visible ? "block" : "none";
  }

  function init() {
    var version = currentVersion();
    if (!version) return;
    var seen = null;
    try {
      seen = localStorage.getItem(VERSION_KEY);
    } catch (e) {
      /* ignore unreadable storage */
    }
    if (seen === version) {
      setDot(false);
      return;
    }
    setDot(true);
    var btn = document.getElementById("changelog-open-button");
    if (btn) {
      markSeen(version); // store BEFORE opening: a reload must not re-open
      btn.click();
    }
  }

  // User opens manually -> mark seen + clear the dot.
  document.addEventListener(
    "click",
    function (e) {
      var target = e.target;
      if (!target || !target.closest) return;
      if (!target.closest("#changelog-open-button")) return;
      var version = currentVersion();
      if (version) markSeen(version);
      setDot(false);
    },
    true
  );

  // Dash hydrates asynchronously: the button may not exist at DOMContentLoaded.
  // Wait for it with a MutationObserver (same idea as read_state.js) plus a
  // safety timeout, then run init exactly once.
  var done = false;

  function ready() {
    if (done) return;
    if (!document.getElementById("changelog-open-button")) return;
    done = true;
    init();
  }

  function start() {
    ready();
    if (done) return;
    var observer = new MutationObserver(ready);
    observer.observe(document.body, { childList: true, subtree: true });
    setTimeout(function () {
      observer.disconnect();
      ready();
    }, 10000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
