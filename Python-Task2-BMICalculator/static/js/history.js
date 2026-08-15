/* static/js/history.js */

(function () {
  var root = document.getElementById("history-root");
  var searchInput = document.getElementById("history-search");
  var filterGroup = document.getElementById("history-window-filter");
  var exportBtn = document.getElementById("export-csv-btn");
  var currentWindow = "All";
  var allRecords = [];

  function renderEmpty() {
    root.innerHTML =
      '<div class="empty-state">' +
      '<div class="empty-state__icon">+</div>' +
      "<h3>No health records yet.</h3>" +
      "<p>Add your first check-in to start building your history.</p>" +
      '<a href="/dashboard" class="btn-primary">Add Check-in</a>' +
      "</div>";
  }

  function renderError(message) {
    root.innerHTML = '<div class="error-banner">' + escapeHtml(message) + "</div>";
  }

  function renderTable(records) {
    if (!records.length) {
      root.innerHTML = '<div class="empty-state"><h3>No matching entries.</h3><p>Try a different search or time filter.</p></div>';
      return;
    }
    var rows = records.slice().reverse().map(function (r) {
      return "<tr data-id=\"" + r.id + "\">" +
        "<td>" + escapeHtml(r.entry_date) + "</td>" +
        "<td>" + r.weight_kg + " kg</td>" +
        "<td>" + r.bmi + " &middot; " + escapeHtml(r.category) + "</td>" +
        "<td>" + (r.water_l != null ? r.water_l + " L" : "-") + "</td>" +
        "<td>" + (r.steps != null ? r.steps.toLocaleString() : "-") + "</td>" +
        "<td>" + (r.sleep_hours != null ? r.sleep_hours + "h" : "-") + "</td>" +
        "<td><button class=\"table-action-btn table-action-btn--danger\" data-action=\"delete\">Delete</button></td>" +
        "</tr>";
    }).join("");

    root.innerHTML =
      '<div class="data-table-wrap"><table class="data-table"><thead><tr>' +
      "<th>Date</th><th>Weight</th><th>BMI</th><th>Water</th><th>Steps</th><th>Sleep</th><th></th>" +
      "</tr></thead><tbody>" + rows + "</tbody></table></div>";

    root.querySelectorAll('[data-action="delete"]').forEach(function (btn) {
      btn.addEventListener("click", function () {
        var row = btn.closest("tr");
        var id = row.dataset.id;
        if (!confirm("Delete this entry?")) return;
        apiRequest("/api/health/" + id, { method: "DELETE" })
          .then(function () {
            showToast("Entry deleted.", "success");
            load();
          })
          .catch(function (err) { showToast(err.message, "error"); });
      });
    });
  }

  function applyFilters() {
    var query = searchInput.value.trim();
    var filtered = allRecords;
    if (query) {
      filtered = filtered.filter(function (r) { return r.entry_date.indexOf(query) !== -1; });
    }
    renderTable(filtered);
  }

  function load() {
    root.innerHTML = '<div class="skeleton-card skeleton-card--tall"></div>';
    apiRequest("/api/health/history?window=" + encodeURIComponent(currentWindow))
      .then(function (data) {
        allRecords = data.history;
        if (!allRecords.length) { renderEmpty(); return; }
        applyFilters();
      })
      .catch(function (err) { renderError(err.message); });
  }

  filterGroup.addEventListener("click", function (e) {
    var btn = e.target.closest(".filter-btn");
    if (!btn) return;
    filterGroup.querySelectorAll(".filter-btn").forEach(function (b) { b.classList.remove("is-active"); });
    btn.classList.add("is-active");
    currentWindow = btn.dataset.window;
    load();
  });

  searchInput.addEventListener("input", function () {
    if (allRecords.length) applyFilters();
  });

  exportBtn.addEventListener("click", function () {
    window.location.href = "/api/export";
  });

  load();
})();
