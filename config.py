import os


def load_config():
    port = int(os.environ.get("PORT", 8000))
    data_dir = os.environ.get("DATA_DIR", "./data")
    secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    return {"PORT": port, "DATA_DIR": data_dir, "SECRET_KEY": secret_key}
