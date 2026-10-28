/* Snooker Century — tiny progressive-enhancement helpers (everything works without JS). */
(function () {
  "use strict";

  // Theme toggle (light / dark), remembered per browser.
  var root = document.documentElement;
  var toggle = document.querySelector("[data-theme-toggle]");
  function applyIcon() {
    if (!toggle) return;
    var dark = root.getAttribute("data-bs-theme") === "dark";
    toggle.innerHTML = '<i class="bi ' + (dark ? "bi-sun-fill" : "bi-moon-stars-fill") + '"></i>';
    toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }
  if (toggle) {
    applyIcon();
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      try { localStorage.setItem("sc-theme", next); } catch (e) {}
      applyIcon();
    });
  }

  // Show / hide password.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-toggle-pw]");
    if (!btn) return;
    var input = btn.parentElement.querySelector("input");
    if (!input) return;
    var show = input.type === "password";
    input.type = show ? "text" : "password";
    btn.innerHTML = '<i class="bi ' + (show ? "bi-eye-slash" : "bi-eye") + '"></i>';
    btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
  });

  // Quick-fill buttons for the score input.
  document.addEventListener("click", function (e) {
    var btn = e.target.closest("[data-fill]");
    if (!btn) return;
    var input = document.querySelector(btn.getAttribute("data-target"));
    if (!input) return;
    input.value = btn.getAttribute("data-fill");
    input.focus();
  });

  // Prevent double submits (slow mobile connections).
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.matches("form[data-once]")) return;
    var btn = form.querySelector('[type="submit"]');
    if (btn) {
      setTimeout(function () { btn.disabled = true; btn.classList.add("disabled"); }, 0);
    }
  });

  // Auto-dismiss success flashes.
  document.querySelectorAll(".alert-success[data-autohide]").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 450);
    }, 4500);
  });
})();
