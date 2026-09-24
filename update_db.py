import re

def update_database():
    with open('database.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update init_db schema
    schema_additions = """
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
    """
    
    # insert before conn.commit() in init_db
    content = content.replace("conn.commit()", schema_additions + "\n        conn.commit()", 1)

    # 2. Add new functions for Admins and Previews
    new_functions = """
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
"""

    content += "\n" + new_functions

    with open('database.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    update_database()
