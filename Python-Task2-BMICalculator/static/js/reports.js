/* static/js/reports.js */

(function () {
  var generateBtn = document.getElementById("generate-report-btn");
  var csvBtn = document.getElementById("export-csv-report-btn");
  var statusEl = document.getElementById("report-status");

  generateBtn.addEventListener("click", function () {
    generateBtn.disabled = true;
    generateBtn.textContent = "Generating...";
    statusEl.textContent = "";

    fetch("/api/report")
      .then(function (response) {
        if (!response.ok) {
          return response.json().then(function (data) {
            throw new Error((data && data.error) || "Could not generate report.");
          });
        }
        return response.blob();
      })
      .then(function (blob) {
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement("a");
        a.href = url;
        a.download = "vitals_report.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        showToast("Report downloaded.", "success");
      })
      .catch(function (err) {
        statusEl.textContent = err.message;
        showToast(err.message, "error");
      })
      .finally(function () {
        generateBtn.disabled = false;
        generateBtn.textContent = "Generate Health Report";
      });
  });

  csvBtn.addEventListener("click", function () {
    window.location.href = "/api/export";
  });
})();
