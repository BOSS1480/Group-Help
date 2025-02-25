from telegram.ext import ContextTypes
from database import get_db, get_chat_settings
from language import get_message
from commands import check_admin

def add_filter(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    if not update.message.reply_to_message or len(context.args) == 0:
        update.message.reply_text(get_message(chat_id, "filter_usage"))
        return
    
    trigger = context.args[0]
    response = update.message.reply_to_message.text
    conn, c = get_db()
    c.execute("INSERT OR REPLACE INTO filters (chat_id, trigger, response) VALUES (?, ?, ?)", (chat_id, trigger, response))
    conn.commit()
    update.message.reply_text(get_message(chat_id, "filter_added").format(trigger=trigger))

def remove_filter(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    if len(context.args) == 0:
        update.message.reply_text(get_message(chat_id, "stop_usage"))
        return
    
    trigger = context.args[0]
    conn, c = get_db()
    c.execute("DELETE FROM filters WHERE chat_id = ? AND trigger = ?", (chat_id, trigger))
    if c.rowcount > 0:
        update.message.reply_text(get_message(chat_id, "filter_removed").format(trigger=trigger))
    else:
        update.message.reply_text(get_message(chat_id, "filter_not_found").format(trigger=trigger))
    conn.commit()

def list_filters(update, context):
    chat_id = update.effective_chat.id
    conn, c = get_db()
    c.execute("SELECT trigger FROM filters WHERE chat_id = ?", (chat_id,))
    filters = c.fetchall()
    if filters:
        filter_list = "\n".join([f"- {f[0]}" for f in filters])
        update.message.reply_text(get_message(chat_id, "filters_list").format(filters=filter_list))
    else:
        update.message.reply_text(get_message(chat_id, "no_filters"))

def set_welcome(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    if len(context.args) == 0 or context.args[0] not in ["on", "off"]:
        update.message.reply_text(get_message(chat_id, "welcome_usage"))
        return
    
    status = context.args[0] == "on"
    conn, c = get_db()
    c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'welcome_enabled', ?)", (chat_id, str(status)))
    conn.commit()
    update.message.reply_text(get_message(chat_id, "welcome_set").format(status=context.args[0]))

def set_welcome_message(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    if not update.message.reply_to_message:
        update.message.reply_text(get_message(chat_id, "setwelcome_usage"))
        return
    
    message = update.message.reply_to_message.text
    conn, c = get_db()
    c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'welcome_message', ?)", (chat_id, message))
    conn.commit()
    update.message.reply_text(get_message(chat_id, "welcome_message_set"))

def handle_filters_and_welcome(update, context):
    chat_id = update.effective_chat.id
    message = update.message
    text = message.text.lower()
    
    # פילטרים
    conn, c = get_db()
    c.execute("SELECT trigger, response FROM filters WHERE chat_id = ?", (chat_id,))
    filters = dict(c.fetchall())
    if text in filters:
        update.message.reply_text(filters[text])
    
    # ברוכים הבאים
    if message.new_chat_members:
        settings = get_chat_settings(chat_id)
        if settings.get("welcome_enabled", "False") == "True":
            welcome_msg = settings.get("welcome_message")
            if not welcome_msg:
                lang = settings.get("language", "en")
                group_name = update.effective_chat.title
                user = message.new_chat_members[0]
                welcome_msg = get_message(chat_id, "default_welcome").format(user=user.mention_html(user.id), group=group_name)
            update.message.reply_text(welcome_msg, parse_mode="HTML")
