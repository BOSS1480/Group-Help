import os
import json
import logging
import re
from datetime import datetime, timedelta
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters,
    ConversationHandler
)

# ------ הגדרות בסיסיות ------
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ------ מאגרי נתונים ------
try:
    with open('data.json', 'r') as f:
        GROUPS = json.load(f)
except:
    GROUPS = {}

# ------ שפות ------
LOCALES = {}
for lang in ['he', 'en']:
    with open(f'locales/{lang}.json', 'r', encoding='utf-8') as f:
        LOCALES[lang] = json.load(f)

def save_data():
    with open('data.json', 'w') as f:
        json.dump(GROUPS, f)

def get_msg(chat_id: int, key: str, **kwargs) -> str:
    lang = GROUPS.get(str(chat_id), {}).get('lang', 'he')
    return LOCALES[lang][key].format(**kwargs)

# ------ פונקציות עזר ------
async def is_admin(update: Update, context: CallbackContext, user_id: int = None) -> bool:
    user = user_id or update.effective_user.id
    chat = update.effective_chat
    try:
        member = await chat.get_member(user)
        return member.status in ['administrator', 'creator']
    except:
        return False

async def get_target_user(update: Update) -> dict:
    if update.message.reply_to_message:
        return {
            'id': update.message.reply_to_message.from_user.id,
            'mention': update.message.reply_to_message.from_user.mention_html()
        }
    if context.args:
        try:
            user = await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
            return {
                'id': user.user.id,
                'mention': user.user.mention_html()
            }
        except:
            pass
    return None

# ------ ניהול משתמשים ------
async def ban_user(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    target = await get_target_user(update)
    if not target:
        await update.message.reply_text(get_msg(update.effective_chat.id, 'user_required'))
        return
    
    await context.bot.ban_chat_member(update.effective_chat.id, target['id'])
    await update.message.reply_text(get_msg(update.effective_chat.id, 'banned', user=target['mention']))

async def unban_user(update: Update, context: CallbackContext):
    target = await get_target_user(update)
    if not target:
        return
    
    await context.bot.unban_chat_member(update.effective_chat.id, target['id'])
    await update.message.reply_text(get_msg(update.effective_chat.id, 'unbanned', user=target['mention']))

# ------ מערכת אזהרות ------
async def warn_user(update: Update, context: CallbackContext):
    target = await get_target_user(update)
    if not target:
        return
    
    reason = ' '.join(context.args[1:]) if context.args else 'No reason provided'
    chat_id = str(update.effective_chat.id)
    
    GROUPS.setdefault(chat_id, {}).setdefault('warns', {}).setdefault(target['id'], []).append({
        'by': update.effective_user.id,
        'reason': reason,
        'time': datetime.now().isoformat()
    })
    
    max_warns = GROUPS[chat_id].get('max_warns', 3)
    if len(GROUPS[chat_id]['warns'][target['id']]) >= max_warns:
        action = GROUPS[chat_id].get('warn_action', 'kick')
        if action == 'kick':
            await context.bot.ban_chat_member(chat_id, target['id'])
        elif action == 'ban':
            await context.bot.ban_chat_member(chat_id, target['id'], until_date=datetime.now() + timedelta(days=365))
        
        await update.message.reply_text(get_msg(chat_id, 'warn_limit', user=target['mention']))
    
    save_data()

async def unwarn_user(update: Update, context: CallbackContext):
    target = await get_target_user(update)
    if not target or not GROUPS.get(str(update.effective_chat.id), {}).get('warns', {}).get(target['id']):
        await update.message.reply_text(get_msg(update.effective_chat.id, 'no_warns'))
        return
    
    GROUPS[str(update.effective_chat.id)]['warns'][target['id']].pop()
    await update.message.reply_text(get_msg(update.effective_chat.id, 'unwarned', user=target['mention']))
    save_data()

# ------ פילטרים ------
async def add_filter(update: Update, context: CallbackContext):
    if not update.message.reply_to_message:
        return
    
    trigger = ' '.join(context.args)
    response = update.message.reply_to_message.text or update.message.reply_to_message.caption
    
    GROUPS.setdefault(str(update.effective_chat.id), {}).setdefault('filters', {})[trigger] = response
    await update.message.reply_text(get_msg(update.effective_chat.id, 'filter_added'))
    save_data()

async def handle_filters(update: Update, context: CallbackContext):
    text = update.message.text or update.message.caption
    if not text:
        return
    
    chat_id = str(update.effective_chat.id)
    for trigger, response in GROUPS.get(chat_id, {}).get('filters', {}).items():
        if trigger.lower() in text.lower():
            await update.message.reply_text(response)
            break

# ------ הגדרות ------
async def settings_menu(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("🌐 שפה", callback_data="lang"),
         InlineKeyboardButton("⚠️ אזהרות", callback_data="warns")],
        [InlineKeyboardButton("🔗 קישורים", callback_data="links"),
         InlineKeyboardButton("👋 ברוכים הבאים", callback_data="welcome")]
    ]
    await update.message.reply_text("⚙️ הגדרות קבוצה:", reply_markup=InlineKeyboardMarkup(keyboard))
    return 'settings'

async def settings_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    # הוסף לוגיקה להגדרות כאן
    await query.answer("הגדרה עודכנה!")
    return ConversationHandler.END

# ------ הרצת הבוט ------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # רישום פקודות
    commands = [
        ('start', lambda u,c: u.message.reply_text(get_msg(u.effective_chat.id, 'start'))),
        ('help', lambda u,c: u.message.reply_text(get_msg(u.effective_chat.id, 'help'))),
        ('ban', ban_user),
        ('unban', unban_user),
        ('warn', warn_user),
        ('unwarn', unwarn_user),
        ('kick', kick_user),
        ('mute', mute_user),
        ('unmute', unmute_user),
        ('filter', add_filter),
        ('stop', remove_filter),
        ('filters', list_filters),
        ('welcome', welcome_toggle),
        ('setwelcome', set_welcome),
        ('setlang', set_language),
        ('settings', settings_menu)
    ]
    
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))
    
    # הוספת האנדלרים הנוספים
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_filters))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("settings", settings_menu)],
        states={'settings': [CallbackQueryHandler(settings_callback)]},
        fallbacks=[]
    ))
    
    app.run_polling()

if __name__ == '__main__':
    main()
