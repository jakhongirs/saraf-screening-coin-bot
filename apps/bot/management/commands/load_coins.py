from concurrent.futures import ThreadPoolExecutor

import requests
from django.core.management.base import BaseCommand

from apps.bot.models import Coin, CoinStatusChoices


class Command(BaseCommand):
    help = "Fetch coins from the API and save them to the database."

    def handle(self, *args, **kwargs):
        # Step 1: Get access token
        login_url = "https://sarafscreening.com/api/v1/users/Login/"
        login_data = {
            "device_id": "29987606-A84E-48D0-9E8B-1A7A9ACE8AA6",
            "email": "jakhongirsv@gmail.com",
            "password": "JYiYGpZx5xFtT9q",
        }
        response = requests.post(login_url, json=login_data)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR("Failed to obtain access token"))
            return

        access_token = response.json().get("access")
        if not access_token:
            self.stdout.write(self.style.ERROR("Access token not found in response"))
            return

        # Step 2: Fetch coins data with pagination
        coins_url = "https://sarafscreening.com/api/v1/main/CoinList/"
        headers = {"Authorization": f"Bearer {access_token}"}

        with ThreadPoolExecutor(max_workers=10) as executor:
            while coins_url:
                response = requests.get(coins_url, headers=headers)

                if response.status_code != 200:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to fetch coins from {coins_url}")
                    )
                    break

                data = response.json()

                # Process the 'results' field
                coins_data = data.get("results", [])

                # Concurrently handle each coin
                futures = [
                    executor.submit(self.process_coin, coin) for coin in coins_data
                ]

                # Ensure all futures complete
                for future in futures:
                    future.result()

                # Get the next page URL from the 'next' field
                coins_url = data.get("next")

        self.stdout.write(
            self.style.SUCCESS("Coins successfully fetched and saved to the database")
        )

    def process_coin(self, coin):
        name = coin.get("name")
        symbol = coin.get("symbol")
        status = coin.get("status", CoinStatusChoices.not_screened_yet)

        # Ensure the status is valid
        if status not in dict(CoinStatusChoices.choices):
            status = CoinStatusChoices.not_screened_yet

        # Fetch coins with the same symbol
        coins_with_symbol = Coin.objects.filter(symbol=symbol)

        if coins_with_symbol.exists():
            if coins_with_symbol.count() > 1:
                self.stdout.write(
                    f"Multiple entries found for Symbol={symbol}, skipping update."
                )
            else:
                # Update the existing entry if only one coin is found
                coin_entry = coins_with_symbol.first()
                coin_entry.name = name
                coin_entry.status = status
                coin_entry.save()
                self.stdout.write(
                    f"Updated existing coin: Name={name}, Symbol={symbol}, Status={status}"
                )
        else:
            # Create a new Coin entry if it doesn't exist
            Coin.objects.create(name=name, symbol=symbol, status=status)
            self.stdout.write(
                f"Loaded new coin: Name={name}, Symbol={symbol}, Status={status}"
            )
