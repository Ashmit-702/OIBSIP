/* static/js/goals.js */

(function () {
  var root = document.getElementById("goals-root");
  var openBtn = document.getElementById("open-goal-form");
  var modal = document.getElementById("goal-modal");
  var closeBtn = document.getElementById("close-goal-modal");
  var form = document.getElementById("goal-form");
  var errorBox = document.getElementById("goal-error");

  function openModal() { modal.style.display = "flex"; errorBox.style.display = "none"; }
  function closeModal() { modal.style.display = "none"; }

  function renderNoGoal() {
    root.innerHTML =
      '<div class="empty-state">' +
      '<div class="empty-state__icon">+</div>' +
      "<h3>No goal set yet.</h3>" +
      "<p>Set a target weight and date to start tracking your pace toward it.</p>" +
      '<button class="btn-primary" id="empty-goal-btn">Set a Goal</button>' +
      "</div>";
    document.getElementById("empty-goal-btn").addEventListener("click", openModal);
  }

  function renderNoRecords() {
    root.innerHTML =
      '<div class="empty-state">' +
      '<div class="empty-state__icon">+</div>' +
      "<h3>No health records yet.</h3>" +
      "<p>Log a check-in to start tracking progress toward your goal.</p>" +
      '<a href="/dashboard" class="btn-primary">Add Check-in</a>' +
      "</div>";
  }

  function renderError(message) {
    root.innerHTML = '<div class="error-banner">' + escapeHtml(message) + "</div>";
  }

  function render(goal, summary) {
    if (!goal) { renderNoGoal(); return; }
    if (!summary) { renderNoRecords(); return; }

    var p = summary.progress;
    var pace = summary.required_pace;
    var completion = summary.estimated_completion;

    var paceHtml = "";
    if (pace) {
      if (pace.days_remaining <= 0) {
        paceHtml = '<p style="color:var(--ink-soft);font-size:0.88rem;">Your target date has passed.</p>';
      } else {
        paceHtml =
          '<div class="stat-box" style="margin-top:14px;">' +
          '<div class="stat-box__label">Pace required to hit target date</div>' +
          '<div class="stat-box__value">' + pace.weekly_kg_required + " kg/week</div>" +
          "</div>";
        if (!pace.feasible) {
          paceHtml += '<p style="color:var(--zone-over);font-size:0.82rem;margin-top:8px;">' +
            "This pace is faster than commonly recommended guidance — consider a later target date.</p>";
        }
      }
    }

    var completionHtml = "";
    if (completion.available) {
      completionHtml =
        '<div class="stat-box">' +
        '<div class="stat-box__label">Estimated completion (at current trend)</div>' +
        '<div class="stat-box__value">' + (completion.eta_date || "-") + "</div>" +
        "</div>";
    } else {
      completionHtml = '<p style="color:var(--ink-soft);font-size:0.85rem;">' +
        escapeHtml(completion.reason) + "</p>";
    }

    root.innerHTML =
      '<div class="card" style="margin-bottom:20px;">' +
      '<h3 class="chart-card__title">' + summary.goal_type.charAt(0).toUpperCase() + summary.goal_type.slice(1) +
      " to " + summary.target_weight_kg + " kg</h3>" +
      '<div class="progress-track" style="margin-bottom:8px;">' +
      '<div class="progress-fill" style="width:' + p.percent + '%;"></div></div>' +
      '<p style="font-size:0.88rem;color:var(--ink-soft);margin:0;">' +
      p.start_weight + " kg &rarr; " + p.current_weight + " kg &rarr; " + p.target_weight + " kg &middot; " +
      "<strong>" + p.percent + "% complete</strong> &middot; " + Math.abs(p.remaining_kg) + " kg remaining" +
      "</p>" + paceHtml + "</div>" +
      '<div class="stat-grid" style="grid-template-columns:1fr 1fr;">' + completionHtml + "</div>";
  }

  function load() {
    apiRequest("/api/goals")
      .then(function (data) { render(data.goal, data.summary); })
      .catch(function (err) { renderError(err.message); });
  }

  openBtn.addEventListener("click", openModal);
  closeBtn.addEventListener("click", closeModal);
  modal.addEventListener("click", function (e) { if (e.target === modal) closeModal(); });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var goalTypeInput = form.querySelector('input[name="goal_type"]:checked');
    if (!goalTypeInput) {
      errorBox.textContent = "Please choose a goal type.";
      errorBox.style.display = "block";
      return;
    }
    var payload = {
      goal_type: goalTypeInput.value,
      target_weight_kg: document.getElementById("goal-target-weight").value,
      target_date: document.getElementById("goal-target-date").value || null,
    };
    var submitBtn = form.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.textContent = "Saving...";

    apiRequest("/api/goals", { method: "POST", body: JSON.stringify(payload) })
      .then(function () {
        showToast("Goal saved.", "success");
        closeModal();
        load();
      })
      .catch(function (err) {
        errorBox.textContent = err.message;
        errorBox.style.display = "block";
      })
      .finally(function () {
        submitBtn.disabled = false;
        submitBtn.textContent = "Save Goal";
      });
  });

  load();
})();
