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
});
