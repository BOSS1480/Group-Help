import os
import json
import logging
from telegram import (
    Update,
    User,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MessageEntity
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

# ----------------- הגדרות -----------------
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- מאגרי נתונים -----------------
LOCALES = {}
GROUPS = {}

# ----------------- מצבים -----------------
SETTINGS, SET_LANG, SET_MAX_WARNS, SET_LINK_ACTION, SET_WARN_ACTION = range(5)

# ----------------- טעינת שפות -----------------
for lang_file in os.listdir('locales'):
    if lang_file.endswith('.json'):
        lang = lang_file.split('.')[0]
        with open(f'locales/{lang_file}', 'r', encoding='utf-8') as f:
            LOCALES[lang] = json.load(f)

def get_msg(chat_id: int, key: str, **kwargs) -> str:
    lang = GROUPS.get(chat_id, {}).get('lang', 'he')
    return LOCALES[lang][key].format(**kwargs)

# ----------------- פונקציות עזר -----------------
async def is_admin(update: Update, context: CallbackContext) -> bool:
    user = update.effective_user
    if user.username == 'GroupAnonymousBot':
        return await verify_anonymous_admin(update, context)
    try:
        member = await update.effective_chat.get_member(user.id)
        return member.status in ['administrator', 'creator']
    except:
        return False

async def verify_anonymous_admin(update: Update, context: CallbackContext) -> bool:
    verification_id = str(uUID.uuid4())
    keyboard = [[InlineKeyboardButton(
        text=get_msg(update.effective_chat.id, 'verify_button'),
        callback_data=f"auth_{verification_id}"
    )]]
    
    context.user_data['pending_auth'] = {
        'command': update.message.text,
        'chat_id': update.effective_chat.id
    }
    
    await update.message.reply_text(
        get_msg(update.effective_chat.id, 'verification_required'),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return False

# ----------------- ניהול משתמשים -----------------
async def kick_user(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else None
    if not target:
        await update.message.reply_text(get_msg(update.effective_chat.id, 'user_required'))
        return
    
    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_text(get_msg(update.effective_chat.id, 'kicked', user=target.mention_html()))

async def ban_user(update: Update, context: CallbackContext):
    # דומה ל-kick עם הרשאות תמידיות

async def unban_user(update: Update, context: CallbackContext):
    target = await get_target_user(update)
    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    await update.message.reply_text(get_msg(update.effective_chat.id, 'unbanned', user=target.mention_html()))

async def mute_user(update: Update, context: CallbackContext):
    time = int(context.args[0]) if context.args else 1440  # ברירת מחדל 24 שעות
    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_media_messages=False,
        can_send_other_messages=False
    )
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions)
    await update.message.reply_text(get_msg(update.effective_chat.id, 'muted', user=target.mention_html(), time=time))

async def unmute_user(update: Update, context: CallbackContext):
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True
    )
    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, permissions)
    await update.message.reply_text(get_msg(update.effective_chat.id, 'unmuted', user=target.mention_html()))

# ----------------- מערכת פילטרים -----------------
async def add_filter(update: Update, context: CallbackContext):
    word = ' '.join(context.args).lower()
    GROUPS.setdefault(update.effective_chat.id, {}).setdefault('filters', []).append(word)
    await update.message.reply_text(f"✅ המילה '{word}' נוספה לפילטר")

async def remove_filter(update: Update, context: CallbackContext):
    word = ' '.join(context.args).lower()
    if word in GROUPS.get(update.effective_chat.id, {}).get('filters', []):
        GROUPS[update.effective_chat.id]['filters'].remove(word)
        await update.message.reply_text(f"✅ המילה '{word}' הוסרה מהפילטר")

async def check_filters(update: Update, context: CallbackContext):
    text = update.message.text.lower()
    filters = GROUPS.get(update.effective_chat.id, {}).get('filters', [])
    for word in filters:
        if word in text:
            await update.message.delete()
            await update.message.reply_text(
                get_msg(update.effective_chat.id, 'filter_violation', user=update.effective_user.mention_html())
            )

# ----------------- הודעות ברוכים הבאים -----------------
async def welcome_new_member(update: Update, context: CallbackContext):
    for member in update.message.new_chat_members:
        welcome_text = GROUPS.get(update.effective_chat.id, {}).get('welcome_msg', 'ברוך הבא!')
        await update.message.reply_text(welcome_text.format(user=member.mention_html()))

async def set_welcome(update: Update, context: CallbackContext):
    welcome_msg = ' '.join(context.args)
    GROUPS.setdefault(update.effective_chat.id, {})['welcome_msg'] = welcome_msg
    await update.message.reply_text("✅ הודעת הברכה עודכנה!")

# ----------------- מערכת הגדרות -----------------
async def group_settings(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    settings = GROUPS.get(chat_id, {})
    
    text = get_msg(chat_id, 'settings').format(
        max_warns=settings.get('max_warns', 3),
        link_action=settings.get('link_action', 'delete'),
        warn_action=settings.get('warn_action', 'kick'),
        filters_count=len(settings.get('filters', []))
    )
    
    keyboard = [
        [InlineKeyboardButton("✏️ מקסימום אזהרות", callback_data='set_max_warns'),
         InlineKeyboardButton("🔗 פעולת קישורים", callback_data='set_link_action')],
        [InlineKeyboardButton("⚠️ פעולת אזהרות", callback_data='set_warn_action'),
         InlineKeyboardButton("🗑️ ניהול פילטרים", callback_data='manage_filters')]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return SETTINGS

# ----------------- הרצת הבוט -----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # רישום כל הפקודות
    commands = [
        ('start', lambda u,c: u.message.reply_text(get_msg(u.effective_chat.id, 'start'))),
        ('help', lambda u,c: u.message.reply_text(get_msg(u.effective_chat.id, 'help'))),
        ('kick', kick_user),
        ('ban', ban_user),
        ('unban', unban_user),
        ('mute', mute_user),
        ('unmute', unmute_user),
        ('warn', warn_user),
        ('addfilter', add_filter),
        ('delfilter', remove_filter),
        ('setwelcome', set_welcome),
        ('settings', group_settings),
        ('setlang', set_language)
    ]
    
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))
    
    # הוספת כל האנדלרים הנוספים
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_filters))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern=r"^auth_"))
    
    app.run_polling()

if __name__ == '__main__':
    main()
