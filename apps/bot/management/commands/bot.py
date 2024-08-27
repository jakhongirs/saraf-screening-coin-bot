import logging

from django.core.management.base import BaseCommand
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import CallbackContext, CommandHandler, InlineQueryHandler, Updater

from apps.bot.models import Coin

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7546345897:AAEGCiEUA4DfRi-i80aXSmvUS0ItPY-EGJ4"


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Hello! I can help you search for coins. Use inline mode to search by symbol."
    )


def inline_search(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query
    if not query:
        return

    results = []
    coins = Coin.objects.filter(symbol__icontains=query)[:50]

    for coin in coins:
        results.append(
            InlineQueryResultArticle(
                id=coin.id,
                title=coin.symbol,
                description=f"Name: {coin.name}, Status: {coin.get_status_display()}",
                input_message_content=InputTextMessageContent(
                    f"Coin: {coin.name} ({coin.symbol})\nStatus: {coin.get_status_display()}"
                ),
            )
        )

    update.inline_query.answer(results)


class Command(BaseCommand):
    help = "Runs the Telegram bot"

    def handle(self, *args, **options):
        updater = Updater(TOKEN)
        dp = updater.dispatcher

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(InlineQueryHandler(inline_search))

        self.stdout.write("Starting bot...")
        updater.start_polling()
        updater.idle()
