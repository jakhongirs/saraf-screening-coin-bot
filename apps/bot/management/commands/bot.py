import logging
import re
from datetime import datetime

import httpx
import requests
from django.core.management.base import BaseCommand
from telegram import ParseMode, Update
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from apps.bot.models import Coin, EarningsData, Symbol

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "7546345897:AAEGCiEUA4DfRi-i80aXSmvUS0ItPY-EGJ4"
GROUP_CHAT_ID = -1002234521267


def translate_status(status):
    translations = {
        "compliant": "Joiz",
        "not_screened_yet": "Tekshirilmagan",
        "non_compliant": "Joiz emas",
        "doubtful": "Shubhali",
    }
    return translations.get(status, status)


class Command(BaseCommand):
    help = "Combined bot for coin and stock compliance checks"

    def handle(self, *args, **kwargs):
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher

        def start(update: Update, context: CallbackContext) -> None:
            update.message.reply_text(
                "Salom! Quyidagi buyruqlarni ishlating:\n"
                "- Kripto statusini qidirish: 'joizmi: BTC'\n"
                "- Aksiya earnings tarixini qidirish: 'joizmi aksiya: YYYY-MM-DD'\n"
                "- Aksiyalarni qidirish: 'joizmi aksiya: AAPL'"
            )

        def handle_message(update: Update, context: CallbackContext) -> None:
            if not update.message:
                logger.warning("Received an update without a message.")
                return

            chat_id = update.message.chat_id
            message_text = update.message.text.lower().strip()

            if chat_id != GROUP_CHAT_ID:
                update.message.reply_text(
                    "Bu bot faqat ruxsat berilgan guruhda ishlaydi."
                )
                return

            if message_text.startswith("joizmi:"):
                handle_coin_query(update, message_text.split("joizmi:")[1].strip())
            elif message_text.startswith("joizmi aksiya:"):
                query = message_text.split("joizmi aksiya:")[1].strip()
                if is_valid_date(query):
                    handle_earnings_by_date(update, query, context)
                else:
                    handle_stock_query(update, query)

        def handle_coin_query(update: Update, symbol: str) -> None:
            coins = Coin.objects.filter(symbol__iexact=symbol)
            if coins.exists():
                response = "🔍 Topilgan kripto aktivlar:\n\n"
                for coin in coins:
                    status_translated = translate_status(coin.status)
                    response += (
                        f"💰 Kripto aktiv: {coin.name}\n"
                        f"📌 Belgisi: {coin.symbol}\n"
                        f"📊 Holat: {status_translated}\n"
                        "---------------------------------\n"
                    )
            else:
                response = f"'{symbol}' belgisiga ega kripto aktiv topilmadi."
            update.message.reply_text(response)

        def handle_earnings_by_date(
            update: Update, date: str, context: CallbackContext
        ) -> None:
            user_date = date

            if is_weekend(user_date):
                update.message.reply_text(
                    "📅 Siz so'ragan sanada aksiya bozori ishlamaydi."
                )
                return

            context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action="typing"
            )

            earnings = get_earnings(user_date)

            if not earnings:
                symbols = []

                try:
                    symbols = fetch_symbols(user_date)
                except (requests.RequestException, ValueError, AttributeError) as e:
                    update.message.reply_text(
                        "Iltimos, qayta urinib ko'ring. Sanani qayta kiriting (YYYY-MM-DD):"
                    )
                    return

                statuses = {}
                for symbol in symbols:
                    try:
                        symbol_obj = Symbol.objects.get(symbol=symbol["symbol"])
                        earnings_data = EarningsData.objects.get(
                            date=user_date, symbol=symbol_obj
                        )
                        statuses[symbol["symbol"]] = (
                            symbol_obj.shariah_status,
                            earnings_data.time,
                        )
                    except Symbol.DoesNotExist:
                        statuses[symbol["symbol"]] = (
                            Symbol.UNKNOWN,
                            EarningsData.TIME_NOT_SUPPLIED,
                        )

                response = format_response(statuses)
            else:
                response = format_response(
                    {
                        e.symbol.symbol: (e.symbol.shariah_status, e.time)
                        for e in earnings
                    }
                )

            try:
                update.message.reply_text(response, parse_mode=ParseMode.HTML)
            except Exception as e:
                if "Message is too long" in str(e):
                    with open("result.txt", "w") as f:
                        f.write(response)
                    update.message.reply_document(document=open("result.txt", "rb"))

        def handle_stock_query(update: Update, symbol: str) -> None:
            """
            Handles stock queries by searching the Symbol model for the provided stock symbol.
            """
            status_translations = {
                Symbol.COMPLIANT: "Joiz",
                Symbol.NON_COMPLIANT: "Joiz emas",
                Symbol.QUESTIONABLE: "Shubhali",
                Symbol.UNKNOWN: "Tekshirilmagan",
            }

            stocks = Symbol.objects.filter(symbol__iexact=symbol)
            if stocks.exists():
                response = "🔍 Topilgan aksiyalar:\n\n"
                for stock in stocks:
                    translated_status = status_translations.get(
                        stock.shariah_status, "Noma'lum"
                    )
                    response += (
                        f"📌 Belgisi: {stock.symbol}\n"
                        f"📊 Holat: {translated_status}\n"
                        "---------------------------------\n"
                    )
            else:
                response = f"'{symbol}' belgisiga ega aksiya topilmadi."

            update.message.reply_text(response)

        def is_valid_date(date_str: str) -> bool:
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                return False
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
                return True
            except ValueError:
                return False

        def is_weekend(date_str: str) -> bool:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.weekday() >= 5

        def get_earnings(date: str) -> list:
            return EarningsData.objects.filter(date=date).select_related("symbol")

        def fetch_symbols(date: str) -> list:
            url = f"https://api.nasdaq.com/api/calendar/earnings?date={date}"
            headers = {"User-Agent": "Mozilla/5.0"}
            with httpx.Client(http2=True) as client:
                response = client.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json().get("data", {}).get("rows", [])
                symbols = [
                    {
                        "symbol": item["symbol"],
                        "name": item["name"],
                        "time": item["time"],
                    }
                    for item in data
                ]
                for item in symbols:
                    symbol, created = Symbol.objects.get_or_create(
                        symbol=item["symbol"], defaults={"name": item["name"]}
                    )
                    EarningsData.objects.create(
                        date=date, symbol=symbol, time=item["time"]
                    )
            return symbols

        def format_response(statuses: dict) -> str:
            status_icons = {
                Symbol.COMPLIANT: "✅",
                Symbol.NON_COMPLIANT: "❌",
                Symbol.QUESTIONABLE: "❓",
                Symbol.UNKNOWN: "❓",
            }
            status_labels = {
                Symbol.COMPLIANT: "Joiz",
                Symbol.NON_COMPLIANT: "Joiz emas",
                Symbol.QUESTIONABLE: "Shubhali",
                Symbol.UNKNOWN: "Tekshirilmagan",
            }
            time_icons = {
                EarningsData.TIME_PRE_MARKET: "☀️",
                EarningsData.TIME_NOT_SUPPLIED: "❔",
                EarningsData.TIME_AFTER_HOURS: "🌙",
            }
            time_labels = {
                EarningsData.TIME_PRE_MARKET: "Pre-Market",
                EarningsData.TIME_NOT_SUPPLIED: "Not Supplied",
                EarningsData.TIME_AFTER_HOURS: "After Hours",
            }

            # Header of the table
            response_lines = [
                "<b>Ticker</b>\t|\t<b>Status</b>\t|\t<b>Vaqt</b>",
                "----------------------------------------",
            ]

            # Formatting the response with tabs and spaces
            for symbol, (status, time) in statuses.items():
                status_icon = status_icons.get(status, "❔")
                status_label = status_labels.get(status, "Unknown")
                time_icon = time_icons.get(time, "❔")
                time_label = time_labels.get(time, "Not Supplied")

                response_lines.append(
                    f"<b>{symbol}</b>\t|\t{status_label} {status_icon}\t|\t{time_label} {time_icon}"
                )

            # Combine the response lines
            response = "\n".join(response_lines)
            return response

        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

        self.stdout.write("Botni ishga tushiraman...")
        updater.start_polling()
        updater.idle()
