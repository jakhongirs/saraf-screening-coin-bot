import logging

from django.core.management.base import BaseCommand
from telegram import Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from apps.bot.models import Coin

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7546345897:AAEGCiEUA4DfRi-i80aXSmvUS0ItPY-EGJ4"

telegram_group_chat_id = -1002234521267


# Status translation function
def translate_status(status):
    translations = {
        "compliant": "Joiz",
        "not_screened_yet": "Tekshirilmagan",
        "non_compliant": "Joiz emas",
        "doubtful": "Shubhali",
    }
    return translations.get(status, status)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Salom! Kripto aktivlar ma'lumotini qidirish uchun 'joizmi: btc' kabi xabar yuboring."
    )


def handle_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    message_text = update.message.text.lower().strip()

    # Log the group chat ID
    logger.info(f"Group chat ID where message was received: {chat_id}")

    # Check if the message starts with 'joizmi:'
    if message_text.startswith("joizmi:") and chat_id == telegram_group_chat_id:
        symbol = message_text.split("joizmi:")[1].strip()

        print(symbol)

        # Search for all coins by symbol
        coins = Coin.objects.filter(symbol__iexact=symbol)

        if coins.exists():
            # Create a response message for all matching coins
            response = "🔍 Topilgan kripto aktivlar:\n\n"
            for coin in coins:
                status_uzbek = translate_status(coin.status)
                response += (
                    f"💰 Kripto aktiv: {coin.name}\n"
                    f"📌 Belgisi: {coin.symbol}\n"
                    f"📊 Holat: {status_uzbek}\n"
                    "---------------------------------\n"
                )
        else:
            response = f"'{symbol}' belgisiga ega kripto aktiv topilmadi"

        update.message.reply_text(response)


class Command(BaseCommand):
    help = "Telegram botni ishga tushiradi"

    def handle(self, *args, **options):
        updater = Updater(TOKEN)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

        self.stdout.write("Botni ishga tushiraman...")
        updater.start_polling()
        updater.idle()
