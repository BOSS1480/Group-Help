from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, get_chat_settings
from language import get_message
from utils import check_admin
from commands import warn, mute

def settings_menu(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    settings = get_chat_settings(chat_id)
    lang = settings.get("language", "en")
    service_status = "✅" if settings.get("delete_service", "False") == "True" else "❌"
    link_action = settings.get("link_action", "off")
    max_warns = settings.get("max_warns", "3")
    warn_action = settings.get("warn_action", "kick")
    
    keyboard = [
        [InlineKeyboardButton("שפה", callback_data="lang_label"), 
         InlineKeyboardButton(f"{lang}", callback_data="toggle_lang")],
        [InlineKeyboardButton("הודעות שירות", callback_data="service_label"), 
         InlineKeyboardButton(service_status, callback_data="toggle_service")],
        [InlineKeyboardButton("ניהול קישורים", callback_data="link_label"), 
         InlineKeyboardButton(link_action, callback_data="cycle_link")],
        [InlineKeyboardButton("מספר אזהרות", callback_data="warns_label"), 
         InlineKeyboardButton(max_warns, callback_data="cycle_warns")],
        [InlineKeyboardButton("פעולה לאחר אזהרות", callback_data="action_label"), 
         InlineKeyboardButton(warn_action, callback_data="cycle_action")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(get_message(chat_id, "settings_menu"), reply_markup=reply_markup)

def button_handler(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data
    settings = get_chat_settings(chat_id)
    
    if data == "toggle_lang":
        new_lang = "he" if settings.get("language", "en") == "en" else "en"
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO chats (chat_id, language) VALUES (?, ?)", (chat_id, new_lang))
        conn.commit()
        update_settings_message(query, context, chat_id)
    
    elif data == "toggle_service":
        new_status = "False" if settings.get("delete_service", "False") == "True" else "True"
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'delete_service', ?)", (chat_id, new_status))
        conn.commit()
        update_settings_message(query, context, chat_id)
    
    elif data == "cycle_link":
        actions = ["off", "delete", "warn", "mute"]
        current = settings.get("link_action", "off")
        new_action = actions[(actions.index(current) + 1) % len(actions)]
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'link_action', ?)", (chat_id, new_action))
        conn.commit()
        update_settings_message(query, context, chat_id)
    
    elif data == "cycle_warns":
        warns = ["2", "3", "4"]
        current = settings.get("max_warns", "3")
        new_warns = warns[(warns.index(current) + 1) % len(warns)]
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'max_warns', ?)", (chat_id, new_warns))
        conn.commit()
        update_settings_message(query, context, chat_id)
    
    elif data == "cycle_action":
        actions = ["kick", "ban", "mute"]
        current = settings.get("warn_action", "kick")
        new_action = actions[(actions.index(current) + 1) % len(actions)]
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'warn_action', ?)", (chat_id, new_action))
        conn.commit()
        update_settings_message(query, context, chat_id)
    
    elif data.startswith("unwarn_"):
        from commands import unwarn_by_button
        unwarn_by_button(update, context)
    
    elif data.startswith("verify_"):
        from commands import verify_admin
        verify_admin(update, context)

def update_settings_message(query, context, chat_id):
    settings = get_chat_settings(chat_id)
    lang = settings.get("language", "en")
    service_status = "✅" if settings.get("delete_service", "False") == "True" else "❌"
    link_action = settings.get("link_action", "off")
    max_warns = settings.get("max_warns", "3")
    warn_action = settings.get("warn_action", "kick")
    
    keyboard = [
        [InlineKeyboardButton("שפה", callback_data="lang_label"), 
         InlineKeyboardButton(f"{lang}", callback_data="toggle_lang")],
        [InlineKeyboardButton("הודעות שירות", callback_data="service_label"), 
         InlineKeyboardButton(service_status, callback_data="toggle_service")],
        [InlineKeyboardButton("ניהול קישורים", callback_data="link_label"), 
         InlineKeyboardButton(link_action, callback_data="cycle_link")],
        [InlineKeyboardButton("מספר אזהרות", callback_data="warns_label"), 
         InlineKeyboardButton(max_warns, callback_data="cycle_warns")],
        [InlineKeyboardButton("פעולה לאחר אזהרות", callback_data="action_label"), 
         InlineKeyboardButton(warn_action, callback_data="cycle_action")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(get_message(chat_id, "settings_menu"), reply_markup=reply_markup)

def handle_settings_input(update, context):
    chat_id = update.effective_chat.id
    settings = get_chat_settings(chat_id)
    if settings.get("link_action") in ["delete", "warn", "mute"] and "http" in update.message.text:
        if settings["link_action"] == "delete":
            update.message.delete()
        elif settings["link_action"] == "warn":
            warn(update, context)
        elif settings["link_action"] == "mute":
            mute(update, context)
