/* Snooker Century — tiny progressive-enhancement helpers (everything works without JS). */
(function () {
  "use strict";

  // Theme toggle (light / dark), remembered per browser.
  var root = document.documentElement;
  function applyIcon() {
    var toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) return;
    var dark = root.getAttribute("data-bs-theme") === "dark";
    toggle.innerHTML = '<i class="bi ' + (dark ? "bi-sun-fill" : "bi-moon-stars-fill") + '"></i>';
    toggle.setAttribute("aria-label", dark ? "Switch to light theme" : "Switch to dark theme");
  }
  applyIcon();

  // Show / hide password.
  document.addEventListener("click", function (e) {
    if (!(e.target instanceof Element)) return;
    var themeButton = e.target.closest("[data-theme-toggle]");
    if (themeButton) {
      var next = root.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      try { localStorage.setItem("sc-theme", next); } catch (e) {}
      applyIcon();
      return;
    }

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
    if (!(e.target instanceof Element)) return;
    var btn = e.target.closest("[data-fill]");
    if (!btn) return;
    var input = document.querySelector(btn.getAttribute("data-target"));
    if (!input) return;
    input.value = btn.getAttribute("data-fill");
    input.focus();
  });

  function showPage(html, url, addHistory) {
    var nextPage = new DOMParser().parseFromString(html, "text/html");
    if (!nextPage.body) {
      throw new Error("The server returned a page that could not be displayed.");
    }
    if (!nextPage.querySelector("main")) {
      window.location.assign(url);
      return;
    }

    document.title = nextPage.title;
    document.body.className = nextPage.body.className;
    document.body.innerHTML = nextPage.body.innerHTML;

    var destination = new URL(url, window.location.href);
    if (addHistory && destination.href !== window.location.href) {
      window.history.pushState({}, "", destination);
    }
    window.scrollTo(0, 0);
    applyIcon();
    dismissSuccessAlerts();
  }

  function showRequestError(message, form) {
    var alert = document.createElement("div");
    alert.className = "alert alert-danger";
    alert.setAttribute("role", "alert");
    alert.textContent = message;
    var container = form || document.querySelector("main");
    if (container) container.prepend(alert);
  }

  function requestPage(url, options, addHistory, form) {
    return fetch(url, options).then(function (response) {
      return response.text().then(function (body) {
        var contentType = response.headers.get("content-type") || "";
        if (contentType.indexOf("application/json") !== -1) {
          var data;
          try {
            data = JSON.parse(body);
          } catch (error) {
            throw new Error("The server returned an invalid response.");
          }
          if (!response.ok || data.success === false) {
            if (form) showRequestError(data.error || "The request could not be completed.", form);
            return;
          }
          return fetch(response.url || url, {
            headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "text/html" }
          }).then(function (pageResponse) {
            if (!pageResponse.ok) throw new Error("The updated page could not be loaded.");
            return pageResponse.text().then(function (page) {
              showPage(page, pageResponse.url || response.url || url, addHistory);
            });
          });
        }

        showPage(body, response.url || url, addHistory);
      });
    }).catch(function (error) {
      showRequestError(error.message || "Unable to connect. Please try again.", form);
    });
  }

  // Submit same-origin forms without a full-page navigation.
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement) || form.hasAttribute("data-no-ajax") || form.target) return;
    var method = (form.method || "get").toLowerCase();
    if (method !== "get" && method !== "post") return;
    var url = new URL(form.action || window.location.href, window.location.href);
    if (url.origin !== window.location.origin || !/^https?:$/.test(url.protocol)) return;

    event.preventDefault();
    if (form.dataset.ajaxSubmitting === "true") return;
    form.dataset.ajaxSubmitting = "true";

    var submitButton = form.querySelector('[type="submit"]');
    if (submitButton) submitButton.disabled = true;

    var options = {
      method: method.toUpperCase(),
      headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "text/html, application/json" }
    };
    if (method === "get") {
      url.search = "";
      new FormData(form).forEach(function (value, key) {
        if (typeof value === "string") url.searchParams.append(key, value);
      });
    } else {
      options.body = new FormData(form);
    }

    requestPage(url, options, true, form).finally(function () {
      if (form.isConnected) {
        delete form.dataset.ajaxSubmitting;
        if (submitButton && submitButton.isConnected) submitButton.disabled = false;
      }
    });
  });

  // Keep ordinary internal navigation in the same asynchronous page flow.
  document.addEventListener("click", function (event) {
    if (!(event.target instanceof Element)) return;
    var link = event.target.closest("a[href]");
    if (!link || link.hasAttribute("data-no-ajax") || link.target || link.hasAttribute("download")
      || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;

    var destination = new URL(link.href, window.location.href);
    if (destination.origin !== window.location.origin || !/^https?:$/.test(destination.protocol)) return;
    if (destination.href === window.location.href || (destination.pathname === window.location.pathname
      && destination.search === window.location.search && destination.hash)) return;

    event.preventDefault();
    requestPage(destination, {
      headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "text/html" }
    }, true);
  });

  window.addEventListener("popstate", function () {
    requestPage(window.location.href, {
      headers: { "X-Requested-With": "XMLHttpRequest", "Accept": "text/html" }
    }, false);
  });

  function dismissSuccessAlerts() {
    document.querySelectorAll(".alert-success[data-autohide]").forEach(function (el) {
      setTimeout(function () {
        if (!el.isConnected) return;
        el.style.transition = "opacity .4s";
        el.style.opacity = "0";
        setTimeout(function () { el.remove(); }, 450);
      }, 4500);
    });
  }

  // Prevent double submits (slow mobile connections).
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.matches("form[data-once]")) return;
    var btn = form.querySelector('[type="submit"]');
    if (btn) {
      setTimeout(function () { btn.disabled = true; btn.classList.add("disabled"); }, 0);
    }
  });

  dismissSuccessAlerts();
})();
