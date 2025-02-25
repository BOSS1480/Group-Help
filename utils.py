from telegram.ext import ContextTypes

def check_admin(update, context):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    admins = context.bot.get_chat_administrators(chat_id)
    return any(admin.user.id == user_id for admin in admins)

def get_target_user(update, context):
    message = update.message
    if message.reply_to_message:
        return message.reply_to_message.from_user
    elif len(context.args) > 0:
        target = context.args[0]
        try:
            return context.bot.get_chat_member(update.effective_chat.id, int(target)).user
        except ValueError:
            return context.bot.get_chat_member(update.effective_chat.id, target).user
    return None

def is_anonymous_admin(update, context):
    member = context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status == "administrator" and member.user.is_anonymous
