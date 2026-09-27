import os


def load_config():
    port = int(os.environ.get("PORT", 8000))
    data_dir = os.environ.get("DATA_DIR", "./data")
    return {"PORT": port, "DATA_DIR": data_dir}
