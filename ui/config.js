// Where the two services are. These are the local addresses (docker compose).
// The CD workflow overwrites this file with the Azure addresses when it deploys.
window.CONFIG = {
    DIVES_URL: "http://localhost:8000",
    SITES_URL: "http://localhost:8001",
};
