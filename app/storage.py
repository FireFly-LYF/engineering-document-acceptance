"""Local schema initialization. No credentials or document blobs stored in the DB."""
import sqlite3
from pathlib import Path
from app.registry import ROOT, Registry


def open_database(path):
    if str(path).startswith('mysql://'):
        from app.mysql_storage import MySQLConnection
        conn = MySQLConnection(str(path))
        Registry().install(conn)
        return conn
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=5000')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.executescript((ROOT / 'database/schema.sqlite.sql').read_text(encoding='utf-8'))
    Registry().install(conn)
    return conn
