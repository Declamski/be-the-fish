import os


def load_config():
    port = int(os.environ.get("PORT", 8000))
    data_dir = os.environ.get("DATA_DIR", "./data")
    secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    # Where the sites service is, and how long to wait for it before giving up.
    sites_url = os.environ.get("SITES_URL", "http://localhost:8001")
    sites_timeout_s = float(os.environ.get("SITES_TIMEOUT_S", 2))
    return {
        "PORT": port,
        "DATA_DIR": data_dir,
        "SECRET_KEY": secret_key,
        "SITES_URL": sites_url,
        "SITES_TIMEOUT_S": sites_timeout_s,
    }
