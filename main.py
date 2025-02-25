import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from commands import *
from filters import *
from language import set_language, get_message
from settings import settings_menu, handle_settings_input, button_handler
from database import init_db

# החלף בטוקן האמיתי של הבוט שלך
TOKEN = "7523206004:AAEA0sANMSyGBYoGxAG1ixHO3wqW-Y7V4iE"

def main():
    # אתחול מסד הנתונים
    init_db()

    # הגדרת הבוט
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # פקודות בסיסיות
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("setlang", set_language))

    # פקודות ניהול
    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(CommandHandler("unban", unban))
    dp.add_handler(CommandHandler("kick", kick))
    dp.add_handler(CommandHandler("mute", mute))
    dp.add_handler(CommandHandler("unmute", unmute))
    dp.add_handler(CommandHandler("warn", warn))
    dp.add_handler(CommandHandler("unwarn", unwarn))
    dp.add_handler(CommandHandler("warns", warns))

    # פקודות פילטרים וברוכים הבאים
    dp.add_handler(CommandHandler("filter", add_filter))
    dp.add_handler(CommandHandler("stop", remove_filter))
    dp.add_handler(CommandHandler("filters", list_filters))
    dp.add_handler(CommandHandler("welcome", set_welcome))
    dp.add_handler(CommandHandler("setwelcome", set_welcome_message))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_filters_and_welcome))

    # הגדרות וכפתורים
    dp.add_handler(CommandHandler("settings", settings_menu))
    dp.add_handler(CallbackQueryHandler(button_handler))

    # טיפול בהודעות עבור הגדרות
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_settings_input))

    # הרצה ב-Koyeb
    port = int(os.environ.get("PORT", 8000))
    updater.start_webhook(listen="0.0.0.0", port=port, url_path=TOKEN)
    updater.bot.setWebhook(f"https://group-help.koyeb.app/{TOKEN}")
    updater.idle()

if __name__ == "__main__":
    main()
