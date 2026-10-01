// Any element with data-load-url="/some/url" is filled with the HTML that URL
// returns. The dive page uses it to show the feed domain's kudos and comments
// without the dives domain having to import the feed domain.
document.querySelectorAll("[data-load-url]").forEach(function (element) {
    fetch(element.dataset.loadUrl)
        .then(function (response) {
            return response.text();
        })
        .then(function (html) {
            element.innerHTML = html;
        });
});
