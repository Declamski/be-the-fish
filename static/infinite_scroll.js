// Infinite scroll for the feed. When there are more dives, the last item of
// #feed-list is a "sentinel" <li data-next-url="/feed/more?offset=20">.
// When the sentinel scrolls into view we fetch the next page and put it in its
// place. The new page ends with a new sentinel if there is still more.
const feedList = document.querySelector("#feed-list");

const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
        if (entry.isIntersecting) {
            loadNextPage(entry.target);
        }
    });
});

function loadNextPage(sentinel) {
    observer.unobserve(sentinel);
    fetch(sentinel.dataset.nextUrl)
        .then(function (response) {
            return response.text();
        })
        .then(function (html) {
            sentinel.remove();
            feedList.insertAdjacentHTML("beforeend", html);
            watchSentinel();
        });
}

function watchSentinel() {
    const sentinel = feedList.querySelector("[data-next-url]");
    if (sentinel) {
        observer.observe(sentinel);
    }
}

watchSentinel();
