import requests
import csv
import os
from decimal import Decimal, InvalidOperation
from datetime import datetime

def fetch_crypto_prices(input_file, output_file, last_run_date_file):
    # Read tickers from input file
    with open(input_file, "r") as file:
        tickers = [line.strip() for line in file]

    # Fetch current prices from MexC API
    mexc_url = "https://api.mexc.com/api/v3/ticker/price"
    response = requests.get(mexc_url)
    response.raise_for_status()
    data = response.json()

    # Create a dictionary of prices for quick lookup
    prices = {item["symbol"]: Decimal(item["price"]) for item in data}

    # Initialize previous data and determine if it's a new day
    previous_data = {}
    is_new_day = False
    today_date = datetime.now().date()

    # Read last run date from the 'lastrundate.txt' file
    if os.path.exists(last_run_date_file):
        with open(last_run_date_file, "r") as f:
            last_run_date = f.read().strip()
            # If the last run date is not today's date, treat it as a new day
            if last_run_date != str(today_date):
                is_new_day = True
    else:
        # If the file doesn't exist, treat it as the first run
        is_new_day = True

    # Read existing data from the output CSV file if it exists
    if os.path.exists(output_file):
        with open(output_file, "r") as csvfile:
            csvreader = csv.reader(csvfile, delimiter="\t")
            header = next(csvreader)
            for row in csvreader:
                # Skip empty rows
                if not row or len(row) < 5:
                    continue
                try:
                    previous_data[row[0]] = {
                        "YestDayPrice": Decimal(row[1]) if row[1] != "N/A" else None,
                        "StartDayPrice": Decimal(row[2]) if row[2] != "N/A" else None,
                        "OldPrice": Decimal(row[3]) if row[3] != "N/A" else None,
                        "NewPrice": Decimal(row[4]) if row[4] != "N/A" else None,
                    }
                except InvalidOperation:
                    print(f"Skipping invalid row: {row}")

    # Prepare to write new data to the output file
    output_data = []
    for ticker in tickers:
        if not ticker.strip():
            output_data.append([])
            continue

        symbol_usdt = f"{ticker}USDT"
        symbol_busd = f"{ticker}BUSD"

        # Get the current price for the ticker
        new_price = prices.get(symbol_usdt) or prices.get(symbol_busd)

        if new_price is None:
            output_data.append([ticker, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            continue

        prev = previous_data.get(ticker, {})
        yest_day_price = prev.get("YestDayPrice")
        start_day_price = prev.get("StartDayPrice") if not is_new_day else new_price
        old_price = prev.get("NewPrice", new_price)

        # Calculate price differences
        price_diff = 100 * ((new_price - old_price) / old_price) if old_price else None
        curr_yest_price_diff = (
            100 * ((new_price - yest_day_price) / yest_day_price)
            if yest_day_price
            else None
        )

        # If it's a new day, update the YestDayPrice with the StartDayPrice of the previous day
        if is_new_day:
            yest_day_price = prev.get("StartDayPrice")

        output_data.append([
            ticker,
            f"{yest_day_price:.6f}" if yest_day_price is not None else "N/A",
            f"{start_day_price:.6f}" if start_day_price is not None else "N/A",
            f"{old_price:.6f}" if old_price is not None else "N/A",
            f"{new_price:.6f}" if new_price is not None else "N/A",
            f"{price_diff:.2f}" if price_diff is not None else "N/A",
            f"{curr_yest_price_diff:.2f}" if curr_yest_price_diff is not None else "N/A",
        ])

    # Write the output data to the CSV file
    with open(output_file, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter="\t")
        csvwriter.writerow([
            "Ticker", "YestDayPrice", "StartDayPrice", "OldPrice", "NewPrice", "PriceDiff", "CurrYestPriceDiff", today_date
        ])
        for row in output_data:
            csvwriter.writerow(row)

    # Update the last run date file
    with open(last_run_date_file, "w") as f:
        f.write(str(today_date))

input_file = "crypto_tickers.txt"
output_file = "fetch_crypto_prices.csv"
last_run_date_file = "lastrundate.txt"
fetch_crypto_prices(input_file, output_file, last_run_date_file)
