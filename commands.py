from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_db, log_action, get_chat_settings
from language import get_message
from utils import check_admin, get_target_user, is_anonymous_admin

def start(update, context):
    chat_id = update.effective_chat.id
    update.message.reply_text(get_message(chat_id, "start"))

def help_command(update, context):
    chat_id = update.effective_chat.id
    update.message.reply_text(get_message(chat_id, "help"))

def ban(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if is_anonymous_admin(update, context):
        keyboard = [[InlineKeyboardButton("אמת הרשאות", callback_data=f"verify_ban_{chat_id}_{update.message.message_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("לחץ לאימות הרשאותיך:", reply_markup=reply_markup)
        return
    
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    context.bot.ban_chat_member(chat_id, target.id)
    update.message.reply_text(get_message(chat_id, "banned").format(user=target.full_name))
    log_action(chat_id, f"{target.full_name} banned by {update.effective_user.full_name}")

def unban(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    if len(context.args) == 0:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    target_id = context.args[0]
    context.bot.unban_chat_member(chat_id, target_id)
    update.message.reply_text(get_message(chat_id, "unbanned").format(user=target_id))
    log_action(chat_id, f"{target_id} unbanned by {update.effective_user.full_name}")

def kick(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    context.bot.ban_chat_member(chat_id, target.id)
    context.bot.unban_chat_member(chat_id, target.id)
    update.message.reply_text(get_message(chat_id, "kicked").format(user=target.full_name))
    log_action(chat_id, f"{target.full_name} kicked by {update.effective_user.full_name}")

def mute(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    duration = context.args[1] if len(context.args) > 1 else "1h"
    seconds = {"m": 60, "h": 3600, "d": 86400}
    try:
        time_value = int(duration[:-1]) * seconds[duration[-1]]
    except (ValueError, KeyError):
        time_value = 3600  # ברירת מחדל לשעה
    
    context.bot.restrict_chat_member(chat_id, target.id, until_date=time_value, can_send_messages=False)
    update.message.reply_text(get_message(chat_id, "muted").format(user=target.full_name, time=duration))
    log_action(chat_id, f"{target.full_name} muted for {duration} by {update.effective_user.full_name}")

def unmute(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    context.bot.restrict_chat_member(chat_id, target.id, can_send_messages=True)
    update.message.reply_text(get_message(chat_id, "unmuted").format(user=target.full_name))
    log_action(chat_id, f"{target.full_name} unmuted by {update.effective_user.full_name}")

def warn(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    conn, c = get_db()
    c.execute("INSERT OR REPLACE INTO warnings (chat_id, user_id, count, reason) VALUES (?, ?, COALESCE((SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?) + 1, 1), ?)", 
              (chat_id, target.id, chat_id, target.id, reason))
    conn.commit()
    
    c.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, target.id))
    warn_count = c.fetchone()[0]
    settings = get_chat_settings(chat_id)
    max_warns = settings.get("max_warns", 3)
    
    # הוספת כפתור "בטל אזהרה"
    keyboard = [[InlineKeyboardButton("בטל אזהרה", callback_data=f"unwarn_{target.id}_{chat_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        get_message(chat_id, "warned").format(user=target.full_name, count=warn_count, reason=reason),
        reply_markup=reply_markup
    )
    log_action(chat_id, f"{target.full_name} warned ({warn_count}/{max_warns}) by {update.effective_user.full_name}: {reason}")
    
    if warn_count >= max_warns:
        action = settings.get("warn_action", "kick")
        if action == "kick":
            context.bot.ban_chat_member(chat_id, target.id)
            context.bot.unban_chat_member(chat_id, target.id)
            update.message.reply_text(get_message(chat_id, "kicked_after_warns").format(user=target.full_name))
        elif action == "ban":
            context.bot.ban_chat_member(chat_id, target.id)
            update.message.reply_text(get_message(chat_id, "banned_after_warns").format(user=target.full_name))
        elif action == "mute":
            context.bot.restrict_chat_member(chat_id, target.id, until_date=86400, can_send_messages=False)
            update.message.reply_text(get_message(chat_id, "muted_after_warns").format(user=target.full_name))

def unwarn(update, context):
    chat_id = update.effective_chat.id
    if not check_admin(update, context):
        update.message.reply_text(get_message(chat_id, "not_admin"))
        return
    
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    conn, c = get_db()
    c.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, target.id))
    result = c.fetchone()
    if not result or result[0] == 0:
        update.message.reply_text(get_message(chat_id, "no_warnings").format(user=target.full_name))
        return
    
    c.execute("UPDATE warnings SET count = count - 1 WHERE chat_id = ? AND user_id = ?", (chat_id, target.id))
    conn.commit()
    
    c.execute("SELECT count FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, target.id))
    warn_count = c.fetchone()[0]
    update.message.reply_text(get_message(chat_id, "unwarned").format(user=target.full_name, count=warn_count))
    log_action(chat_id, f"Warning removed from {target.full_name} by {update.effective_user.full_name} ({warn_count} left)")

def warns(update, context):
    chat_id = update.effective_chat.id
    target = get_target_user(update, context)
    if not target:
        update.message.reply_text(get_message(chat_id, "no_target"))
        return
    
    conn, c = get_db()
    c.execute("SELECT count, reason FROM warnings WHERE chat_id = ? AND user_id = ?", (chat_id, target.id))
    result = c.fetchone()
    if result and result[0] > 0:
        update.message.reply_text(get_message(chat_id, "warn_count").format(user=target.full_name, count=result[0], reason=result[1]))
    else:
        update.message.reply_text(get_message(chat_id, "no_warnings").format(user=target.full_name))
