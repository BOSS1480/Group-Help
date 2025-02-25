import os
import json
import uuid
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
    filters
)

# הגדרות
BOT_TOKEN = os.environ.get('BOT_TOKEN')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# טעינת שפות
LOCALES = {}
for lang_file in os.listdir('locales'):
    if lang_file.endswith('.json'):
        lang = lang_file.split('.')[0]
        with open(f'locales/{lang_file}', 'r', encoding='utf-8') as f:
            LOCALES[lang] = json.load(f)

# מאגר נתונים
GROUPS = {}

def get_msg(chat_id: int, key: str, **kwargs) -> str:
    lang = GROUPS.get(chat_id, {}).get('lang', 'en')
    return LOCALES[lang][key].format(**kwargs)

async def get_target(update: Update, context: CallbackContext) -> User | None:
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    if context.args:
        try:
            return await context.bot.get_chat_member(update.effective_chat.id, context.args[0])
        except:
            pass
    await update.message.reply_text(get_msg(update.effective_chat.id, 'user_required'))
    return None

async def is_admin(update: Update, context: CallbackContext) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    
    if user.username == 'GroupAnonymousBot':
        verification_id = str(uuid.uuid4())
        keyboard = [[InlineKeyboardButton(
            text=get_msg(chat.id, 'verification_required'),
            callback_data=f"verify_{verification_id}"
        )]]
        
        context.user_data['pending_verify'] = {
            'command': update.message.text,
            'chat_id': chat.id
        }
        
        await update.message.reply_text(
            get_msg(chat.id, 'verification_required'),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False
    
    member = await chat.get_member(user.id)
    return member.status in ['administrator', 'creator']

async def verify_admin(update: Update, context: CallbackContext):
    query = update.callback_query
    verification_id = query.data.split('_')[1]
    pending = context.user_data.get('pending_verify', {})
    
    if not pending or pending.get('chat_id') != query.message.chat_id:
        await query.answer("❌ Verification expired")
        return
    
    member = await context.bot.get_chat_member(pending['chat_id'], query.from_user.id)
    if member.status not in ['administrator', 'creator']:
        await query.answer("❌ Not an admin!")
        return
    
    await context.bot.send_message(
        chat_id=pending['chat_id'],
        text=pending['command']
    )
    await query.answer(get_msg(pending['chat_id'], 'verification_success'))
    del context.user_data['pending_verify']

async def kick_user(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    await update.effective_chat.ban_user(target.id)
    await update.message.reply_text(get_msg(update.effective_chat.id, 'kicked', user=target.mention_html()))

async def ban_user(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    await update.effective_chat.ban_user(target.id)
    await update.message.reply_text(get_msg(update.effective_chat.id, 'banned', user=target.mention_html()))

async def mute_user(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    time = int(context.args[0]) if context.args else 60
    await context.bot.restrict_chat_member(
        chat_id=update.effective_chat.id,
        user_id=target.id,
        permissions=ChatPermissions(
            can_send_messages=False,
            can_send_media_messages=False
        )
    )
    await update.message.reply_text(get_msg(update.effective_chat.id, 'muted', user=target.mention_html(), time=time))

async def warn_user(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    target = await get_target(update, context)
    if not target:
        return
    
    chat_id = update.effective_chat.id
    GROUPS.setdefault(chat_id, {}).setdefault('warns', {}).setdefault(target.id, [])
    GROUPS[chat_id]['warns'][target.id].append(update.message.date)
    
    max_warns = GROUPS[chat_id].get('max_warns', 3)
    if len(GROUPS[chat_id]['warns'][target.id]) >= max_warns:
        await update.effective_chat.ban_user(target.id)
        await update.message.reply_text(get_msg(chat_id, 'warn_limit', user=target.mention_html()))
        del GROUPS[chat_id]['warns'][target.id]
    else:
        await update.message.reply_text(get_msg(chat_id, 'warned', user=target.mention_html(),
                                            count=len(GROUPS[chat_id]['warns'][target.id]), max=max_warns))

async def message_filter(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    settings = GROUPS.get(chat_id, {})
    
    if settings.get('block_links', True):
        if any(entity.type in [MessageEntity.URL, MessageEntity.TEXT_LINK] for entity in update.message.entities or []):
            await update.message.delete()
            await update.message.reply_text(get_msg(chat_id, 'link_deleted'))
    
    if settings.get('block_forwards', True) and update.message.forward_from:
        await update.message.delete()
        await update.message.reply_text(get_msg(chat_id, 'forward_deleted'))

async def set_language(update: Update, context: CallbackContext):
    if not await is_admin(update, context):
        return
    
    lang = context.args[0].lower() if context.args else 'en'
    if lang not in LOCALES:
        await update.message.reply_text("❌ Supported languages: " + ", ".join(LOCALES.keys()))
        return
    
    GROUPS.setdefault(update.effective_chat.id, {})['lang'] = lang
    await update.message.reply_text(f"🌐 Language set to {lang.upper()}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # פקודות
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text(get_msg(u.effective_chat.id, 'start'))))
    app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text(get_msg(u.effective_chat.id, 'help'))))
    app.add_handler(CommandHandler("kick", kick_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("warn", warn_user))
    app.add_handler(CommandHandler("setlang", set_language))
    
    # אימות
    app.add_handler(CallbackQueryHandler(verify_admin, pattern=r"^verify_"))
    
    # סינון הודעות
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_filter))
    
    app.run_polling()

if __name__ == '__main__':
    main()
