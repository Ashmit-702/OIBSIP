/**
 * script.js
 * Vitals frontend logic: unit conversion, dark mode, returning-user recognition,
 * form submission, gauge animation, stat cards, goal tracking, streaks &
 * achievements, community stats, multi-metric trend chart, PDF/CSV export,
 * and a custom toast/modal system (replacing browser alert/confirm).
 */

/* ================= Toast system ================= */
const toastContainer = document.getElementById("toast-container");

function showToast(message, type) {
  const toast = document.createElement("div");
  toast.className = "toast" + (type ? " toast--" + type : "");
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(function () {
    toast.classList.add("toast--leaving");
    setTimeout(function () { toast.remove(); }, 250);
  }, 3200);
}

/* ================= Confirm modal system ================= */
const modalOverlay = document.getElementById("modal-overlay");
const modalText = document.getElementById("modal-text");
const modalCancel = document.getElementById("modal-cancel");
const modalConfirm = document.getElementById("modal-confirm");
let modalConfirmCallback = null;

function showConfirmModal(text, onConfirm) {
  modalText.textContent = text;
  modalConfirmCallback = onConfirm;
  modalOverlay.style.display = "flex";
}

function hideConfirmModal() {
  modalOverlay.style.display = "none";
  modalConfirmCallback = null;
}

modalCancel.addEventListener("click", hideConfirmModal);
modalOverlay.addEventListener("click", function (e) {
  if (e.target === modalOverlay) hideConfirmModal();
});
modalConfirm.addEventListener("click", function () {
  const cb = modalConfirmCallback;
  hideConfirmModal();
  if (cb) cb();
});

/* ================= Element refs ================= */
const form = document.getElementById("bmi-form");
const calcBtn = document.getElementById("calc-btn");
const formError = document.getElementById("form-error");
const usernameInput = document.getElementById("username");
const greeting = document.getElementById("greeting");
const knownUsersList = document.getElementById("known-users");

const bmiValueEl = document.getElementById("bmi-value");
const bmiCategoryEl = document.getElementById("bmi-category");
const needle = document.getElementById("needle");

const insightText = document.getElementById("insight-text");
const copyBtn = document.getElementById("copy-btn");
const shareBtn = document.getElementById("share-btn");
const clearBtn = document.getElementById("clear-btn");
const downloadPdfBtn = document.getElementById("download-pdf-btn");
const downloadCsvBtn = document.getElementById("download-csv-btn");

const streakRow = document.getElementById("streak-row");
const streakBadge = document.getElementById("streak-badge");
const achievementsRow = document.getElementById("achievements-row");

const goalProgressBlock = document.getElementById("goal-progress-block");
const goalProgressFill = document.getElementById("goal-progress-fill");
const goalProgressPercent = document.getElementById("goal-progress-percent");
const goalProgressCaption = document.getElementById("goal-progress-caption");

const forecastCard = document.getElementById("forecast-card");
const forecastConfidence = document.getElementById("forecast-confidence");
const forecastHeadline = document.getElementById("forecast-headline");
const forecastGrid = document.getElementById("forecast-grid");
const forecastProjected = document.getElementById("forecast-projected");
const forecastEtaBlock = document.getElementById("forecast-eta-block");
const forecastEta = document.getElementById("forecast-eta");
const forecastCaption = document.getElementById("forecast-caption");

const scoreValueEl = document.getElementById("score-value");
const scoreRingFill = document.getElementById("score-ring-fill");
const scoreBreakdown = document.getElementById("score-breakdown");
const SCORE_RING_CIRCUMFERENCE = 326.7;

const historyBody = document.getElementById("history-body");
const trendCount = document.getElementById("trend-count");
const trendEmpty = document.getElementById("trend-empty");
const communityStrip = document.getElementById("community-strip");

const statIdealWeight = document.getElementById("stat-ideal-weight");
const statBmr = document.getElementById("stat-bmr");
const statCalories = document.getElementById("stat-calories");
const statBodyfat = document.getElementById("stat-bodyfat");
const statWater = document.getElementById("stat-water");

