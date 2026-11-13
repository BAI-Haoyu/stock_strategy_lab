"""Session-scoped SQLite experiment records, using parameterized SQL."""
import json
from pathlib import Path
import sqlite3
from datetime import datetime, timezone


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute("""CREATE TABLE IF NOT EXISTS experiments
        (id INTEGER PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
         created TEXT NOT NULL, config TEXT NOT NULL, summary TEXT NOT NULL)""")
    return connection


def save_experiment(path, owner, name, config, summary):
    name = name.strip()
    if not name or len(name) > 80:
        raise ValueError("Use an experiment name between 1 and 80 characters.")
    with connect(path) as con:
        cursor = con.execute("INSERT INTO experiments(owner,name,created,config,summary) VALUES(?,?,?,?,?)",
                             (owner, name, datetime.now(timezone.utc).isoformat(timespec="seconds"),
                              json.dumps(config, allow_nan=False), json.dumps(summary, allow_nan=False)))
        return cursor.lastrowid


def list_experiments(path, owner):
    with connect(path) as con:
        rows = con.execute("SELECT id,name,created FROM experiments WHERE owner=? ORDER BY id DESC", (owner,)).fetchall()
    return [{"id": r[0], "name": r[1], "created": r[2]} for r in rows]


def load_experiment(path, owner, identifier):
    with connect(path) as con:
        row = con.execute("SELECT config,summary FROM experiments WHERE owner=? AND id=?", (owner, identifier)).fetchone()
    if row is None:
        raise ValueError("Experiment not found in this session.")
    return {"config": json.loads(row[0]), "summary": json.loads(row[1])}
