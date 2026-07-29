/**
 * script.js
 * Wires up the BMI form, animates the gauge needle, renders the history
 * table, draws the Chart.js trend line, and displays the AI insight.
 */

const form = document.getElementById("bmi-form");
const calcBtn = document.getElementById("calc-btn");
const formError = document.getElementById("form-error");

const bmiValueEl = document.getElementById("bmi-value");
const bmiCategoryEl = document.getElementById("bmi-category");
const needle = document.getElementById("needle");

const insightText = document.getElementById("insight-text");
const historyBody = document.getElementById("history-body");
const trendCount = document.getElementById("trend-count");
const trendEmpty = document.getElementById("trend-empty");

let trendChart = null;

// Gauge sweeps from -90deg (far left, low BMI) to +90deg (far right, high BMI).
// We map a BMI range of 12 -> 42 across that 180 degree sweep, clamping at the ends.
function bmiToAngle(bmi) {
  const min = 12, max = 42;
  const clamped = Math.max(min, Math.min(max, bmi));
  const ratio = (clamped - min) / (max - min);
  return -90 + ratio * 180;
}

function categoryClass(category) {
  return {
    "Underweight": "under",
    "Normal": "normal",
    "Overweight": "over",
    "Obese": "obese"
  }[category] || "normal";
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  formError.textContent = "";
  calcBtn.disabled = true;
  calcBtn.querySelector("span").textContent = "Calculating…";

  const username = document.getElementById("username").value.trim();
  const weight = document.getElementById("weight").value;
  const height = document.getElementById("height").value;

  try {
    const res = await fetch("/api/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, weight, height })
    });
    const data = await res.json();

    if (!res.ok) {
      formError.textContent = data.error || "Something went wrong. Please try again.";
      return;
    }

    renderResult(data);
  } catch (err) {
    formError.textContent = "Could not reach the server. Check your connection and try again.";
  } finally {
    calcBtn.disabled = false;
    calcBtn.querySelector("span").textContent = "Calculate";
  }
});

function renderResult(data) {
  // Gauge
  bmiValueEl.textContent = data.bmi.toFixed(1);
  bmiCategoryEl.textContent = data.category;
  const angle = bmiToAngle(data.bmi);
  needle.style.transform = `rotate(${angle}deg)`;

  // Insight card
  if (data.warning) {
    insightText.textContent = data.warning;
  } else if (data.ai_insight) {
    insightText.textContent = data.ai_insight.message;
  }

  // History + trend
  if (data.history && data.history.length) {
    renderHistory(data.history);
    renderTrend(data.history);
  }
}

function renderHistory(history) {
  historyBody.innerHTML = "";
  // Show most recent first in the table
  [...history].reverse().forEach(record => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${formatDate(record.created_at)}</td>
      <td>${record.weight_kg} kg</td>
      <td>${record.height_m} m</td>
      <td>${Number(record.bmi).toFixed(1)}</td>
      <td>${record.category}</td>
    `;
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
  trendCount.textContent = `${history.length} entr${history.length === 1 ? "y" : "ies"}`;

  const ctx = document.getElementById("trend-chart").getContext("2d");
  const labels = history.map(r => formatDate(r.created_at));
  const values = history.map(r => Number(r.bmi));

  if (trendChart) {
    trendChart.data.labels = labels;
    trendChart.data.datasets[0].data = values;
    trendChart.update();
    return;
  }

  trendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "BMI",
        data: values,
        borderColor: "#0F6E63",
        backgroundColor: "rgba(15, 110, 99, 0.08)",
        borderWidth: 2,
        pointRadius: 3,
        pointBackgroundColor: "#0F6E63",
        tension: 0.3,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { grid: { color: "#EDEBE3" } },
        x: { grid: { display: false } }
      }
    }
  });
}
