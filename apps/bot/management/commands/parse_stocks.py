import requests
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.bot.models import Symbol


class Command(BaseCommand):
    help = "Fetch and parse stock data from the API"

    def handle(self, *args, **options):
        print("Starting to fetch and update symbols...")
        self.fetch_and_update_symbols()
        print("Completed fetching and updating symbols.")

    def fetch_and_update_symbols(self):
        base_url = "https://h3ques1ic9vt6z4rp-1.a1.typesense.net/collections/stocks_data/documents/search"
        headers = {
            "accept": "application/json",
            "accept-language": "ru",
            "authorization": "Bearer 904971|8BQ8cuLlmokrZ33faOE7jo9AUCAQBAh4zrCpRdYafab26497",
            "content-type": "application/json",
            "origin": "https://musaffa.com",
            "priority": "u=1, i",
            "referer": "https://musaffa.com/",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "user-timezone-offset": "300",
            "x-typesense-api-key": "NHAYhtkThbpAtxpBemD4AKPc9loguxqT",
        }

        params = {
            "page": 1,
            "per_page": 15,
            "q": "*",
            "filter_by": "status:=PUBLISH&&isMainTicker:=1&&country:=US&&exchange:[`NYSE`,`NASDAQ`]&&musaffaHalalRating:[`COMPLIANT`,`NON_COMPLIANT`,`QUESTIONABLE`]",
            "sort_by": "usdMarketCap:desc",
        }

        while True:
            print(f"Fetching data for page {params['page']}...")
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            hits = data.get("hits", [])

            if not hits:
                print("No more data to fetch. Exiting loop.")
                break

            print(f"Processing {len(hits)} records from page {params['page']}...")
            with transaction.atomic():
                for hit in hits:
                    document = hit.get("document", {})
                    symbol = document.get("company_symbol")
                    shariah_status = document.get("musaffaHalalRating", "UNKNOWN")

                    if symbol:
                        obj, created = Symbol.objects.get_or_create(
                            symbol=symbol,
                            defaults={
                                "shariah_status": shariah_status,
                            },
                        )

                        if created:
                            print(
                                f"Created new Symbol: {symbol} with status {shariah_status}"
                            )
                        else:
                            obj.shariah_status = shariah_status
                            obj.save()
                            print(
                                f"Updated existing Symbol: {symbol} with new status {shariah_status}"
                            )

            # Move to the next page
            if "page" in params:
                params["page"] += 1
            else:
                break
