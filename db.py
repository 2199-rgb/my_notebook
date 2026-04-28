import sqlite3

from flask import g

from config import DB_NAME


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = sqlite3.connect(DB_NAME)
        db.row_factory = sqlite3.Row
        g._database = db
    return db


def close_db(exception=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        g._database = None


def get_direct_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_direct_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS essays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            image_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        c.execute('ALTER TABLE essays ADD COLUMN image_path TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE essays ADD COLUMN author_name TEXT DEFAULT "寒食季"')
    except sqlite3.OperationalError:
        pass
    try:
        c.execute('ALTER TABLE essays ADD COLUMN author_type TEXT DEFAULT "protected"')
    except sqlite3.OperationalError:
        pass

    c.execute("UPDATE essays SET author_name = '寒食季' WHERE author_name IS NULL OR author_name = ''")
    c.execute("UPDATE essays SET author_type = 'protected' WHERE author_type IS NULL OR author_type = ''")
    c.execute('''
        CREATE TABLE IF NOT EXISTS ddls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            target_date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    c.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
            path, title, content, category
        )
    ''')

    c.execute("SELECT value FROM meta WHERE key = 'tz_fixed'")
    row = c.fetchone()
    if not row:
        c.execute("UPDATE essays SET created_at = datetime(created_at, '+8 hours')")
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('tz_fixed', '1')")

    conn.commit()
    conn.close()
