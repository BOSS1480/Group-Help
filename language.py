import json
from database import get_db
from commands import check_admin

def load_messages():
    with open("messages.json", "r", encoding="utf-8") as f:
        return json.load(f)

MESSAGES = load_messages()

def get_message(chat_id, key):
    conn, c = get_db()
    c.execute("SELECT language FROM chats WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    lang = result[0] if result else "en"
    return MESSAGES[lang].get(key, "Message not found")

def set_language(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    if len(context.args) == 0 or context.args[0] not in ["he", "en"]:
        update.message.reply_text(get_message(chat_id, "setlang_usage"))
        return
    
    lang = context.args[0]
    conn, c = get_db()
    c.execute("INSERT OR REPLACE INTO chats (chat_id, language) VALUES (?, ?)", (chat_id, lang))
    conn.commit()
    update.message.reply_text(get_message(chat_id, "language_set").format(lang=lang))
