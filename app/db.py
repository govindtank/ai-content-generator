import sqlite3
from datetime import datetime
from flask import g

from app.config import Config


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(Config.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(Config.DATABASE_PATH)
    db.row_factory = sqlite3.Row
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            avatar_url TEXT NOT NULL DEFAULT '',
            gemini_api_key TEXT NOT NULL DEFAULT '',
            image_generations_used INTEGER NOT NULL DEFAULT 0,
            image_generations_limit INTEGER NOT NULL DEFAULT 3,
            is_subscribed INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('image', 'text')),
            prompt TEXT NOT NULL,
            model TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    db.commit()
    db.close()


def get_user_by_google_id(google_id):
    db = get_db()
    return db.execute(
        "SELECT * FROM users WHERE google_id = ?", (google_id,)
    ).fetchone()


def get_user_by_id(user_id):
    db = get_db()
    return db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(google_id, email, name, avatar_url):
    db = get_db()
    cur = db.execute(
        """INSERT INTO users (google_id, email, name, avatar_url)
           VALUES (?, ?, ?, ?)""",
        (google_id, email, name, avatar_url),
    )
    db.commit()
    return cur.lastrowid


def update_user_google_info(user_id, email, name, avatar_url):
    db = get_db()
    db.execute(
        """UPDATE users SET email=?, name=?, avatar_url=?, updated_at=?
           WHERE id=?""",
        (email, name, avatar_url, datetime.utcnow(), user_id),
    )
    db.commit()


def set_gemini_api_key(user_id, api_key):
    db = get_db()
    db.execute(
        "UPDATE users SET gemini_api_key=?, updated_at=? WHERE id=?",
        (api_key, datetime.utcnow(), user_id),
    )
    db.commit()


def record_generation(user_id, gen_type, prompt, model):
    db = get_db()
    if gen_type == "image":
        db.execute(
            """UPDATE users SET image_generations_used = image_generations_used + 1,
               updated_at=? WHERE id=?""",
            (datetime.utcnow(), user_id),
        )
    db.execute(
        "INSERT INTO generations (user_id, type, prompt, model) VALUES (?, ?, ?, ?)",
        (user_id, gen_type, prompt, model),
    )
    db.commit()


def get_generations(user_id, limit=10):
    db = get_db()
    return db.execute(
        """SELECT * FROM generations WHERE user_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
