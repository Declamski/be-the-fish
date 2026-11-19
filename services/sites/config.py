import os


def load_config():
    port = int(os.environ.get("PORT", 8000))
    # The git commit the image was built from, shown by GET /health.
    version = os.environ.get("VERSION", "dev")
    # The address of the UI, the only website allowed to call this service (CORS).
    cors_origin = os.environ.get("CORS_ORIGIN", "http://localhost:8080")
    # Secret, so no default: e.g. mssql://sites_user:<password>@localhost:1433/sites
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set (mssql://user:password@host:port/database)")
    return {"PORT": port, "VERSION": version, "CORS_ORIGIN": cors_origin,
            "DATABASE_URL": database_url}