let trendChart = null;
let lastResult = null;
let lastHistory = [];
let currentMetric = "bmi";

/* ================= Dark mode ================= */
const themeToggle = document.getElementById("theme-toggle");
const savedTheme = localStorage.getItem("vitals-theme");
if (savedTheme === "dark") document.documentElement.setAttribute("data-theme", "dark");

themeToggle.addEventListener("click", function () {
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  if (isDark) {
    document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("vitals-theme", "light");
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    localStorage.setItem("vitals-theme", "dark");
  }
  refreshChartColor();
});

/* ================= Unit toggle ================= */
const unitButtons = document.querySelectorAll(".unit-btn");
const metricFields = document.getElementById("metric-fields");
const imperialFields = document.getElementById("imperial-fields");
let currentUnit = "metric";

unitButtons.forEach(function (btn) {
  btn.addEventListener("click", function () {
    unitButtons.forEach(function (b) { b.classList.remove("is-active"); });
    btn.classList.add("is-active");
    currentUnit = btn.dataset.unit;
    metricFields.style.display = currentUnit === "metric" ? "flex" : "none";
    imperialFields.style.display = currentUnit === "imperial" ? "flex" : "none";
  });
});

/* ================= Advanced + goal fields toggle ================= */
const advancedToggle = document.getElementById("advanced-toggle");
const advancedFields = document.getElementById("advanced-fields");
const goalFields = document.getElementById("goal-fields");
let advancedOpen = false;

advancedToggle.addEventListener("click", function () {
  advancedOpen = !advancedOpen;
  const display = advancedOpen ? "flex" : "none";
  advancedFields.style.display = display;
  goalFields.style.display = display;
  advancedToggle.textContent = advancedOpen
    ? "- Hide age, activity & goal fields"
    : "+ Add age & activity for BMR, calories, and goal tracking (optional)";
});

/* ================= Community stats ================= */
function loadCommunityStats() {
  fetch("/api/community-stats")
    .then(function (res) { return res.json(); })
    .then(function (data) {
      if (data.total_entries > 0) {
        communityStrip.textContent = data.total_entries + " entries logged by " +
          data.distinct_users + " people · community average BMI " + data.average_bmi;
      }
    })
    .catch(function () { /* silent - non-critical */ });
}
loadCommunityStats();

/* ================= Returning user recognition ================= */
let knownUsers = [];

function loadKnownUsers() {
  fetch("/api/users")
    .then(function (res) { return res.json(); })
    .then(function (data) {
      knownUsers = data.users || [];
      knownUsersList.innerHTML = knownUsers.map(function (u) {
        return '<option value="' + u + '">';
      }).join("");
    })
    .catch(function () { /* silent */ });
}
loadKnownUsers();

let greetingTimeout = null;
usernameInput.addEventListener("input", function () {
  clearTimeout(greetingTimeout);
  greetingTimeout = setTimeout(function () {
    const name = usernameInput.value.trim();
    if (!name) { greeting.style.display = "none"; return; }
    const match = knownUsers.find(function (u) { return u.toLowerCase() === name.toLowerCase(); });
    if (match) {
      fetch("/api/history/" + encodeURIComponent(match))
        .then(function (res) { return res.json(); })
        .then(function (data) {
          const count = (data.history || []).length;
          if (count > 0) {
            greeting.textContent = "Welcome back, " + match + " - you've logged " + count +
              " entr" + (count === 1 ? "y" : "ies") + " so far.";
            greeting.style.display = "block";
            lastHistory = data.history;
            renderHistory(data.history);
            renderTrend(data.history);
            downloadPdfBtn.style.display = "inline-block";
            downloadCsvBtn.style.display = "inline-block";
            downloadPdfBtn.dataset.username = match;
            downloadCsvBtn.dataset.username = match;
          }
        })
        .catch(function () { /* ignore */ });
    } else {
      greeting.style.display = "none";
    }
  }, 400);
});

/* ================= Gauge helpers ================= */
function bmiToAngle(bmi) {
  const min = 12, max = 42;
  const clamped = Math.max(min, Math.min(max, bmi));
  const ratio = (clamped - min) / (max - min);
  return -90 + ratio * 180;
}

