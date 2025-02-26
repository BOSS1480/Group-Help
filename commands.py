# commands.py
import time
import logging

from telegram import ParseMode, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

from utils import (
    get_chat_config, get_language_text, log_action, get_target_user, parse_duration,
    admin_required, save_data, group_only, is_user_admin
)
from messages import LANG

logger = logging.getLogger(__name__)

def build_settings(chat_config):
    lang = chat_config.get("language", "he")
    if lang == "he":
        title = "📋 הגדרות הקבוצה:"
        language_label = "שפה"
        warn_limit_label = "מספר אזהרות"
        service_msgs_label = "הודעות שירות"
        links_label = "טיפול בקישורים"
        language_value = "עברית" if chat_config.get("language", "he") == "he" else "אנגלית"
        warn_limit_value = str(chat_config.get("warn_limit", 3))
        service_msgs_value = "מופעלות" if chat_config.get("service_msgs", True) else "כבויות"
        links_value = chat_config.get("links_action", "delete")
    else:
        title = "📋 Group Settings:"
        language_label = "Language"
        warn_limit_label = "Warn Limit"
        service_msgs_label = "Service Messages"
        links_label = "Links Handling"
        language_value = "English" if chat_config.get("language", "he") == "en" else "Hebrew"
        warn_limit_value = str(chat_config.get("warn_limit", 3))
        service_msgs_value = "On" if chat_config.get("service_msgs", True) else "Off"
        links_value = chat_config.get("links_action", "delete")
    text = (
        f"<b>{title}</b>\n"
        f"<b>{language_label}:</b> {language_value}\n"
        f"<b>{warn_limit_label}:</b> {warn_limit_value}\n"
        f"<b>{service_msgs_label}:</b> {service_msgs_value}\n"
        f"<b>{links_label}:</b> {links_value}"
    )
    keyboard = [
        [
            InlineKeyboardButton(language_label, callback_data="change_language"),
            InlineKeyboardButton(language_value, callback_data="change_language")
        ],
        [
            InlineKeyboardButton(warn_limit_label, callback_data="change_warn_limit"),
            InlineKeyboardButton(warn_limit_value, callback_data="change_warn_limit")
        ],
        [
            InlineKeyboardButton(service_msgs_label, callback_data="toggle_service_msgs"),
            InlineKeyboardButton(service_msgs_value, callback_data="toggle_service_msgs")
        ],
        [
            InlineKeyboardButton(links_label, callback_data="change_links_action"),
            InlineKeyboardButton(links_value, callback_data="change_links_action")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return text, reply_markup

# /start – הודעת פתיחה עם כפתורים
def start(update, context):
    chat_config = get_chat_config(update.effective_chat.id)
    lang = chat_config.get("language", "he")
    keyboard = [
        [InlineKeyboardButton("➤ הוסף אותי לקבוצה", url="https://t.me/tsst_php_bot?startgroup=add")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_html(LANG[lang]["start"], reply_markup=reply_markup)

def help_command(update, context):
    chat_config = get_chat_config(update.effective_chat.id)
    lang = chat_config.get("language", "he")
    keyboard = [
        [InlineKeyboardButton("← חזרה", callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_html(LANG[lang]["help"], reply_markup=reply_markup)

def main_menu_callback(update, context):
    query = update.callback_query
    query.answer()
    chat_config = get_chat_config(update.effective_chat.id)
    lang = chat_config.get("language", "he")
    if query.data == "show_help":
        keyboard = [[InlineKeyboardButton("← חזרה", callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_html(LANG[lang]["help"], reply_markup=reply_markup)
    elif query.data == "back_to_start":
        keyboard = [
            [InlineKeyboardButton("➤ הוסף אותי לקבוצה", url="https://t.me/tsst_php_bot?startgroup=add")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_html(LANG[lang]["start"], reply_markup=reply_markup)
    elif query.data == "auth_admin":
        auth_callback(update, context)
    else:
        query.edit_message_text("פעולה לא ידועה.")

@group_only
@admin_required
def ban(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    if is_user_admin(update, target.id):
        update.message.reply_html("לא ניתן לבצע פעולה על מנהל.")
        return
    try:
        chat.kick_member(target.id)
        update.message.reply_html(
            f"המשתמש <a href=\"tg://user?id={target.id}\">{target.first_name}</a> <b>חסום</b> בהצלחה."
        )
        log_action(update, f"Banned user: {target.id}")
    except TelegramError as e:
        logger.error(e)
        update.message.reply_text(str(e))

@group_only
@admin_required
def unban(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    try:
        chat.unban_member(target.id)
        update.message.reply_html(
            f"המשתמש <a href=\"tg://user?id={target.id}\">{target.first_name}</a> <b>שוחרר</b> מהחסימה."
        )
        log_action(update, f"Unbanned user: {target.id}")
    except TelegramError as e:
        logger.error(e)
        update.message.reply_text(str(e))

@group_only
@admin_required
def kick(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    if is_user_admin(update, target.id):
        update.message.reply_html("לא ניתן לבצע פעולה על מנהל.")
        return
    try:
        chat.kick_member(target.id)
        chat.unban_member(target.id)
        update.message.reply_html(
            f"המשתמש <a href=\"tg://user?id={target.id}\">{target.first_name}</a> <b>עוף</b> מהקבוצה."
        )
        log_action(update, f"Kicked user: {target.id}")
    except TelegramError as e:
        logger.error(e)
        update.message.reply_text(str(e))

@group_only
@admin_required
def mute(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    if is_user_admin(update, target.id):
        update.message.reply_html("לא ניתן לבצע פעולה על מנהל.")
        return
    if not context.args:
        update.message.reply_text("אנא ספק/י משך זמן (למשל, 1m, 1h, 1d).")
        return
    duration = parse_duration(context.args[0])
    if duration is None:
        update.message.reply_text("פורמט זמן לא חוקי.")
        return
    until_date = int(time.time() + duration)
    try:
        perms = ChatPermissions(can_send_messages=False)
        chat.restrict_member(target.id, permissions=perms, until_date=until_date)
        update.message.reply_html(
            f"המשתמש <a href=\"tg://user?id={target.id}\">{target.first_name}</a> <b>הושתק</b> למשך {context.args[0]}."
        )
        log_action(update, f"Muted user: {target.id} for {context.args[0]}")
    except TelegramError as e:
        logger.error(e)
        update.message.reply_text(str(e))

@group_only
@admin_required
def unmute(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    try:
        perms = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
        chat.restrict_member(target.id, permissions=perms, until_date=0)
        update.message.reply_html(
            f"המשתמש <a href=\"tg://user?id={target.id}\">{target.first_name}</a> <b>השתקתו בוטלה</b>."
        )
        log_action(update, f"Unmuted user: {target.id}")
    except TelegramError as e:
        logger.error(e)
        update.message.reply_text(str(e))

@group_only
@admin_required
def warn(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    if is_user_admin(update, target.id):
        update.message.reply_html("לא ניתן לתת אזהרה למנהל.")
        return
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    chat_config = get_chat_config(chat.id)
    warns_dict = chat_config.get("warns", {})
    user_warns = warns_dict.get(str(target.id), [])
    user_warns.append({"reason": reason, "time": int(time.time())})
    warns_dict[str(target.id)] = user_warns
    chat_config["warns"] = warns_dict
    save_data()
    current_warns = len(user_warns)
    limit = chat_config.get("warn_limit", 3)
    reason_line = f"\nסיבה: <i>{reason}</i>" if reason else ""
    text = LANG[chat_config.get("language", "he")]["warns_info"].format(
        id=target.id, name=target.first_name, current=current_warns, limit=limit, reason_line=reason_line
    )
    keyboard = [[InlineKeyboardButton("ביטול אזהרה", callback_data=f"cancel_warn:{chat.id}:{target.id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message.reply_to_message:
        update.message.reply_to_message.reply_html(text, reply_markup=reply_markup)
    else:
        update.message.reply_html(text, reply_markup=reply_markup)
    log_action(update, f"Warned user: {target.id} (Reason: {reason})")

@group_only
@admin_required
def unwarn(update, context):
    chat = update.effective_chat
    target = get_target_user(update, context)
    if not target:
        update.message.reply_html(get_language_text(update, "user_not_found"))
        return
    chat_config = get_chat_config(chat.id)
    warns_dict = chat_config.get("warns", {})
    user_warns = warns_dict.get(str(target.id), [])
    if user_warns:
        user_warns.pop()
        warns_dict[str(target.id)] = user_warns
        chat_config["warns"] = warns_dict
        save_data()
        update.message.reply_html(
            f"המנהל <a href=\"tg://user?id={update.effective_user.id}\">{update.effective_user.first_name}</a> הסיר אזהרה מהמשתמש "
            f"<a href=\"tg://user?id={target.id}\">{target.first_name}</a>.\n"
            f"כרגע יש לו <b>{len(user_warns)}</b> מתוך <b>{chat_config.get('warn_limit', 3)}</b>."
        )
        log_action(update, f"Removed warning from user: {target.id}")
    else:
        update.message.reply_html(f"<a href=\"tg://user?id={target.id}\">{target.first_name}</a> אין לו אזהרות.")

def warns_command(update, context):
    chat = update.effective_chat
    chat_config = get_chat_config(chat.id)
    warns_dict = chat_config.get("warns", {})
    target = get_target_user(update, context)
    if not target:
        target = update.effective_user
    user_warns = warns_dict.get(str(target.id), [])
    if user_warns:
        reasons = "\n".join([f"{i+1}. {w['reason']}" for i, w in enumerate(user_warns)])
        text = LANG[chat_config.get("language", "he")]["warns_info"].format(
            id=target.id, name=target.first_name, current=len(user_warns),
            limit=chat_config.get("warn_limit", 3), reason_line=f"\nסיבות:\n{reasons}"
        )
        update.message.reply_html(text)
    else:
        update.message.reply_html(LANG[chat_config.get("language", "he")]["no_warns"].format(id=target.id, name=target.first_name))

@group_only
@admin_required
def add_filter(update, context):
    chat = update.effective_chat
    if not update.message.reply_to_message:
        update.message.reply_text("אנא הגיב/י להודעה שתשמש כתשובה לפילטר.")
        return
    if not context.args:
        update.message.reply_text("אנא ספק/י מילה עבור הפילטר.")
        return
    keyword = context.args[0].lower()
    chat_config = get_chat_config(chat.id)
    # שמירת הטקסט כפי שהוא (כולל עיצוב HTML)
    filter_text = update.message.reply_to_message.text_html or update.message.reply_to_message.text
    filters_dict = chat_config.get("filters", {})  # סגור את הסוגריים כראוי
    filters_dict[keyword] = filter_text
    chat_config["filters"] = filters_dict
    save_data()
    update.message.reply_html(f"הפילטר <b>{keyword}</b> נוסף.")
    log_action(update, f"Added filter: {keyword}")

@group_only
@admin_required
def remove_filter(update, context):
    chat = update.effective_chat
    if not context.args:
        update.message.reply_text("אנא ספק/י את המילה עבור הפילטר להסרה.")
        return
    keyword = context.args[0].lower()
    chat_config = get_chat_config(chat.id)
    filters_dict = chat_config.get("filters", {})
    if keyword in filters_dict:
        del filters_dict[keyword]
        chat_config["filters"] = filters_dict
        save_data()
        update.message.reply_html(f"הפילטר <b>{keyword}</b> הוסר.")
        log_action(update, f"Removed filter: {keyword}")
    else:
        update.message.reply_text("פילטר לא נמצא.")

@group_only
def list_filters(update, context):
    chat = update.effective_chat
    chat_config = get_chat_config(chat.id)
    filters_dict = chat_config.get("filters", {})
    if filters_dict:
        msg = "פילטרים:\n" + "\n".join([f"<b>{k}</b>: {v}" for k, v in filters_dict.items()])
        update.message.reply_html(msg)
    else:
        update.message.reply_text("לא הוגדרו פילטרים.")

@group_only
@admin_required
def toggle_welcome(update, context):
    chat = update.effective_chat
    if not context.args:
        update.message.reply_text("אנא ספק/י 'on' או 'off'.")
        return
    arg = context.args[0].lower()
    chat_config = get_chat_config(chat.id)
    if arg == "on":
        chat_config["welcome"]["enabled"] = True
        update.message.reply_html("הודעות הברוכים הבאים <b>מאופשרות</b>.")
    elif arg == "off":
        chat_config["welcome"]["enabled"] = False
        update.message.reply_html("הודעות הברוכים הבאים <b>כבויות</b>.")
    else:
        update.message.reply_text("פרמטר לא חוקי, יש להשתמש ב-'on' או 'off'.")
        return
    save_data()
    log_action(update, f"Set welcome messages to {arg}")

@group_only
@admin_required
def set_welcome_message(update, context):
    chat = update.effective_chat
    if not update.message.reply_to_message:
        update.message.reply_text("אנא הגיב/י להודעה שתשמש כהודעת ברוכים הבאים.")
        return
    chat_config = get_chat_config(chat.id)
    chat_config["welcome"]["message"] = update.message.reply_to_message.text_html or update.message.reply_to_message.text
    save_data()
    update.message.reply_html("הודעת הברוכים הבאים <b>עודכנה</b>.")
    log_action(update, "Set welcome message.")

@group_only
@admin_required
def set_language(update, context):
    chat = update.effective_chat
    if not context.args:
        update.message.reply_text("אנא ספק/י קוד שפה (he או en).")
        return
    lang_code = context.args[0].lower()
    if lang_code not in ["he", "en"]:
        update.message.reply_text("קוד שפה לא חוקי, יש להשתמש ב-'he' או 'en'.")
        return
    chat_config = get_chat_config(chat.id)
    chat_config["language"] = lang_code
    save_data()
    if lang_code == "he":
        update.message.reply_html(LANG["he"]["language_set_he"])
    else:
        update.message.reply_html(LANG["en"]["language_set_en"])
    log_action(update, f"Set language to {lang_code}")

@group_only
@admin_required
def settings(update, context):
    chat = update.effective_chat
    chat_config = get_chat_config(chat.id)
    text, reply_markup = build_settings(chat_config)
    update.message.reply_html(text, reply_markup=reply_markup)
    log_action(update, "Accessed settings.")

def settings_callback(update, context):
    query = update.callback_query
    user = update.effective_user
    if not is_user_admin(update, user.id) and not update.effective_message.sender_chat:
        query.answer("פונקציה זו זמינה רק למנהלים.", show_alert=True)
        return
    query.answer()
    chat = update.effective_chat
    chat_config = get_chat_config(chat.id)
    data_cb = query.data
    if data_cb == "change_language":
        new_lang = "en" if chat_config["language"] == "he" else "he"
        chat_config["language"] = new_lang
        save_data()
    elif data_cb == "change_warn_limit":
        new_limit = 2 if chat_config["warn_limit"] == 3 else 3
        chat_config["warn_limit"] = new_limit
        save_data()
    elif data_cb == "toggle_service_msgs":
        chat_config["service_msgs"] = not chat_config.get("service_msgs", True)
        save_data()
    elif data_cb == "change_links_action":
        current = chat_config.get("links_action", "delete")
        if current == "delete":
            new_action = "warn"
        elif current == "warn":
            new_action = "kick"
        else:
            new_action = "delete"
        chat_config["links_action"] = new_action
        save_data()
    text, reply_markup = build_settings(chat_config)
    query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    log_action(update, f"Updated setting via callback: {data_cb}")

def cancel_warn_callback(update, context):
    query = update.callback_query
    user = update.effective_user
    if not is_user_admin(update, user.id) and not update.effective_message.sender_chat:
        query.answer("פונקציה זו זמינה רק למנהלים.", show_alert=True)
        return
    query.answer()
    try:
        _, chat_id, target_id = query.data.split(":")
        chat_config = get_chat_config(chat_id)
        warns_dict = chat_config.get("warns", {})
        user_warns = warns_dict.get(str(target_id), [])
        if not user_warns:
            new_text = "אין אזהרות להסרה."
        else:
            user_warns.pop()
            warns_dict[str(target_id)] = user_warns
            chat_config["warns"] = warns_dict
            save_data()
            new_text = (
                f"המנהל <a href=\"tg://user?id={user.id}\">{user.first_name}</a> הסיר אזהרה מהמשתמש "
                f"<a href=\"tg://user?id={target_id}\">?</a>.\n"
                f"כרגע יש לו <b>{len(user_warns)}</b> מתוך <b>{chat_config.get('warn_limit', 3)}</b>."
            )
        query.edit_message_text(new_text, parse_mode=ParseMode.HTML)
        log_action(update, f"Canceled warning for user: {target_id}")
    except Exception as e:
        logger.error(e)
        query.edit_message_text("אירעה שגיאה.")

def auth_callback(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text=get_language_text(update, "auth_success"))
    log_action(update, f"Anonymous admin authenticated: {update.effective_user.id}")

def new_member(update, context):
    chat = update.effective_chat
    chat_config = get_chat_config(chat.id)
    if chat_config["welcome"]["enabled"]:
        welcome_text = chat_config["welcome"]["message"]
        if not welcome_text:
            welcome_text = LANG[chat_config["language"]]["welcome_default"].format(
                id=update.effective_user.id, name=update.effective_user.first_name, group=chat.title
            )
        for member in update.message.new_chat_members:
            try:
                context.bot.send_message(chat_id=chat.id, text=welcome_text, parse_mode=ParseMode.HTML)
            except TelegramError as e:
                logger.error(e)

def message_filter(update, context):
    chat = update.effective_chat
    chat_config = get_chat_config(chat.id)
    filters_dict = chat_config.get("filters", {})
    msg_text = update.message.text
    if not msg_text:
        return
    text_lower = msg_text.lower()
    for key, response in filters_dict.items():
        if key in text_lower:
            update.message.reply_html(response)
            break
