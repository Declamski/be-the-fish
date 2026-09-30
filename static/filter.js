// Filter-as-you-type. Any <input data-filter="CSS selector"> hides the
// elements matching that selector whose text does not contain what was typed.
document.querySelectorAll("input[data-filter]").forEach(function (input) {
    const items = document.querySelectorAll(input.dataset.filter);

    input.addEventListener("input", function () {
        const query = input.value.trim().toLowerCase();
        items.forEach(function (item) {
            const text = item.textContent.toLowerCase();
            item.hidden = !text.includes(query);
        });
    });
});

// Searchable dropdown. Any <input data-filter-select="#select-id"> narrows that
// <select> to the options containing what was typed. Safari ignores `hidden` on
// <option>, so the options are taken out and put back instead of hidden.
document.querySelectorAll("input[data-filter-select]").forEach(function (input) {
    const select = document.querySelector(input.dataset.filterSelect);
    const allOptions = Array.from(select.options);

    input.addEventListener("input", function () {
        const query = input.value.trim().toLowerCase();
        const chosen = select.value;

        select.innerHTML = "";
        allOptions.forEach(function (option) {
            const text = option.textContent.toLowerCase();
            // Always keep "No site" and whatever is currently chosen.
            if (option.value === "" || option.value === chosen || text.includes(query)) {
                select.appendChild(option);
            }
        });
        select.value = chosen;
    });

    // Enter in the search box should not submit the dive form.
    input.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
        }
    });
});