/* Ties the app's accent color to the user's actual BMI category, so the
   reading panel, insight card and gauge respond visually to the result
   instead of staying a fixed brand color regardless of outcome. */
const CATEGORY_ACCENTS = {
  "Underweight": { accent: "--zone-under", soft: "--zone-under-soft" },
  "Normal": { accent: "--zone-normal", soft: "--zone-normal-soft" },
  "Overweight": { accent: "--zone-over", soft: "--zone-over-soft" },
  "Obese": { accent: "--zone-obese", soft: "--zone-obese-soft" },
};

function applyCategoryAccent(category) {
  const mapping = CATEGORY_ACCENTS[category];
  if (!mapping) return;
  const root = document.documentElement;
  const styles = getComputedStyle(root);
  root.style.setProperty("--accent", styles.getPropertyValue(mapping.accent).trim());
  root.style.setProperty("--accent-soft", styles.getPropertyValue(mapping.soft).trim());
}

function animateNumber(el, target, decimals) {
  const start = 0;
  const duration = 600;
  const startTime = performance.now();
  function tick(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = start + (target - start) * eased;
    el.textContent = value.toFixed(decimals);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

/* ================= Form submit ================= */
form.addEventListener("submit", function (e) {
  e.preventDefault();
  formError.textContent = "";
  calcBtn.disabled = true;
  calcBtn.querySelector("span").textContent = "Calculating...";

  const username = usernameInput.value.trim();

  let weightKg, heightM;
  if (currentUnit === "metric") {
    weightKg = parseFloat(document.getElementById("weight").value);
    heightM = parseFloat(document.getElementById("height").value);
  } else {
    const lb = parseFloat(document.getElementById("weight-lb").value);
    const ft = parseFloat(document.getElementById("height-ft").value) || 0;
    const inch = parseFloat(document.getElementById("height-in").value) || 0;
    weightKg = lb * 0.453592;
    heightM = ((ft * 12) + inch) * 0.0254;
  }

  const age = document.getElementById("age").value;
  const gender = document.getElementById("gender").value;
  const activityLevel = document.getElementById("activity_level").value;
  const goalWeightInput = document.getElementById("goal-weight").value;

  const body = { username: username, weight: weightKg, height: heightM };
  if (age && gender) {
    body.age = age;
    body.gender = gender;
    body.activity_level = activityLevel;
  }

  fetch("/api/calculate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  })
    .then(function (res) {
      return res.json().then(function (data) { return { ok: res.ok, data: data }; });
    })
    .then(function (result) {
      if (!result.ok) {
        formError.textContent = result.data.error || "Something went wrong. Please try again.";
        showToast(result.data.error || "Something went wrong.", "error");
        return;
      }

      lastResult = Object.assign({}, result.data, { username: username });

      // If a goal weight was entered this time, save/update it, then re-render with fresh progress
      if (goalWeightInput) {
        fetch("/api/goal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: username, goal_weight: goalWeightInput })
        })
          .then(function (res) { return res.json(); })
          .then(function (goalData) {
            lastResult.goal_progress = goalData.progress;
            renderResult(lastResult);
          })
          .catch(function () { renderResult(lastResult); });
      } else {
        renderResult(lastResult);
      }

      loadKnownUsers();
      loadCommunityStats();
      showToast("Saved — BMI " + result.data.bmi.toFixed(1) + " logged.", "success");
    })
    .catch(function () {
      formError.textContent = "Could not reach the server. Check your connection and try again.";
      showToast("Could not reach the server.", "error");
    })
    .finally(function () {
      calcBtn.disabled = false;
      calcBtn.querySelector("span").textContent = "Calculate";
    });
});

function renderResult(data) {
  animateNumber(bmiValueEl, data.bmi, 1);
  const angle = bmiToAngle(data.bmi);
  needle.style.transform = "rotate(" + angle + "deg)";
  applyCategoryAccent(data.category);

  if (data.ideal_weight) {
    statIdealWeight.textContent = data.ideal_weight.min + "-" + data.ideal_weight.max + " kg";
  }
  statBmr.textContent = data.bmr ? Math.round(data.bmr) + " kcal/day" : "Add age & gender";
  statCalories.textContent = data.daily_calories ? Math.round(data.daily_calories) + " kcal/day" : "Add age & gender";
  statBodyfat.textContent = data.body_fat ? data.body_fat + "%" : "Add age & gender";
  statWater.textContent = data.water_intake ? data.water_intake + " L/day" : "-";

  if (data.category_info) {
    bmiCategoryEl.textContent = data.category_info.emoji + "  " + data.category;
  } else {
    bmiCategoryEl.textContent = data.category;
  }

  if (data.warning) {
    insightText.textContent = data.warning;
  } else if (data.ai_insight) {
    insightText.textContent = data.ai_insight.message;
  }
  renderForecast(data.forecast);
  renderHealthScore(data.health_score);
  copyBtn.style.display = "inline-block";
  if (navigator.share) shareBtn.style.display = "inline-block";
  clearBtn.style.display = "inline-block";
  downloadPdfBtn.style.display = "inline-block";
  downloadCsvBtn.style.display = "inline-block";
  downloadPdfBtn.dataset.username = data.username;
  downloadCsvBtn.dataset.username = data.username;

  // Streak
  if (data.streak && data.streak > 0) {
    streakBadge.textContent = "\uD83D\uDD25 " + data.streak + "-day streak";
    streakRow.style.display = "flex";
  }

  // Achievements
  if (data.achievements && data.achievements.length) {
    achievementsRow.innerHTML = data.achievements.map(function (a) {
      return '<span class="achievement-chip">' + a.emoji + " " + a.label + "</span>";
    }).join("");
  }

  // Goal progress
  if (data.goal_progress) {
    const gp = data.goal_progress;
    goalProgressBlock.style.display = "block";
    goalProgressPercent.textContent = gp.percent + "%";
    goalProgressFill.style.width = gp.percent + "%";
    goalProgressCaption.textContent = gp.start_weight + " kg \u2192 " + gp.current_weight +
      " kg \u2192 goal " + gp.goal_weight + " kg";
  }

  if (data.history && data.history.length) {
    lastHistory = data.history;
    renderHistory(data.history);
    renderTrend(data.history);
  }
}

/* ================= Health Score (transparent, deterministic) ================= */
function renderHealthScore(healthScore) {
  if (!healthScore) return;

  scoreValueEl.textContent = healthScore.score;
  const offset = SCORE_RING_CIRCUMFERENCE * (1 - healthScore.score / 100);
  scoreRingFill.style.strokeDashoffset = offset;

  scoreBreakdown.innerHTML = "";
  healthScore.components.forEach(function (c) {
    const row = document.createElement("div");
    row.className = "score-row";

    const label = document.createElement("span");
    label.className = "score-row__label";
    label.textContent = c.label;

    const barWrap = document.createElement("span");
    barWrap.className = "score-row__bar";
    const barFill = document.createElement("span");
    barFill.className = "score-row__bar-fill";
    barFill.style.width = Math.max(0, Math.min(100, (c.score / c.max) * 100)) + "%";
    barWrap.appendChild(barFill);

    const points = document.createElement("span");
    points.className = "score-row__points";
    points.textContent = c.score + "/" + c.max;

    row.appendChild(label);
    row.appendChild(barWrap);
    row.appendChild(points);
    scoreBreakdown.appendChild(row);
  });
}

/* ================= Predictive forecast (USP) ================= */
function renderForecast(forecast) {
  if (!forecast || !forecast.available) {
    forecastCard.classList.add("forecast-card--locked");
    forecastConfidence.textContent = "Locked";
    forecastHeadline.textContent = (forecast && forecast.reason) ||
      "Log one more entry on a different day to unlock your personalized BMI trend forecast.";
    forecastGrid.style.display = "none";
    forecastCaption.textContent = "Once unlocked, Vitals+ models your trend with regression " +
      "on your own logged history to project where things are headed.";
    return;
  }

  forecastCard.classList.remove("forecast-card--locked");
  forecastConfidence.textContent = forecast.confidence === "higher"
    ? "High confidence"
    : "Preliminary";

  const directionWord = forecast.trend_direction === "rising" ? "rising"
    : forecast.trend_direction === "falling" ? "falling" : "holding steady";
  const weeklyChange = Math.abs(forecast.bmi_change_per_week).toFixed(2);

  if (forecast.trend_direction === "stable") {
    forecastHeadline.textContent = "Your BMI has been holding steady across your logged entries.";
  } else {
    forecastHeadline.textContent = "Your BMI is " + directionWord + " by about " + weeklyChange +
      " points/week based on your own history.";
  }

  forecastGrid.style.display = "grid";
  forecastProjected.textContent = forecast.projected_bmi.toFixed(1) + " in " + forecast.projected_days + "d";

  if (forecast.goal_eta_days !== undefined) {
    if (forecast.goal_eta_days === null) {
      forecastEtaBlock.style.display = "flex";
      forecastEta.textContent = "Trend moving away from goal";
    } else {
      forecastEtaBlock.style.display = "flex";
      forecastEta.textContent = "~" + forecast.goal_eta_days + " days";
    }
  } else {
    forecastEtaBlock.style.display = "none";
  }

  forecastCaption.textContent = "Modelled with linear regression on your own logged entries — " +
    "a preview of where this trend leads if nothing changes, not a prediction of what will happen.";
}

/* ================= Copy / Share summary ================= */
function buildSummary() {
  if (!lastResult) return "";
  const lines = [];
  lines.push(lastResult.username + "'s Vitals Summary");
  lines.push("BMI: " + lastResult.bmi.toFixed(1) + " (" + lastResult.category + ")");
  lines.push("Healthy weight range: " + lastResult.ideal_weight.min + "-" + lastResult.ideal_weight.max + " kg");
  if (lastResult.bmr) lines.push("BMR: " + Math.round(lastResult.bmr) + " kcal/day");
  if (lastResult.daily_calories) lines.push("Estimated daily calories: " + Math.round(lastResult.daily_calories) + " kcal/day");
  if (lastResult.body_fat) lines.push("Estimated body fat: " + lastResult.body_fat + "%");
  if (lastResult.water_intake) lines.push("Recommended water intake: " + lastResult.water_intake + " L/day");
  if (lastResult.health_score) lines.push("Health Score: " + lastResult.health_score.score + "/100");
  if (lastResult.streak) lines.push("Current streak: " + lastResult.streak + " day(s)");
  if (lastResult.forecast && lastResult.forecast.available) {
    lines.push("Forecasted BMI in " + lastResult.forecast.projected_days + " days: " +
      lastResult.forecast.projected_bmi.toFixed(1) + " (" + lastResult.forecast.trend_direction + " trend)");
  }
  if (lastResult.ai_insight && lastResult.ai_insight.available) {
    lines.push("");
    lines.push("Note: " + lastResult.ai_insight.message);
  }
  return lines.join("\n");
}

copyBtn.addEventListener("click", function () {
  navigator.clipboard.writeText(buildSummary())
    .then(function () {
      copyBtn.textContent = "Copied";
      copyBtn.classList.add("copied");
      showToast("Summary copied to clipboard.", "success");
      setTimeout(function () {
        copyBtn.textContent = "Copy summary";
        copyBtn.classList.remove("copied");
      }, 1800);
    })
    .catch(function () {
      showToast("Could not copy to clipboard.", "error");
    });
});

shareBtn.addEventListener("click", function () {
  if (navigator.share) {
    navigator.share({ title: "My Vitals Summary", text: buildSummary() }).catch(function () { /* cancelled */ });
  }
});

/* ================= Clear history ================= */
clearBtn.addEventListener("click", function () {
  if (!lastResult || !lastResult.username) return;
  showConfirmModal(
    'Delete all saved entries for "' + lastResult.username + '"? This cannot be undone.',
    function () {
      fetch("/api/history/" + encodeURIComponent(lastResult.username), { method: "DELETE" })
        .then(function () {
          historyBody.innerHTML = '<tr><td colspan="5" class="empty-note">No entries logged yet.</td></tr>';
          trendEmpty.style.display = "block";
          trendCount.textContent = "";
          lastHistory = [];
          if (trendChart) {
            trendChart.data.labels = [];
            trendChart.data.datasets[0].data = [];
            trendChart.update();
          }
          loadKnownUsers();
          loadCommunityStats();
          showToast("History cleared.", "success");
        })
        .catch(function () {
          showToast("Could not clear history right now.", "error");
        });
    }
  );
});

/* ================= PDF / CSV downloads ================= */
function triggerDownload(url, filename) {
  fetch(url)
    .then(function (res) {
      if (!res.ok) throw new Error("Download failed");
      return res.blob();
    })
    .then(function (blob) {
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
    })
    .catch(function () {
      showToast("Could not generate the download. Please try again.", "error");
    });
}

downloadPdfBtn.addEventListener("click", function () {
  const uname = downloadPdfBtn.dataset.username;
  if (!uname) return;
  triggerDownload("/api/report/" + encodeURIComponent(uname), uname + "_vitals_report.pdf");
});

downloadCsvBtn.addEventListener("click", function () {
  const uname = downloadCsvBtn.dataset.username;
  if (!uname) return;
  triggerDownload("/api/export/" + encodeURIComponent(uname), uname + "_vitals_history.csv");
});

/* ================= History + trend rendering ================= */
function renderHistory(history) {
  historyBody.innerHTML = "";
  const reversed = history.slice().reverse();
  reversed.forEach(function (record) {
    const tr = document.createElement("tr");
    tr.innerHTML =
      "<td>" + formatDate(record.created_at) + "</td>" +
      "<td>" + record.weight_kg + " kg</td>" +
      "<td>" + record.height_m + " m</td>" +
      "<td>" + Number(record.bmi).toFixed(1) + "</td>" +
      "<td>" + record.category + "</td>";
    historyBody.appendChild(tr);
  });
}

function formatDate(raw) {
  const d = new Date(raw);
  if (isNaN(d)) return raw;
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "short", year: "numeric" });
}

