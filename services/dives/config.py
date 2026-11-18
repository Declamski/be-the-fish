import os


def load_config():
    port = int(os.environ.get("PORT", 8000))
    # The git commit the image was built from, shown by GET /health.
    version = os.environ.get("VERSION", "dev")
    # Secret, so no default: e.g. mssql://dives_user:<password>@localhost:1433/dives
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set (mssql://user:password@host:port/database)")
    secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    # Where the sites service is, and how long to wait for it before giving up.
    sites_url = os.environ.get("SITES_URL", "http://localhost:8001")
    sites_timeout_s = float(os.environ.get("SITES_TIMEOUT_S", 2))
    return {
        "PORT": port,
        "VERSION": version,
        "DATABASE_URL": database_url,
        "SECRET_KEY": secret_key,
        "SITES_URL": sites_url,
        "SITES_TIMEOUT_S": sites_timeout_s,
    }
