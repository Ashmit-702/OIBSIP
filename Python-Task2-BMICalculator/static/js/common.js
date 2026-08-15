/* static/js/common.js — shared across every page */

(function () {
  var toggle = document.getElementById("theme-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var isDark = document.documentElement.getAttribute("data-theme") === "dark";
      if (isDark) {
        document.documentElement.removeAttribute("data-theme");
        localStorage.setItem("vitals-theme", "light");
      } else {
        document.documentElement.setAttribute("data-theme", "dark");
        localStorage.setItem("vitals-theme", "dark");
      }
      window.dispatchEvent(new CustomEvent("vitals-theme-changed"));
    });
  }
})();

function showToast(message, type) {
  var container = document.getElementById("toast-container");
  if (!container) return;
  var toast = document.createElement("div");
  toast.className = "toast" + (type ? " toast--" + type : "");
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(function () {
    toast.style.opacity = "0";
    toast.style.transition = "opacity .25s ease";
    setTimeout(function () { toast.remove(); }, 260);
  }, 3400);
}

async function apiRequest(url, options) {
  options = options || {};
  var headers = Object.assign({}, options.headers || {});
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  var response;
  try {
    response = await fetch(url, Object.assign({}, options, { headers: headers }));
  } catch (networkErr) {
    throw new Error("Network error — please check your connection and try again.");
  }
  var data = null;
  var contentType = response.headers.get("content-type") || "";
  if (contentType.indexOf("application/json") !== -1) {
    data = await response.json().catch(function () { return null; });
  }
  if (!response.ok) {
    var message = (data && data.error) ? data.error : "Something went wrong (" + response.status + ").";
    throw new Error(message);
  }
  return data;
}

function formatKg(value) {
  if (value === null || value === undefined) return "—";
  return value.toFixed(1) + " kg";
}

function escapeHtml(str) {
  var div = document.createElement("div");
  div.textContent = str == null ? "" : String(str);
  return div.innerHTML;
}
