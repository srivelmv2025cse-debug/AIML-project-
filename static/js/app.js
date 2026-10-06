document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("[data-menu-toggle]");
    const sidebar = document.querySelector("[data-sidebar]");

    if (toggle && sidebar) {
        toggle.addEventListener("click", () => {
            const isOpen = sidebar.classList.toggle("is-open");
            toggle.setAttribute("aria-expanded", String(isOpen));
        });

        document.querySelectorAll(".nav-link").forEach((link) => {
            link.addEventListener("click", () => {
                sidebar.classList.remove("is-open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    if (window.Chart && window.dashboardCharts) {
        const palette = ["#187f78", "#5f9eb7", "#e79252", "#8472b5", "#d45d5d", "#6a9f58"];
        const makeChart = (id, type, series, label) => {
            const canvas = document.getElementById(id);
            if (!canvas || !series) return;
            new Chart(canvas, { type, data: { labels: series.labels, datasets: [{ label, data: series.values, borderColor: palette[0], backgroundColor: type === "line" ? "rgba(24, 127, 120, .12)" : palette, borderWidth: 2, fill: type === "line", tension: .35, borderRadius: 4 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: "#edf1f1" } }, x: { grid: { display: false } } } } });
        };
        const dailyCanvas = document.getElementById("analyticsDailyChart");
        if (dailyCanvas && window.dashboardCharts.daily) {
            const anomalyDates = new Set((window.dashboardAnomalies || []).map((item) => item.date));
            const daily = window.dashboardCharts.daily;
            new Chart(dailyCanvas, { type: "line", data: { labels: daily.labels, datasets: [{ label: "Daily sales", data: daily.values, borderColor: palette[0], backgroundColor: "rgba(24, 127, 120, .12)", pointBackgroundColor: daily.labels.map((date) => anomalyDates.has(date) ? "#d45d5d" : palette[0]), pointRadius: daily.labels.map((date) => anomalyDates.has(date) ? 6 : 3), borderWidth: 2, fill: true, tension: .35 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, grid: { color: "#edf1f1" } }, x: { grid: { display: false } } } } });
        }
        makeChart("dailySalesChart", "line", window.dashboardCharts.daily, "Daily sales");
        makeChart("monthlySalesChart", "line", window.dashboardCharts.monthly, "Monthly sales");
        makeChart("categorySalesChart", "doughnut", window.dashboardCharts.category, "Category sales");
        makeChart("analyticsCategoryChart", "bar", window.dashboardCharts.category, "Category sales");
        makeChart("productSalesChart", "bar", window.dashboardCharts.product, "Product sales");
        makeChart("regionSalesChart", "bar", window.dashboardCharts.region, "Regional sales");
    }

    if (window.Chart && window.dashboardCustomerSegments) {
        new Chart(document.getElementById("dashboardCustomerSegmentsChart"), {
            type: "doughnut",
            data: {
                labels: window.dashboardCustomerSegments.map((segment) => segment.label),
                datasets: [{ data: window.dashboardCustomerSegments.map((segment) => segment.size), backgroundColor: ["#187f78", "#5f9eb7", "#e79252", "#8472b5", "#d45d5d"] }],
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
        });
    }

    if (window.Chart && window.customerAnalytics) {
        const segmentation = window.customerAnalytics.segmentation;
        if (segmentation.available) {
            const colors = ["#187f78", "#5f9eb7", "#e79252", "#8472b5", "#d45d5d"];
            new Chart(document.getElementById("customerSegmentSizesChart"), {
                type: "bar",
                data: {
                    labels: segmentation.cluster_sizes.map((segment) => segment.label),
                    datasets: [{ label: "Customers", data: segmentation.cluster_sizes.map((segment) => segment.size), backgroundColor: colors }],
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
            });
            const points = segmentation.scatter;
            const clusterNames = [...new Set(points.map((point) => point.cluster))];
            new Chart(document.getElementById("customerScatterChart"), {
                type: "scatter",
                data: { datasets: clusterNames.map((cluster, index) => ({
                    label: cluster,
                    data: points.filter((point) => point.cluster === cluster).map((point) => ({ x: point.x, y: point.y })),
                    backgroundColor: colors[index % colors.length],
                    pointRadius: 4,
                })) },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { tooltip: { callbacks: { label: (context) => `${context.dataset.label}: $${context.parsed.x.toFixed(2)} average order value, ${context.parsed.y} days recency` } } },
                    scales: { x: { title: { display: true, text: "Average order value ($)" }, beginAtZero: true }, y: { title: { display: true, text: "Recency (days)" }, beginAtZero: true } },
                },
            });
        }
    }

    if (window.Chart && window.forecastData && !window.forecastData.error) {
        const historical = window.forecastData.historical;
        const predicted = window.forecastData.forecast;
        const labels = historical.labels.concat(predicted.labels);
        const historicalValues = historical.values.concat(new Array(predicted.values.length).fill(null));
        const predictedValues = new Array(Math.max(historical.values.length - 1, 0)).fill(null).concat([historical.values[historical.values.length - 1]].concat(predicted.values));
        new Chart(document.getElementById("forecastChart"), { type: "line", data: { labels, datasets: [{ label: "Historical sales", data: historicalValues, borderColor: "#187f78", backgroundColor: "rgba(24, 127, 120, .1)", fill: true, tension: .3 }, { label: "Ensemble prediction", data: predictedValues, borderColor: "#e79252", borderDash: [6, 5], pointRadius: 3, tension: .3 }] }, options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false }, scales: { y: { beginAtZero: true, grid: { color: "#edf1f1" } }, x: { grid: { display: false } } } } });

        const availableModels = window.forecastData.models.filter((model) => model.available);
        const comparisonCanvas = document.getElementById("modelComparisonChart");
        if (comparisonCanvas) new Chart(comparisonCanvas, { type: "bar", data: { labels: availableModels.map((model) => model.name).concat("Ensemble"), datasets: [{ label: "MAE", data: availableModels.map((model) => model.metrics.mae).concat(window.forecastData.ensemble_metrics.mae), backgroundColor: "#187f78" }, { label: "RMSE", data: availableModels.map((model) => model.metrics.rmse).concat(window.forecastData.ensemble_metrics.rmse), backgroundColor: "#e79252" }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } }, scales: { y: { beginAtZero: true } } } });

        const scenarioCanvas = document.getElementById("scenarioChart");
        if (scenarioCanvas) {
            const scenarioColors = { "Best Case": "#187f78", "Expected Case": "#5f9eb7", "Worst Case": "#d45d5d" };
            new Chart(scenarioCanvas, { type: "line", data: { labels: window.forecastData.forecast.labels, datasets: Object.entries(window.forecastData.scenarios).map(([name, scenario]) => ({ label: `${name} (simulated)`, data: scenario.values, borderColor: scenarioColors[name], backgroundColor: "transparent", tension: .3 })) }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } }, scales: { y: { beginAtZero: true }, x: { grid: { display: false } } } } });
        }
    }
});
