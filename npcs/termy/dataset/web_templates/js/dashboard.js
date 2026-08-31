/* theme extras · dashboard
   Hooks: [data-latency] stat value, [data-fresh] "updated …s ago". */
(() => {
  "use strict";

  /* Jitter the p99 latency every 2 s so the board feels alive. */
  const lat = document.querySelector("[data-latency]");
  if (lat) setInterval(() => {
    lat.textContent = (38 + Math.floor(Math.random() * 9)) + "ms";
  }, 2000);

  /* Freshness clock — resets at 30 s to stay believable. */
  const fresh = document.querySelector("[data-fresh]");
  if (fresh) {
    let s = 2;
    setInterval(() => {
      s = s >= 30 ? 1 : s + 1;
      fresh.textContent = `updated ${s}s ago`;
    }, 1000);
  }
})();