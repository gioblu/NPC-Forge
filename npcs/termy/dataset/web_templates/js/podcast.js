/* theme extras · podcast — ticks the "now playing" elapsed time.
   Hook: [data-elapsed] in the deck. */
(() => {
  "use strict";
  const el = document.querySelector("[data-elapsed]");
  if (!el) return;
  let s = 34 * 60 + 12;                          // seed: 34:12
  const pad = (n) => String(n).padStart(2, "0");
  setInterval(() => {
    s++;
    el.textContent = `${Math.floor(s / 60)}:${pad(s % 60)}`;
  }, 1000);
})();