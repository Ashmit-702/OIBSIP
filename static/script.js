/**
 * script.js
 * Handles unit conversion, dark mode, returning-user recognition, the BMI form
 * submission, gauge animation, stat card rendering, Chart.js trend rendering,
 * copy/share summary, clear history, and print export.
 */

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
const printBtn = document.getElementById("print-btn");

const categoryCard = document.getElementById("category-card");
const categoryEmoji = document.getElementById("category-emoji");
const categoryBlurb = document.getElementById("category-blurb");

const historyBody = document.getElementById("history-body");
const trendCount = document.getElementById("trend-count");
const trendEmpty = document.getElementById("trend-empty");

const statIdealWeight = document.getElementById("stat-ideal-weight");
const statBmr = document.getElementById("stat-bmr");
const statCalories = document.getElementById("stat-calories");
const statBodyfat = document.getElementById("stat-bodyfat");
const statWater = document.getElementById("stat-water");

let trendChart = null;
let lastResult = null;

/* ---------- Dark mode ---------- */
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
  if (trendChart) {
    const accentColor = getComputedStyle(document.documentElement).getPropertyValue("--vital").trim();
    trendChart.data.datasets[0].borderColor = accentColor;
    trendChart.data.datasets[0].pointBackgroundColor = accentColor;
    trendChart.update();
  }
});

/* ---------- Unit toggle ---------- */
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

/* ---------- Advanced fields toggle ---------- */
const advancedToggle = document.getElementById("advanced-toggle");
const advancedFields = document.getElementById("advanced-fields");
let advancedOpen = false;

advancedToggle.addEventListener("click", function () {
  advancedOpen = !advancedOpen;
  advancedFields.style.display = advancedOpen ? "flex" : "none";
  advancedToggle.textContent = advancedOpen
    ? "- Hide age & activity fields"
    : "+ Add age & activity for BMR and calorie estimates (optional)";
});

/* ---------- Returning user recognition ---------- */
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
    .catch(function () { /* silent - nice to have only */ });
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
            renderHistory(data.history);
            renderTrend(data.history);
          }
        })
        .catch(function () { /* ignore */ });
    } else {
      greeting.style.display = "none";
    }
  }, 400);
});

/* ---------- Gauge helpers ---------- */
function bmiToAngle(bmi) {
  const min = 12, max = 42;
  const clamped = Math.max(min, Math.min(max, bmi));
  const ratio = (clamped - min) / (max - min);
  return -90 + ratio * 180;
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

/* ---------- Form submit ---------- */
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
        return;
      }
      lastResult = Object.assign({}, result.data, { username: username });
      renderResult(result.data);
      loadKnownUsers();
    })
    .catch(function () {
      formError.textContent = "Could not reach the server. Check your connection and try again.";
    })
    .finally(function () {
      calcBtn.disabled = false;
      calcBtn.querySelector("span").textContent = "Calculate";
    });
});

function renderResult(data) {
  animateNumber(bmiValueEl, data.bmi, 1);
  bmiCategoryEl.textContent = data.category;
  const angle = bmiToAngle(data.bmi);
  needle.style.transform = "rotate(" + angle + "deg)";

  if (data.ideal_weight) {
    statIdealWeight.textContent = data.ideal_weight.min + "-" + data.ideal_weight.max + " kg";
  }
  statBmr.textContent = data.bmr ? Math.round(data.bmr) + " kcal/day" : "Add age & gender";
  statCalories.textContent = data.daily_calories ? Math.round(data.daily_calories) + " kcal/day" : "Add age & gender";
  statBodyfat.textContent = data.body_fat ? data.body_fat + "%" : "Add age & gender";
  statWater.textContent = data.water_intake ? data.water_intake + " L/day" : "-";

  if (data.category_info) {
    categoryEmoji.textContent = data.category_info.emoji;
    categoryBlurb.textContent = data.category_info.blurb;
    categoryCard.style.display = "flex";
  }

  if (data.warning) {
    insightText.textContent = data.warning;
  } else if (data.ai_insight) {
    insightText.textContent = data.ai_insight.message;
  }
  copyBtn.style.display = "inline-block";
  if (navigator.share) shareBtn.style.display = "inline-block";
  clearBtn.style.display = "inline-block";

  if (data.history && data.history.length) {
    renderHistory(data.history);
    renderTrend(data.history);
  }
}

/* ---------- Copy / Share summary ---------- */
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
      setTimeout(function () {
        copyBtn.textContent = "Copy summary";
        copyBtn.classList.remove("copied");
      }, 1800);
    })
    .catch(function () {
      copyBtn.textContent = "Couldn't copy";
    });
});

shareBtn.addEventListener("click", function () {
  if (navigator.share) {
    navigator.share({ title: "My Vitals Summary", text: buildSummary() }).catch(function () { /* cancelled */ });
  }
});

/* ---------- Clear history ---------- */
clearBtn.addEventListener("click", function () {
  if (!lastResult || !lastResult.username) return;
  const confirmed = confirm('Delete all saved entries for "' + lastResult.username + '"? This cannot be undone.');
  if (!confirmed) return;

  fetch("/api/history/" + encodeURIComponent(lastResult.username), { method: "DELETE" })
    .then(function () {
      historyBody.innerHTML = '<tr><td colspan="5" class="empty-note">No entries logged yet.</td></tr>';
      trendEmpty.style.display = "block";
      trendCount.textContent = "";
      if (trendChart) {
        trendChart.data.labels = [];
        trendChart.data.datasets[0].data = [];
        trendChart.update();
      }
      loadKnownUsers();
    })
    .catch(function () {
      alert("Could not clear history right now. Please try again.");
    });
});

/* ---------- Print export ---------- */
printBtn.addEventListener("click", function () { window.print(); });

/* ---------- History + trend rendering ---------- */
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

function renderTrend(history) {
  trendEmpty.style.display = history.length < 2 ? "block" : "none";
  trendCount.textContent = history.length + " entr" + (history.length === 1 ? "y" : "ies");

  const ctx = document.getElementById("trend-chart").getContext("2d");
  const labels = history.map(function (r) { return formatDate(r.created_at); });
  const values = history.map(function (r) { return Number(r.bmi); });

  const accentColor = getComputedStyle(document.documentElement).getPropertyValue("--vital").trim() || "#0F6E63";

  if (trendChart) {
    trendChart.data.labels = labels;
    trendChart.data.datasets[0].data = values;
    trendChart.update();
    return;
  }

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "BMI",
        data: values,
        borderColor: accentColor,
        backgroundColor: "rgba(15, 110, 99, 0.08)",
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: accentColor,
        tension: 0.3,
        fill: true
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
