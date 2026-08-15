/* static/js/analytics.js */

(function () {
  var root = document.getElementById("analytics-root");
  var filterGroup = document.getElementById("window-filter");
  var currentWindow = "All";
  var weightChart = null;
  var bmiChart = null;
  var consistencyChart = null;

  function renderEmpty() {
    root.innerHTML =
      '<div class="empty-state">' +
      '<div class="empty-state__icon">+</div>' +
      "<h3>No health records yet.</h3>" +
      "<p>Add your first check-in to start seeing trends.</p>" +
      '<a href="/dashboard" class="btn-primary">Add Check-in</a>' +
      "</div>";
  }

  function renderError(message) {
    root.innerHTML = '<div class="error-banner">' + escapeHtml(message) + "</div>";
  }

  function chartTextColor() {
    var dark = document.documentElement.getAttribute("data-theme") === "dark";
    return dark ? "#93ABA5" : "#57707B";
  }

  function buildSkeletonLayout() {
    root.innerHTML =
      '<div class="stat-grid" id="stat-grid"></div>' +
      '<div class="card chart-card"><h3 class="chart-card__title">Weight Trend</h3>' +
      '<div class="chart-wrap"><canvas id="weight-chart"></canvas></div></div>' +
      '<div class="card chart-card"><h3 class="chart-card__title">BMI Trend</h3>' +
      '<div class="chart-wrap"><canvas id="bmi-chart"></canvas></div></div>' +
      '<div class="card chart-card"><h3 class="chart-card__title">Weekly Logging Consistency</h3>' +
      '<div class="chart-wrap"><canvas id="consistency-chart"></canvas></div></div>' +
      '<div class="card chart-card" id="forecast-card"></div>';
  }

  function renderStats(stats, consistency) {
    var grid = document.getElementById("stat-grid");
    var items = [
      { label: "Average weight", value: stats.average_weight != null ? stats.average_weight + " kg" : "-" },
      { label: "Total change", value: stats.total_change != null ? (stats.total_change > 0 ? "+" : "") + stats.total_change + " kg" : "-" },
      { label: "Avg weekly change", value: stats.weekly_rate != null ? stats.weekly_rate + " kg/wk" : "-" },
      { label: "Logging consistency", value: consistency.percent + "%" },
    ];
    grid.innerHTML = items.map(function (i) {
      return '<div class="stat-box"><div class="stat-box__label">' + i.label +
        '</div><div class="stat-box__value">' + i.value + "</div></div>";
    }).join("");
  }

  function renderCharts(weightSeries, bmiSeries, weeklyBars) {
    var textColor = chartTextColor();
    var gridColor = "rgba(150,150,150,0.15)";

    if (weightChart) weightChart.destroy();
    if (bmiChart) bmiChart.destroy();
    if (consistencyChart) consistencyChart.destroy();

    weightChart = new Chart(document.getElementById("weight-chart"), {
      type: "line",
      data: {
        labels: weightSeries.labels,
        datasets: [{ label: "Weight (kg)", data: weightSeries.values, borderColor: "#0F6E63",
          backgroundColor: "rgba(15,110,99,0.08)", fill: true, tension: 0.3, pointRadius: 2 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: textColor, maxTicksLimit: 8 }, grid: { color: gridColor } },
          y: { ticks: { color: textColor }, grid: { color: gridColor } },
        },
      },
    });

    bmiChart = new Chart(document.getElementById("bmi-chart"), {
      type: "line",
      data: {
        labels: bmiSeries.labels,
        datasets: [{ label: "BMI", data: bmiSeries.values, borderColor: "#2564C4",
          backgroundColor: "rgba(37,100,196,0.08)", fill: true, tension: 0.3, pointRadius: 2 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: textColor, maxTicksLimit: 8 }, grid: { color: gridColor } },
          y: { ticks: { color: textColor }, grid: { color: gridColor } },
        },
      },
    });

    consistencyChart = new Chart(document.getElementById("consistency-chart"), {
      type: "bar",
      data: {
        labels: weeklyBars.buckets.map(function (b) { return b.label; }),
        datasets: [{ label: "Days logged", data: weeklyBars.buckets.map(function (b) { return b.days_logged; }),
          backgroundColor: "#0F6E63", borderRadius: 5 }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: textColor }, grid: { display: false } },
          y: { ticks: { color: textColor, stepSize: 1 }, grid: { color: gridColor }, max: 7 },
        },
      },
    });
  }

  function renderForecast(forecast) {
    var card = document.getElementById("forecast-card");
    if (!forecast.available) {
      card.innerHTML = '<h3 class="chart-card__title">Forecast</h3><p style="color:var(--ink-soft);font-size:0.88rem;">' +
        escapeHtml(forecast.reason || "Not enough data yet.") + "</p>";
      return;
    }
    card.innerHTML =
      '<h3 class="chart-card__title">Forecast</h3>' +
      '<p style="font-size:0.9rem;color:var(--ink-soft);margin:0;">' +
      "Trend is currently <strong>" + forecast.trend_direction + "</strong> at about " +
      Math.abs(forecast.weight_change_per_week) + " kg/week. In " + forecast.projected_days +
      " days, projected weight is approximately <strong>" + forecast.projected_weight + " kg</strong> " +
      "(BMI " + forecast.projected_bmi + "). Confidence: " + forecast.confidence + "." +
      "</p>";
  }

  function load() {
    buildSkeletonLayout();
    apiRequest("/api/analytics?window=" + encodeURIComponent(currentWindow))
      .then(function (data) {
        if (!data.has_data) { renderEmpty(); return; }
        renderStats(data.weight_stats, data.consistency);
        renderCharts(data.weight_series, data.bmi_series, data.weekly_consistency);
        renderForecast(data.forecast);
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

  window.addEventListener("vitals-theme-changed", load);

  load();
})();
