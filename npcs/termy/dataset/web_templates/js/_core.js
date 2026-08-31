/* ================================================================
   _core.js — interaction engine shared by every theme.
   The generator prepends this file to any theme-specific js.
   Each feature activates only if its hook exists in the markup,
   so a page with no js at all still renders fine.
   ================================================================ */
(() => {
  "use strict";

  /* 1 · SCROLL REVEALS — elements with [data-reveal] fade up the
         first time they enter the viewport, then stop being watched. */
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      e.target.classList.add("is-in");
      io.unobserve(e.target);
    }
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });
  document.querySelectorAll("[data-reveal]").forEach((el) => io.observe(el));

  /* 2 · TYPEWRITER — <span data-type="some text"></span> types itself
         out. Pair it with a .caret element for the blinking cursor. */
  document.querySelectorAll("[data-type]").forEach((el) => {
    const text = el.dataset.type;
    let i = 0;
    const tick = () => {
      el.textContent = text.slice(0, ++i);
      if (i < text.length) setTimeout(tick, 30 + Math.random() * 55);
    };
    setTimeout(tick, 500);
  });

  /* 3 · COUNTERS — [data-count="1204" data-dec="0" data-suffix=" GB"]
         eases from 0 to its target when scrolled into view. */
  const cio = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      const el = e.target,
            end = parseFloat(el.dataset.count),
            dec = +(el.dataset.dec || 0),
            suf = el.dataset.suffix || "";
      const t0 = performance.now(), dur = 1300;
      const step = (t) => {
        const p = Math.min((t - t0) / dur, 1);
        const v = end * (1 - (1 - p) ** 3);           // ease-out cubic
        el.textContent = v.toLocaleString(undefined,
          { minimumFractionDigits: dec, maximumFractionDigits: dec }) + suf;
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      cio.unobserve(el);
    }
  }, { threshold: 0.5 });
  document.querySelectorAll("[data-count]").forEach((el) => cio.observe(el));

  /* 4 · READING PROGRESS — a fixed .progress bar (blog theme) scales
         horizontally with scroll depth. */
  const bar = document.querySelector(".progress");
  if (bar) addEventListener("scroll", () => {
    const h = document.documentElement;
    const max = h.scrollHeight - h.clientHeight;
    bar.style.transform = `scaleX(${max > 0 ? h.scrollTop / max : 0})`;
  }, { passive: true });

  /* 5 · COUNTDOWN — [data-countdown="2026-11-05T09:00:00"] ticks
         every second (event theme). */
  const cd = document.querySelector("[data-countdown]");
  if (cd) {
    const target = new Date(cd.dataset.countdown).getTime();
    const pad = (n) => String(n).padStart(2, "0");
    const render = () => {
      const d = Math.max(0, target - Date.now());
      cd.textContent = `${Math.floor(d / 864e5)}d ${pad(Math.floor(d / 36e5) % 24)}h `
                     + `${pad(Math.floor(d / 6e4) % 60)}m ${pad(Math.floor(d / 1e3) % 60)}s`;
    };
    render();
    setInterval(render, 1000);
  }
})();