document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".nav-link");
    const pageTitle = document.getElementById("page-title");

    navLinks.forEach((link) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            navLinks.forEach((l) => l.classList.remove("active"));
            link.classList.add("active");

            const page = link.dataset.page;
            pageTitle.textContent = link.textContent;

            // TODO: render each page
            console.log("Navegar para:", page);
        });
    });

    loadDashboard();
});

async function loadDashboard() {
    // TODO: fetch stats from API and populate cards
    console.log("Dashboard carregado");
}
