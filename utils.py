# utils.py
import json
import os
import re
import time
import logging
from functools import wraps

from telegram import ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from messages import LANG

DATA_FILE = 'data.json'
data = {}

logger = logging.getLogger(__name__)

def load_data():
    global data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error("Error loading data: %s", e)
            data = {}
    else:
        data = {}

def save_data():
    global data
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error("Error saving data: %s", e)

def get_chat_config(chat_id):
    chat_id = str(chat_id)
    if chat_id not in data:
        data[chat_id] = {
            "language": "he",  # ברירת מחדל – עברית
            "warn_limit": 3,
            "warns": {},
            "filters": {},
            "welcome": {"enabled": False, "message": ""},
            "log_channel": None,
            "service_msgs": True,
            "links_action": "delete"
        }
        save_data()
    return data[chat_id]

def is_user_admin(update, user_id):
    try:
        member = update.effective_chat.get_member(user_id)
        return member.status in ['administrator', 'creator']
    except TelegramError as e:
        logger.error("Error checking admin status: %s", e)
        return False

def parse_duration(duration_str):
    match = re.match(r"(\d+)([smhd])", duration_str)
    if not match:
        return None
    amount, unit = match.groups()
    amount = int(amount)
    if unit == 's':
        return amount
    elif unit == 'm':
        return amount * 60
    elif unit == 'h':
        return amount * 3600
    elif unit == 'd':
        return amount * 86400
    return None

def get_target_user(update, context):
    msg = update.effective_message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            return context.bot.get_chat_member(update.effective_chat.id, user_id).user
        except ValueError:
            username = context.args[0].lstrip('@')
            for member in update.effective_chat.get_administrators():
                if member.user.username and member.user.username.lower() == username.lower():
                    return member.user
            return None
    else:
        return None

def get_language_text(update, key):
    chat_config = get_chat_config(update.effective_chat.id)
    lang = chat_config.get("language", "he")
    return LANG[lang].get(key, key)

def log_action(update, text):
    chat_config = get_chat_config(update.effective_chat.id)
    log_channel = chat_config.get("log_channel")
    if log_channel:
        try:
            update.bot.send_message(chat_id=log_channel, text=f"[Group {update.effective_chat.id}] {text}")
        except Exception as e:
            logger.error("Error logging action: %s", e)

# Restrict commands to groups only
def group_only(func):
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        if update.effective_chat.type == 'private':
            update.message.reply_text("פקודה זו עובדת רק בקבוצות.")
            return
        return func(update, context, *args, **kwargs)
    return wrapper

# admin_required – מאפשר גם למנהלים אנונימיים במקרים מיוחדים
def admin_required(func):
    @wraps(func)
    def wrapper(update, context, *args, **kwargs):
        user = update.effective_user
        if user is None or (getattr(user, 'is_anonymous', False) and user.id != 1087968824 and not update.effective_message.sender_chat):
            authenticate_admin(update, context)
            return
        if not is_user_admin(update, user.id) and not update.effective_message.sender_chat:
            update.message.reply_text(get_language_text(update, "not_admin"))
            return
        return func(update, context, *args, **kwargs)
    return wrapper

def authenticate_admin(update, context):
    keyboard = [[InlineKeyboardButton("Authenticate", callback_data="auth_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(get_language_text(update, "auth_request"), reply_markup=reply_markup)
