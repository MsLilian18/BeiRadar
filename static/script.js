document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.querySelector('input[name="search"]');
    const suggestionsBox = document.createElement("ul");
    suggestionsBox.classList.add("suggestions");
    searchInput.parentNode.appendChild(suggestionsBox);

    // Example suggestions – replace or fetch dynamically from Flask
    const products = [
        "Milk",
        "Sugar",
        "Bread",
        "Chocolate",
        "Nutribullet Blender NBR1212R",
        "Moulinex Blender LM422",
        "Brookside Milk",
        "Naivas Fresh Eggs"
    ];

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLowerCase();
        suggestionsBox.innerHTML = "";
        if (!query) {
            suggestionsBox.style.display = "none";
            return;
        }

        const filtered = products.filter(item => item.toLowerCase().includes(query));
        if (filtered.length === 0) {
            suggestionsBox.style.display = "none";
            return;
        }

        filtered.forEach(item => {
            const li = document.createElement("li");
            const regex = new RegExp(`(${query})`, "gi");
            li.innerHTML = item.replace(regex, "<span class='match'>$1</span>");
            li.addEventListener("click", () => {
                searchInput.value = item;
                suggestionsBox.style.display = "none";
            });
            suggestionsBox.appendChild(li);
        });

        suggestionsBox.style.display = "block";
    });

    // Hide suggestions when clicking outside
    document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
            suggestionsBox.style.display = "none";
        }
    });
});
