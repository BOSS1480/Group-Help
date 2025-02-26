# bot.py
import os
import logging
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

from utils import load_data
import commands

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    load_data()
    TOKEN = "7523206004:AAEA0sANMSyGBYoGxAG1ixHO3wqW-Y7V4iE"
    if not TOKEN:
        logger.error("BOT_TOKEN environment variable not set")
        return

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Command handlers
    dp.add_handler(CommandHandler("start", commands.start))
    dp.add_handler(CommandHandler("help", commands.help_command))
    dp.add_handler(CommandHandler("ban", commands.ban, pass_args=True))
    dp.add_handler(CommandHandler("unban", commands.unban, pass_args=True))
    dp.add_handler(CommandHandler("kick", commands.kick, pass_args=True))
    dp.add_handler(CommandHandler("mute", commands.mute, pass_args=True))
    dp.add_handler(CommandHandler("unmute", commands.unmute, pass_args=True))
    dp.add_handler(CommandHandler("warn", commands.warn, pass_args=True))
    dp.add_handler(CommandHandler("unwarn", commands.unwarn, pass_args=True))
    dp.add_handler(CommandHandler("warns", commands.warns_command, pass_args=True))
    dp.add_handler(CommandHandler("filter", commands.add_filter, pass_args=True))
    dp.add_handler(CommandHandler("stop", commands.remove_filter, pass_args=True))
    dp.add_handler(CommandHandler("filters", commands.list_filters))
    dp.add_handler(CommandHandler("welcome", commands.toggle_welcome, pass_args=True))
    dp.add_handler(CommandHandler("setwelcome", commands.set_welcome_message))
    dp.add_handler(CommandHandler("setlang", commands.set_language, pass_args=True))
    dp.add_handler(CommandHandler("settings", commands.settings))
    
    # CallbackQuery handlers
    dp.add_handler(CallbackQueryHandler(commands.main_menu_callback, pattern="^(show_help|back_to_start|auth_admin)$"))
    dp.add_handler(CallbackQueryHandler(commands.settings_callback, pattern="^(change_|toggle_)"))
    dp.add_handler(CallbackQueryHandler(commands.cancel_warn_callback, pattern="^cancel_warn:"))
    
    # New member handler
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, commands.new_member))
    # Message filter handler
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, commands.message_filter))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
