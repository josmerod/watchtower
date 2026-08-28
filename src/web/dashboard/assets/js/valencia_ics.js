/* Clientside .ics export for the Valencia Events tab (spec 08, VA2 / T-068).
 *
 * The tab renders a hidden Div (#valencia-ics-events) whose data-events
 * attribute carries compact JSON of the upcoming (from today) events. A single
 * delegated click listener on document builds an RFC 5545 VCALENDAR and
 * triggers a Blob download of "watchtower_valencia.ics" — no server
 * round-trip. Delegation survives Dash re-renders, so no MutationObserver
 * is needed here.
 */
(function () {
  var BTN_ID = "valencia-ics-export-btn";
  var DATA_ID = "valencia-ics-events";
  var FILENAME = "watchtower_valencia.ics";

  /* RFC 5545 TEXT escaping: backslash first, newlines, then ; and , */
  function esc(v) {
    return String(v || "")
      .replace(/\\/g, "\\\\")
      .replace(/\r\n/g, "\\n")
      .replace(/\n/g, "\\n")
      .replace(/\r/g, "\\n")
      .replace(/;/g, "\\;")
      .replace(/,/g, "\\,");
  }

  /* FNV-1a 32-bit: stable, dependency-free UID hash. */
  function hash(s) {
    var h = 0x811c9dc5;
    for (var i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = (h + (h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24)) >>> 0;
    }
    return ("0000000" + h.toString(16)).slice(-8);
  }

  function pad2(n) {
    return ("0" + n).slice(-2);
  }

  function stampNow() {
    var d = new Date();
    return (
      d.getUTCFullYear() + pad2(d.getUTCMonth() + 1) + pad2(d.getUTCDate()) +
      "T" + pad2(d.getUTCHours()) + pad2(d.getUTCMinutes()) + pad2(d.getUTCSeconds()) + "Z"
    );
  }

  /* Parse YYYY-MM-DD[(T| )HH:MM[:SS]] or DD/MM/YYYY → {date:'YYYYMMDD', time:'THHMMSS'|null}. */
  function parseWhen(s) {
    if (!s) return null;
    s = String(s).trim();
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2}))?)?/);
    if (m) return { date: m[1] + m[2] + m[3], time: m[4] ? "T" + m[4] + m[5] + (m[6] || "00") : null };
    m = s.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
    if (m) return { date: m[3] + m[2] + m[1], time: m[4] ? "T" + m[4] + m[5] + "00" : null };
    return null;
  }

  /* All-day DTEND is the exclusive end: last day + 1. */
  function nextDay(yyyymmdd) {
    var d = new Date(Date.UTC(+yyyymmdd.slice(0, 4), +yyyymmdd.slice(4, 6) - 1, +yyyymmdd.slice(6, 8)));
    d.setUTCDate(d.getUTCDate() + 1);
    return d.getUTCFullYear() + pad2(d.getUTCMonth() + 1) + pad2(d.getUTCDate());
  }

  /* UTF-8 byte length of one JS char (surrogate halves count 2 so a pair totals 4). */
  function byteLen(ch) {
    var c = ch.charCodeAt(0);
    if (c < 0x80) return 1;
    if (c < 0x800) return 2;
    if (c >= 0xd800 && c <= 0xdfff) return 2;
    return 3;
  }

  /* RFC 5545 3.1: fold at 75 octets with CRLF + single space; never split a char. */
  function fold(line) {
    var out = [];
    var cur = "";
    var n = 0;
    for (var i = 0; i < line.length; i++) {
      var ch = line[i];
      var b = byteLen(ch);
      if (n + b > 75) {
        out.push(cur);
        cur = " ";
        n = 1;
      }
      cur += ch;
      n += b;
    }
    out.push(cur);
    return out.join("\r\n");
  }

  function buildIcs(events) {
    var lines = [
      "BEGIN:VCALENDAR",
      "VERSION:2.0",
      "PRODID:-//Watchtower//Valencia Events//EN",
      "CALSCALE:GREGORIAN"
    ];
    var stamp = stampNow();
    events.forEach(function (ev) {
      var when = parseWhen(ev.start_date);
      if (!when) return; // no usable date → skip the event
      lines.push("BEGIN:VEVENT");
      lines.push("UID:wt-valencia-" + hash((ev.url || "") + "|" + (ev.title || "") + "|" + (ev.start_date || "")) + "@watchtower");
      lines.push("DTSTAMP:" + stamp);
      lines.push(when.time ? "DTSTART:" + when.date + when.time : "DTSTART;VALUE=DATE:" + when.date);
      var end = parseWhen(ev.end_date);
      if (end && (end.date > when.date || (end.date === when.date && end.time))) {
        lines.push(end.time ? "DTEND:" + end.date + end.time : "DTEND;VALUE=DATE:" + nextDay(end.date));
      }
      lines.push("SUMMARY:" + esc(ev.title));
      if (ev.url) lines.push("URL:" + ev.url);
      if (ev.location) lines.push("LOCATION:" + esc(ev.location));
      lines.push("END:VEVENT");
    });
    lines.push("END:VCALENDAR");
    return lines.map(fold).join("\r\n") + "\r\n";
  }

  function download(text) {
    var blob = new Blob([text], { type: "text/calendar;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = FILENAME;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 1000);
  }

  document.addEventListener(
    "click",
    function (e) {
      var target = e.target;
      var btn = target && target.closest ? target.closest("#" + BTN_ID) : null;
      if (!btn) return;
      e.preventDefault();
      var holder = document.getElementById(DATA_ID);
      if (!holder) return;
      var events;
      try {
        events = JSON.parse(holder.getAttribute("data-events") || "[]");
      } catch (err) {
        return; // malformed payload → no-op rather than a broken download
      }
      if (!events.length) return;
      download(buildIcs(events));
    },
    false
  );
})();
