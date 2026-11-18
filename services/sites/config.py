import os


def load_config():
    port = int(os.environ.get("PORT", 8000))
    # Secret, so no default: e.g. mssql://sites_user:<password>@localhost:1433/sites
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set (mssql://user:password@host:port/database)")
    return {"PORT": port, "DATABASE_URL": database_url}
