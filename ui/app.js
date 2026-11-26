// Shared code for every page: calling the services, the login token, the nav bar,
// and turning stored values (seconds, ISO dates) into readable text.

// --- Login token -------------------------------------------------------------
// The dives service gives us a token when we log in. We keep it in the browser
// (localStorage) and send it with every request as "Authorization: Bearer <token>".

function getToken() {
    return localStorage.getItem("token");
}

function saveLogin(token, user) {
    localStorage.setItem("token", token);
    localStorage.setItem("userName", user.name);
}

function logOut() {
    localStorage.removeItem("token");
    localStorage.removeItem("userName");
    window.location.href = "login.html";
}

// For pages that need a logged-in user: go to the login page if there is no token.
function requireLogin() {
    if (!getToken()) {
        window.location.href = "login.html";
    }
}

// --- Calling the services ----------------------------------------------------

const STARTING_UP_MESSAGE =
    "The service isn't answering. It may be starting up (it sleeps when nobody uses it): try again in a moment.";

// Call one of the services and return the JSON answer.
// service: "dives" or "sites". body: an object (sent as JSON) or a FormData (file upload).
// Throws an Error with a message that can be shown to the user.
async function api(service, method, path, body) {
    let baseUrl = window.CONFIG.DIVES_URL;
    if (service === "sites") {
        baseUrl = window.CONFIG.SITES_URL;
    }

    const options = { method: method, headers: {} };
    if (getToken()) {
        options.headers["Authorization"] = "Bearer " + getToken();
    }
    if (body instanceof FormData) {
        options.body = body;  // the browser sets the multipart Content-Type itself
    } else if (body !== undefined) {
        options.headers["Content-Type"] = "application/json";
        options.body = JSON.stringify(body);
    }

    let response;
    try {
        response = await fetch(baseUrl + path, options);
    } catch (networkError) {
        // No answer at all: the service is down, or still waking up on Azure.
        throw new Error(STARTING_UP_MESSAGE);
    }

    // Azure answers 503 "App port is not ready" while a sleeping container starts.
    if (response.status === 503) {
        throw new Error(STARTING_UP_MESSAGE);
    }
    // The token is missing, wrong or too old: log in again.
    if (response.status === 401 && path !== "/api/login") {
        logOut();
        throw new Error("Please log in again.");
    }

    let data = null;
    try {
        data = await response.json();
    } catch (notJson) {
        data = null;
    }
    if (!response.ok) {
        let message = "Something went wrong (" + response.status + ").";
        if (data && data.error) {
            message = data.error;
        }
        throw new Error(message);
    }
    return data;
}

// --- Showing things on the page ----------------------------------------------

// Every value from the services goes through this before it is put into HTML,
// so a dive note like "<script>" is shown as text instead of being run.
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

// Put a message into the page's <p id="error"> (or clear it with "").
function showError(message) {
    const box = document.getElementById("error");
    box.textContent = message;
    box.hidden = !message;
}

// A value from the page's address, e.g. getParam("id") on dive.html?id=5 gives "5".
function getParam(name) {
    return new URLSearchParams(window.location.search).get(name);
}

// The nav bar at the top of every page.
function renderNav() {
    const header = document.getElementById("nav");
    let links = '<a href="login.html">Log in</a>';
    if (getToken()) {
        links = '<a href="feed.html">Feed</a>' +
            '<a href="dives.html">My dives</a>' +
            '<a href="new.html">Log a dive</a>' +
            '<a href="sites.html">Sites</a>' +
            '<a href="friends.html">Friends</a>' +
            '<button type="button" class="link-button" onclick="logOut()">Log out</button>';
    }
    header.innerHTML = '<nav class="nav"><a class="brand" href="index.html">Be the Fish</a>' +
        '<div class="nav-links">' + links + '</div></nav>';
}

// --- Readable values (same rules as formatting.py in Assignment 1) -----------

// 2700 -> "45 min", 80 -> "1 min 20 s", 45 -> "45 s", 3900 -> "1 h 5 min".
function formatDuration(seconds) {
    if (seconds === null || seconds === undefined) {
        return "-";
    }
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const rest = seconds % 60;
    if (hours > 0) {
        return hours + " h " + minutes + " min";
    }
    if (minutes > 0 && rest > 0) {
        return minutes + " min " + rest + " s";
    }
    if (minutes > 0) {
        return minutes + " min";
    }
    return rest + " s";
}

// "2026-09-01T10:00" -> "1 Sep 2026, 10:00". Anything unreadable is shown as it is.
function formatDateTime(text) {
    if (!text) {
        return "-";
    }
    const date = new Date(text);
    if (isNaN(date.getTime())) {
        return text;
    }
    const month = date.toLocaleString("en-GB", { month: "short" });
    const time = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    return date.getDate() + " " + month + " " + date.getFullYear() + ", " + time;
}

// (18, "m") -> "18 m", (17.73, "m") -> "17.7 m", (null, "m") -> "-".
function formatNumber(value, unit) {
    if (value === null || value === undefined) {
        return "-";
    }
    return Math.round(value * 10) / 10 + " " + unit;
}

// One "label: value" box inside a .stats row.
function stat(label, value) {
    return '<div><span class="stat-label">' + escapeHtml(label) +
        '</span><span class="stat-value">' + escapeHtml(value) + '</span></div>';
}

// --- Form helpers shared by new.html and dive.html ----------------------------

// Fill a <select> with plain values, e.g. ["poor", "good"], and pick `selected`.
// firstLabel adds an empty choice at the top, e.g. "Not recorded".
function fillSelect(select, values, selected, firstLabel) {
    let html = "";
    if (firstLabel) {
        html += '<option value="">' + escapeHtml(firstLabel) + '</option>';
    }
    for (const value of values) {
        const isSelected = value === selected ? " selected" : "";
        html += '<option value="' + escapeHtml(value) + '"' + isSelected + '>' + escapeHtml(value) + '</option>';
    }
    select.innerHTML = html;
}

// Fill the site <select> straight from the sites service (the UI calls both services).
// If sites can't answer, the dropdown only has "No site" and `note` explains why,
// so the dive can still be saved without a site.
async function fillSiteSelect(select, selectedId, note) {
    let html = '<option value="">No site</option>';
    try {
        const sites = await api("sites", "GET", "/api/sites?q=");
        for (const site of sites) {
            const isSelected = site.id === selectedId ? " selected" : "";
            html += '<option value="' + site.id + '"' + isSelected + '>' + escapeHtml(site.label) + '</option>';
        }
        note.textContent = "Missing a site? Contact the admin to have it added.";
    } catch (error) {
        note.textContent = "Dive sites are unavailable right now, so a site can't be chosen. You can still save without one.";
    }
    select.innerHTML = html;
}
