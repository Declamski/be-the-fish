import sqlite3
import os

import sites


def get_connection(data_dir):
    db_path = os.path.join(data_dir, "sites.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    conn = get_connection(data_dir)
    sites.init_db(conn)
    sites.seed_sites(conn)
    conn.close()
