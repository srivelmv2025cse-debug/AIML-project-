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
});
