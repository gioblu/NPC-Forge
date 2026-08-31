/* theme extras · ecommerce
   Hooks: .add buttons, [data-cart="2"] badge (number = starting count). */
(() => {
  "use strict";
  const badge = document.querySelector("[data-cart]");
  let count = badge ? +(badge.dataset.cart || 0) : 0;

  document.querySelectorAll(".add").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.disabled) return;                       // ignore while "Added ✓"
      if (badge) badge.textContent = `Cart · ${++count}`;
      const label = btn.textContent;
      btn.textContent = "Added ✓";
      btn.disabled = true;
      setTimeout(() => { btn.textContent = label; btn.disabled = false; }, 1400);
    });
  });
})();