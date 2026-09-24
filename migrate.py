import database as db

db.init_db()

pw_hash = db.get_config('dashboard_password_hash')
if pw_hash:
    conn = db.get_conn()
    count = conn.execute('SELECT COUNT(*) FROM admins').fetchone()[0]
    if count == 0:
        db.add_admin('admin', pw_hash)
        print('Migrated admin password')
    conn.close()
