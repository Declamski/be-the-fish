import sqlite3
import os

import users
import dives


def get_connection(data_dir):
    db_path = os.path.join(data_dir, "divelog.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(data_dir):
    os.makedirs(data_dir, exist_ok=True)
    conn = get_connection(data_dir)
    users.init_db(conn)
    dives.init_db(conn)
    conn.close()
