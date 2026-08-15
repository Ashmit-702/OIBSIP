/* static/js/dashboard.js */

(function () {
  var root = document.getElementById("dashboard-root");
  var openBtn = document.getElementById("open-checkin");
  var modal = document.getElementById("checkin-modal");
  var closeBtn = document.getElementById("close-checkin");
  var form = document.getElementById("checkin-form");
  var errorBox = document.getElementById("checkin-error");
  var dateInput = document.getElementById("ci-date");

  dateInput.value = new Date().toISOString().slice(0, 10);

  function pillClass(category) {
    return "metric-card__pill pill--" + category;
  }

  function openModal() { modal.style.display = "flex"; errorBox.style.display = "none"; }
  function closeModal() { modal.style.display = "none"; }

  function renderEmpty() {
    root.innerHTML =
      '<div class="empty-state">' +
      '<div class="empty-state__icon">+</div>' +
      "<h3>No health records yet.</h3>" +
      "<p>Add your first check-in to start seeing your dashboard.</p>" +
      '<button class="btn-primary" id="empty-checkin-btn">Add Check-in</button>' +
      "</div>";
    document.getElementById("empty-checkin-btn").addEventListener("click", openModal);
  }

  function renderError(message) {
    root.innerHTML = '<div class="error-banner">' + escapeHtml(message) + "</div>";
  }

  function trendCaption(change) {
    if (change === null || change === undefined) return "Not enough data yet";
    if (change === 0) return "No change this month";
    var dir = change < 0 ? "is-down" : "is-up";
    var arrow = change < 0 ? "\u2193" : "\u2191";
    return '<span class="metric-card__caption ' + dir + '">' + arrow + " " + Math.abs(change).toFixed(1) + " kg this month</span>";
  }

  function render(data) {
    if (!data.has_data) {
      renderEmpty();
      return;
    }

    var goalCard = "-";
    var goalCaption = "No goal set";
    if (data.goal_summary && data.goal_summary.progress) {
      goalCard = data.goal_summary.target_weight_kg + " kg";
      goalCaption = data.goal_summary.progress.percent + "% complete";
    }

    var wellnessScore = data.wellness_score ? data.wellness_score.score : "-";

    var todaysHtml = "";
    var tp = data.today_progress;
    if (tp) {
      todaysHtml =
        '<div class="card" style="margin-bottom:22px;">' +
        "<h3 class=\"chart-card__title\">Today's Progress</h3>" +
        '<div class="stat-grid" style="margin-bottom:0;">' +
        '<div class="stat-box"><div class="stat-box__label">Water</div><div class="stat-box__value">' +
        (tp.water_l != null ? tp.water_l : "0") + " / " + tp.water_target_l + " L</div></div>" +
        '<div class="stat-box"><div class="stat-box__label">Steps</div><div class="stat-box__value">' +
        (tp.steps != null ? tp.steps.toLocaleString() : "0") + " / " + tp.steps_target.toLocaleString() + "</div></div>" +
        '<div class="stat-box"><div class="stat-box__label">Sleep</div><div class="stat-box__value">' +
        (tp.sleep_hours != null ? tp.sleep_hours + " hrs" : "-") + "</div></div>" +
        '<div class="stat-box"><div class="stat-box__label">Logged today</div><div class="stat-box__value">' +
        (tp.logged_today ? "Yes" : "Not yet") + "</div></div>" +
        "</div></div>";
    }

    var insightsHtml = "";
    if (data.top_insights && data.top_insights.length) {
      insightsHtml =
        '<div class="card"><h3 class="chart-card__title">Recent Insights</h3><ul class="insight-list">' +
        data.top_insights.map(function (i) { return "<li>" + escapeHtml(i) + "</li>"; }).join("") +
        "</ul></div>";
    }

    root.innerHTML =
      '<div class="summary-grid">' +
      '<div class="card metric-card"><span class="metric-card__label">BMI</span>' +
      '<span class="metric-card__value">' + data.bmi + "</span>" +
      '<span class="' + pillClass(data.category) + '">' + data.category + "</span></div>" +

      '<div class="card metric-card"><span class="metric-card__label">Weight</span>' +
      '<span class="metric-card__value">' + data.current_weight + " kg</span>" +
      trendCaption(data.month_change) + "</div>" +

      '<div class="card metric-card"><span class="metric-card__label">Goal</span>' +
      '<span class="metric-card__value">' + goalCard + "</span>" +
      '<span class="metric-card__caption">' + goalCaption + "</span></div>" +

      '<div class="card metric-card"><span class="metric-card__label">Consistency</span>' +
      '<span class="metric-card__value">' + wellnessScore + "/100</span>" +
      '<span class="metric-card__caption">Wellness Consistency Score</span></div>' +
      "</div>" +
      todaysHtml + insightsHtml;
  }

  function load() {
    apiRequest("/api/dashboard")
      .then(render)
      .catch(function (err) { renderError(err.message); });
  }

  openBtn.addEventListener("click", openModal);
  closeBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var payload = {
      entry_date: document.getElementById("ci-date").value,
      weight_kg: document.getElementById("ci-weight").value,
      water_l: document.getElementById("ci-water").value || null,
      steps: document.getElementById("ci-steps").value || null,
      sleep_hours: document.getElementById("ci-sleep").value || null,
      waist_cm: document.getElementById("ci-waist").value || null,
      calories: document.getElementById("ci-calories").value || null,
    };
    var submitBtn = form.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving...";

    apiRequest("/api/health", { method: "POST", body: JSON.stringify(payload) })
      .then(function () {
        showToast("Check-in saved.", "success");
        closeModal();
        form.reset();
        dateInput.value = new Date().toISOString().slice(0, 10);
        load();
      })
      .catch(function (err) {
        errorBox.textContent = err.message;
        errorBox.style.display = "block";
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "Save Check-in";
      });
  });

  load();
})();
