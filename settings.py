from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_db, get_chat_settings
from language import get_message
from commands import check_admin, warn, mute

def settings_menu(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    keyboard = [
        [InlineKeyboardButton("מחיקת הודעות שירות", callback_data="delete_service")],
        [InlineKeyboardButton("ניהול קישורים", callback_data="link_action")],
        [InlineKeyboardButton("מספר אזהרות מקסימלי", callback_data="max_warns")],
        [InlineKeyboardButton("פעולה לאחר אזהרות", callback_data="warn_action")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(get_message(chat_id, "settings_menu"), reply_markup=reply_markup)

def button_handler(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    data = query.data
    
    if data == "delete_service":
        keyboard = [
            [InlineKeyboardButton("כן", callback_data="service_yes"), InlineKeyboardButton("לא", callback_data="service_no")]
        ]
        query.edit_message_text(get_message(chat_id, "delete_service_prompt"), reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("service_"):
        value = "True" if data == "service_yes" else "False"
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'delete_service', ?)", (chat_id, value))
        conn.commit()
        query.edit_message_text(get_message(chat_id, "delete_service_set").format(status="כן" if value == "True" else "לא"))
    
    elif data == "link_action":
        keyboard = [
            [InlineKeyboardButton("מחק", callback_data="link_delete"),
             InlineKeyboardButton("אזהרה", callback_data="link_warn"),
             InlineKeyboardButton("השתק", callback_data="link_mute")]
        ]
        query.edit_message_text(get_message(chat_id, "link_action_prompt"), reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("link_"):
        action = data.split("_")[1]
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'link_action', ?)", (chat_id, action))
        conn.commit()
        query.edit_message_text(get_message(chat_id, "link_action_set").format(action=action))
    
    elif data == "max_warns":
        keyboard = [
            [InlineKeyboardButton("2", callback_data="warns_2"),
             InlineKeyboardButton("3", callback_data="warns_3"),
             InlineKeyboardButton("4", callback_data="warns_4")]
        ]
        query.edit_message_text(get_message(chat_id, "max_warns_prompt"), reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("warns_"):
        count = data.split("_")[1]
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'max_warns', ?)", (chat_id, count))
        conn.commit()
        query.edit_message_text(get_message(chat_id, "max_warns_set").format(count=count))
    
    elif data == "warn_action":
        keyboard = [
            [InlineKeyboardButton("הרחקה", callback_data="action_kick"),
             InlineKeyboardButton("חסימה", callback_data="action_ban"),
             InlineKeyboardButton("השתק", callback_data="action_mute")]
        ]
        query.edit_message_text(get_message(chat_id, "warn_action_prompt"), reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("action_"):
        action = data.split("_")[1]
        conn, c = get_db()
        c.execute("INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, 'warn_action', ?)", (chat_id, action))
        conn.commit()
        query.edit_message_text(get_message(chat_id, "warn_action_set").format(action=action))

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
