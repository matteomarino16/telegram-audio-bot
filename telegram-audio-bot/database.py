import sqlite3

conn = sqlite3.connect("tracks.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    file_id TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER NOT NULL,
    track_id INTEGER NOT NULL,
    UNIQUE(user_id, track_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    request_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()
print("Database creato: tracks.db")
