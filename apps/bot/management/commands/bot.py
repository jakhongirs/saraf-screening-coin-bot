import json
import logging
import re
import subprocess
from datetime import datetime

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
            curl_command = [
                "curl",
                f"https://api.nasdaq.com/api/calendar/earnings?date={date}",
                "-H",
                "accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "-H",
                "accept-language: en,ru-RU;q=0.9,ru;q=0.8,en-US;q=0.7",
                "-H",
                "cache-control: max-age=0",
                "-H",
                "cookie: akaalb_ALB_Default=~op=ao_api__east1:ao_api_east1|~rv=38~m=ao_api_east1:0|~os=ff51b6e767de05e2054c5c99e232919a~id=96e710ab586a53cc094690246eb821ad; permutive-id=e3a7d3ee-7064-407c-ab1a-42296e3b7e12; _sharedid=eff7348e-45c8-4b50-8224-3aa316670eca; _sharedid_cst=zix7LPQsHA%3D%3D; _biz_uid=f17bd305e7ab4844c1b80013e1907576; cto_bundle=WIPKL183RjVnMGFQU1JlZyUyQjFoaCUyQkVjUXFGekZMVmhENkZjUkpWWGxuT2doYWpNREVqR0NncmZvVDhoVDVFdUNsUDlCTmVwNnA1Q2I0cGtYQ1I1VU91Z0lRZUZNZ0JCcmVsRmhyaHA3bUZZTUZwUW1hR2xWRThPQWRVJTJCZmV2TlZ4QjJlZktPMExUWVdEN2clMkY3bk5La05WJTJCQm1RUld6ZVhYc2FjTkNFUmRmSUpRUkU1NkRmQkx0enV6WkliamVYbnh4Z1k5; cto_bidid=BkyB4l9XZ3VBUG5Od3JQRCUyQmV1dTllanFzSWdGWE9PS3gxNnZBdVdrYVVZRjd1UDdhSUlVcVJUbW00WFQ3dEtYTlppaUdONTg3dDNBSklJaDN5enlacnVzZHJlRWVsWlUxd2xHVGZ1RDFuODNINWRPUE8xTG5ERm95c211RlR0TkR1UzJyekNzT3RlRDJ2bXVuTnIlMkZMSXMySlFnJTNEJTNE; OTGPPConsent=DBABLA~BVQqAAAACgA.QA; OptanonAlertBoxClosed=2025-01-13T10:31:00.333Z; kndctr_1C1E66D861D6D1480A495C0F_AdobeOrg_consent=general=in; AMCV_1C1E66D861D6D1480A495C0F%40AdobeOrg=MCMID|81104955412846813304085834382039262943; acquiring_page=/market-activity/earnings; acquring_page=/market-activity/earnings; _biz_flagsA=%7B%22Version%22%3A1%2C%22ViewThrough%22%3A%221%22%2C%22XDomain%22%3A%221%22%2C%22Ecid%22%3A%22-1182238534%22%7D; _ga=GA1.1.1700758612.1736764264; _gcl_au=1.1.77088233.1736764267; _fbp=fb.1.1736764273719.480913550117440249; entryUrl=https://www.nasdaq.com/market-activity/earnings; entryReferringURL=https://www.google.com/; kndctr_1C1E66D861D6D1480A495C0F_AdobeOrg_cluster=irl1; kndctr_1C1E66D861D6D1480A495C0F_AdobeOrg_identity=CiY4MTEwNDk1NTQxMjg0NjgxMzMwNDA4NTgzNDM4MjAzOTI2Mjk0M1IQCPn%5F3fnFMhgBKgNPUjIwAfABiYX7zMYy; AKA_A2=A; _ga_BKF79YTM46=GS1.1.1736938830.2.0.1736938830.60.0.0; _ga_BJE6J0090G=GS1.1.1736938830.2.0.1736938830.60.0.0; _biz_nA=6; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Jan+15+2025+16%3A00%3A37+GMT%2B0500+(Uzbekistan+Standard+Time)&version=202410.1.0&browserGpcFlag=0&isIABGlobal=false&hosts=&landingPath=NotLandingPage&GPPCookiesCount=1&groups=C0003%3A1%2CC0002%3A1%2CC0001%3A1%2CC0004%3A1%2COSSTA_BG%3A1&geolocation=UZ%3BTK&AwaitingReconsent=false; tr_jt_okta=; _ga_FEJP7LTC1E=GS1.1.1736938806.3.1.1736938841.0.0.0; _ga_4VZJSZ76VC=GS1.1.1736938806.3.1.1736938843.23.0.0; _biz_pendingA=%5B%5D; FCNEC=%5B%5B%22AKsRol_My9f6P9gPwUzGC2xrx72pXKmIrF8ovz8VyO8CB5UILImV21CpM26JALLtjbUJTUWg4jq4Riz18GhTP48AQ2BNCYZOuMCEXJO0ddcat1MlM_8iWznBmxzrTBdt-ZcM5RRSsO8ZXC36SjwykHC-2FcZKzdUOA%3D%3D%22%5D%5D; _rdt_uuid=1736764273004.3a6d5089-5570-42cf-9da8-11bbb6b72ccd; _rdt_em=0000000000000000000000000000000000000000000000000000000000000001; bm_sv=D41526B7BA31775D271B92995FEEDD56~YAAQkwNJF5ky9WeUAQAAYaCfaRoWWdQ1V7oOPZ9T83Wf0vUzc/vKrypGNjYuM9l2MiJA8FUyo59Lc/HhdYPE6wZMfVJ2hE9COlSeXhs+jfHboXbG+loY4nVyZD//XFtpD20mvTIA0ogq6zEZ+c/AEnZpkeyyXFWFZPsPtIlHyM37XF8RTeXbHnr5/b/h7rI+RR3LabvXATj+yAqRsSNAhRppMjHxIggVgV7168haQtbM3JWkYb+A3mVkBrXNkDcpuw==~1",
                "-H",
                "priority: u=0, i",
                "-H",
                'sec-ch-ua: "Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "-H",
                "sec-ch-ua-mobile: ?0",
                "-H",
                'sec-ch-ua-platform: "macOS"',
                "-H",
                "sec-fetch-dest: document",
                "-H",
                "sec-fetch-mode: navigate",
                "-H",
                "sec-fetch-site: none",
                "-H",
                "sec-fetch-user: ?1",
                "-H",
                "upgrade-insecure-requests: 1",
                "-H",
                "user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            ]

            try:
                result = subprocess.run(
                    curl_command,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(f"Curl command failed: {result.stderr}")
                    raise RuntimeError("Failed to fetch data with curl")

                data = json.loads(result.stdout)
                rows = data.get("data", {}).get("rows", [])
                symbols = [
                    {
                        "symbol": item["symbol"],
                        "name": item["name"],
                        "time": item["time"],
                    }
                    for item in rows
                ]

                for item in symbols:
                    symbol, created = Symbol.objects.get_or_create(
                        symbol=item["symbol"], defaults={"name": item["name"]}
                    )
                    EarningsData.objects.create(
                        date=date, symbol=symbol, time=item["time"]
                    )

                return symbols

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise
            except subprocess.TimeoutExpired as e:
                logger.error(f"Curl command timed out: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise

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