/* ---------- Multi-metric chart toggle ---------- */
const metricButtons = document.querySelectorAll(".metric-btn");
const metricLabels = { bmi: "BMI", weight_kg: "Weight (kg)", daily_calories: "Calories (kcal)" };

metricButtons.forEach(function (btn) {
  btn.addEventListener("click", function () {
    metricButtons.forEach(function (b) { b.classList.remove("is-active"); });
    btn.classList.add("is-active");
    currentMetric = btn.dataset.metric;
    if (lastHistory.length) renderTrend(lastHistory);
  });
});

function refreshChartColor() {
  if (!trendChart) return;
  const accentColor = getComputedStyle(document.documentElement).getPropertyValue("--vital").trim();
  trendChart.data.datasets[0].borderColor = accentColor;
  trendChart.data.datasets[0].pointBackgroundColor = accentColor;
  trendChart.update();
}

function renderTrend(history) {
  trendEmpty.style.display = history.length < 2 ? "block" : "none";
  trendCount.textContent = history.length + " entr" + (history.length === 1 ? "y" : "ies");

  const ctx = document.getElementById("trend-chart").getContext("2d");
  const labels = history.map(function (r) { return formatDate(r.created_at); });
  const values = history.map(function (r) {
    const v = r[currentMetric];
    return (v === null || v === undefined) ? null : Number(v);
  });

  const accentColor = getComputedStyle(document.documentElement).getPropertyValue("--vital").trim() || "#0F6E63";

  if (trendChart) {
    trendChart.data.labels = labels;
    trendChart.data.datasets[0].data = values;
    trendChart.data.datasets[0].label = metricLabels[currentMetric];
    trendChart.update();
    return;
  }

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: metricLabels[currentMetric],
        data: values,
        borderColor: accentColor,
        backgroundColor: "rgba(15, 110, 99, 0.08)",
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: accentColor,
        tension: 0.3,
        fill: true,
        spanGaps: true
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: "rgba(150,150,150,0.15)" } },
        x: { grid: { display: false } }
      }
    }
  });
}
