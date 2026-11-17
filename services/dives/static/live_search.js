// Live search against the server. Any <input data-live-search="/some/url"
// data-results="#element"> asks that URL for results on every keystroke and
// puts the HTML it gets back into the results element.
document.querySelectorAll("input[data-live-search]").forEach(function (input) {
    const results = document.querySelector(input.dataset.results);

    input.addEventListener("input", function () {
        const url = input.dataset.liveSearch + "?q=" + encodeURIComponent(input.value);
        fetch(url)
            .then(function (response) {
                return response.text();
            })
            .then(function (html) {
                results.innerHTML = html;
            });
    });
});
