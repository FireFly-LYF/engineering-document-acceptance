"""Validate catalog and create a fresh local database with actual FK checks."""
import argparse
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.registry import Registry
from app.storage import open_database

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='tmp/architecture.sqlite')
    args = parser.parse_args()
    registry = Registry()
    conn = open_database(args.db)
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    if conn.execute('PRAGMA foreign_key_check').fetchall():
        raise SystemExit('foreign_key_check failed')
    print(f'Validated: tags={len(registry.tags)}, labels={len(registry.labels)}, rules={len(registry.rules["rules"])}, tables={len(tables)}')
    print('Registry fingerprint:', registry.sha256[:16])
    conn.close()
