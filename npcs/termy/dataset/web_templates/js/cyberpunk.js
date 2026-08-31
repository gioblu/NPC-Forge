/* theme extras · cyberpunk
   Hooks: [data-uptime] in the status line, .glitch heading. */
(() => {
  "use strict";

  /* Live uptime counter in the terminal footer. */
  const up = document.querySelector("[data-uptime]");
  if (up) {
    let s = 214 * 3600 + 7 * 60 + 33;                 // seed: 214:07:33
    const pad = (n) => String(n).padStart(2, "0");
    setInterval(() => {
      s++;
      up.textContent = `${Math.floor(s / 3600)}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}`;
    }, 1000);
  }

  /* Random glitch bursts on the heading: the .burst class is defined
     in cyberpunk.css and removed again after 180 ms. */
  const g = document.querySelector(".glitch");
  if (g) setInterval(() => {
    g.classList.add("burst");
    setTimeout(() => g.classList.remove("burst"), 180);
  }, 2600 + Math.random() * 2000);
})();