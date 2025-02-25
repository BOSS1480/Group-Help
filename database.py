import sqlite3

def get_db():
    conn = sqlite3.connect("bot.db")
    c = conn.cursor()
    return conn, c

def init_db():
    conn, c = get_db()
    c.execute("CREATE TABLE IF NOT EXISTS chats (chat_id INTEGER PRIMARY KEY, language TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS warnings (chat_id INTEGER, user_id INTEGER, count INTEGER, reason TEXT, PRIMARY KEY (chat_id, user_id))")
    c.execute("CREATE TABLE IF NOT EXISTS filters (chat_id INTEGER, trigger TEXT, response TEXT, PRIMARY KEY (chat_id, trigger))")
    c.execute("CREATE TABLE IF NOT EXISTS settings (chat_id INTEGER, key TEXT, value TEXT, PRIMARY KEY (chat_id, key))")
    c.execute("CREATE TABLE IF NOT EXISTS logs (chat_id INTEGER, message TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

def log_action(chat_id, message):
    conn, c = get_db()
    c.execute("INSERT INTO logs (chat_id, message) VALUES (?, ?)", (chat_id, message))
    conn.commit()

def get_chat_settings(chat_id):
    conn, c = get_db()
    c.execute("SELECT key, value FROM settings WHERE chat_id = ?", (chat_id,))
    settings = dict(c.fetchall())
    conn.close()
    return settings
