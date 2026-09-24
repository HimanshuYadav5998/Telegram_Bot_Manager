import sqlite3
import threading
import os
from datetime import datetime
from pathlib import Path

# In production (Railway/VPS), set DATA_DIR env var to a persistent volume path.
# Falls back to the directory of this file for local development.
_data_dir = Path(os.environ.get("DATA_DIR", Path(__file__).parent))
_data_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = _data_dir / "bot_data.db"
_lock = threading.Lock()


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = get_conn()
        cur = conn.cursor()

        # Users table — everyone who interacted with the bot
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                user_id     INTEGER UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT,
                first_seen  TEXT NOT NULL,
                status      TEXT DEFAULT 'active'
            )
        """)

        # Events table — all bot activity
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                user_id     INTEGER,
                username    TEXT,
                full_name   TEXT,
                detail      TEXT,
                created_at  TEXT NOT NULL
            )
        """)

        # Join requests table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS join_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER UNIQUE NOT NULL,
                username    TEXT,
                full_name   TEXT,
                status      TEXT DEFAULT 'pending',
                created_at  TEXT NOT NULL,
                updated_at  TEXT
            )
        """)

        # Bot config table (key-value store)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_config (
                key     TEXT PRIMARY KEY,
                value   TEXT
            )
        """)

        # Seed default config
        cur.execute("""
            INSERT OR IGNORE INTO bot_config (key, value)
            VALUES ('channel_link', 'https://t.me/+SoODptmHu-ZiMTA1')
        """)
        cur.execute("""
            INSERT OR IGNORE INTO bot_config (key, value)
            VALUES ('bot_status', 'running')
        """)
        cur.execute("""
            INSERT OR IGNORE INTO bot_config (key, value)
            VALUES ('bot_token', '8837148012:AAFhSZx8L9bcI1iYFkIJyWLoVxxU9EMuPEs')
        """)

        
        # Admins table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')

        # Previews table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS previews (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        ''')

        # Preview Access table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS preview_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preview_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                message_ids TEXT,
                accessed_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                deleted INTEGER DEFAULT 0
            )
        ''')
    
        conn.commit()
        conn.close()


# ─── Users ────────────────────────────────────────────────────────────────────

def upsert_user(user_id: int, username: str, full_name: str):
    with _lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO users (user_id, username, full_name, first_seen)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()


def get_all_users(search: str = ""):
    conn = get_conn()
    if search:
        rows = conn.execute("""
            SELECT * FROM users
            WHERE username LIKE ? OR full_name LIKE ? OR CAST(user_id AS TEXT) LIKE ?
            ORDER BY first_seen DESC
        """, (f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()
    else:
        rows = conn.execute("SELECT * FROM users ORDER BY first_seen DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_user_status(user_id: int, status: str):
    with _lock:
        conn = get_conn()
        conn.execute("UPDATE users SET status=? WHERE user_id=?", (status, user_id))
        conn.commit()
        conn.close()


# ─── Events ───────────────────────────────────────────────────────────────────

def log_event(event_type: str, user_id: int = None, username: str = None,
              full_name: str = None, detail: str = None):
    with _lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO events (event_type, user_id, username, full_name, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_type, user_id, username, full_name, detail,
              datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()


def get_recent_events(limit: int = 50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM events ORDER BY created_at DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Join Requests ─────────────────────────────────────────────────────────────

def upsert_join_request(user_id: int, username: str, full_name: str):
    with _lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO join_requests (user_id, username, full_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()


def update_join_request_status(user_id: int, status: str):
    with _lock:
        conn = get_conn()
        conn.execute("""
            UPDATE join_requests SET status=?, updated_at=? WHERE user_id=?
        """, (status, datetime.utcnow().isoformat(), user_id))
        conn.commit()
        conn.close()


def get_join_requests(status: str = None):
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM join_requests WHERE status=? ORDER BY created_at DESC",
            (status,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM join_requests ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Stats ────────────────────────────────────────────────────────────────────

def get_stats():
    conn = get_conn()
    total_users     = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_starts    = conn.execute(
        "SELECT COUNT(*) FROM events WHERE event_type='start'"
    ).fetchone()[0]
    total_requests  = conn.execute("SELECT COUNT(*) FROM join_requests").fetchone()[0]
    approved        = conn.execute(
        "SELECT COUNT(*) FROM join_requests WHERE status='approved'"
    ).fetchone()[0]
    rejected        = conn.execute(
        "SELECT COUNT(*) FROM join_requests WHERE status='rejected'"
    ).fetchone()[0]
    pending         = conn.execute(
        "SELECT COUNT(*) FROM join_requests WHERE status='pending'"
    ).fetchone()[0]
    banned_users    = conn.execute(
        "SELECT COUNT(*) FROM users WHERE status='banned'"
    ).fetchone()[0]
    conn.close()
    return {
        "total_users":    total_users,
        "total_starts":   total_starts,
        "total_requests": total_requests,
        "approved":       approved,
        "rejected":       rejected,
        "pending":        pending,
        "banned_users":   banned_users,
    }


# ─── Config ───────────────────────────────────────────────────────────────────

def get_config(key: str):
    conn = get_conn()
    row = conn.execute("SELECT value FROM bot_config WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else None


def set_config(key: str, value: str):
    with _lock:
        conn = get_conn()
        conn.execute("""
            INSERT INTO bot_config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value))
        conn.commit()
        conn.close()


# ─── Admins ───────────────────────────────────────────────────────────────────

def get_admin(username: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None

def add_admin(username: str, password_hash: str):
    with _lock:
        conn = get_conn()
        try:
            conn.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", (username, password_hash))
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False
        conn.close()
        return success

def delete_admin(username: str):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM admins WHERE username=?", (username,))
        conn.commit()
        conn.close()

def get_all_admins():
    conn = get_conn()
    rows = conn.execute("SELECT username FROM admins").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Previews ─────────────────────────────────────────────────────────────────

def create_preview(preview_id: str, name: str, type: str, content: str):
    with _lock:
        conn = get_conn()
        conn.execute('''
            INSERT INTO previews (id, name, type, content, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        ''', (preview_id, name, type, content, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

def get_previews():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM previews ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_preview(preview_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM previews WHERE id=?", (preview_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

def toggle_preview(preview_id: str, is_active: int):
    with _lock:
        conn = get_conn()
        conn.execute("UPDATE previews SET is_active=? WHERE id=?", (is_active, preview_id))
        conn.commit()
        conn.close()

def delete_preview(preview_id: str):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM previews WHERE id=?", (preview_id,))
        # Also clean up access records
        conn.execute("DELETE FROM preview_access WHERE preview_id=?", (preview_id,))
        conn.commit()
        conn.close()


# ─── Preview Access ───────────────────────────────────────────────────────────

def record_preview_access(preview_id: str, user_id: int, chat_id: int, message_ids: str, accessed_at: str, expires_at: str):
    with _lock:
        conn = get_conn()
        conn.execute('''
            INSERT INTO preview_access (preview_id, user_id, chat_id, message_ids, accessed_at, expires_at, deleted)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (preview_id, user_id, chat_id, message_ids, accessed_at, expires_at))
        conn.commit()
        conn.close()

def get_expired_accesses():
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    rows = conn.execute('''
        SELECT * FROM preview_access 
        WHERE expires_at <= ? AND deleted = 0
    ''', (now,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_access_deleted(access_id: int):
    with _lock:
        conn = get_conn()
        conn.execute("UPDATE preview_access SET deleted=1 WHERE id=?", (access_id,))
        conn.commit()
        conn.close()

def get_active_access(preview_id: str, user_id: int):
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    row = conn.execute('''
        SELECT * FROM preview_access
        WHERE preview_id=? AND user_id=? AND expires_at > ? AND deleted = 0
        ORDER BY expires_at DESC LIMIT 1
    ''', (preview_id, user_id, now)).fetchone()
    conn.close()
    return dict(row) if row else None
