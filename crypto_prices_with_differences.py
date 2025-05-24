import requests
import csv
from decimal import Decimal
from datetime import datetime

def fetch_prices_with_differences(input_file, output_file, datetime1, datetime2):
    # Read cryptocurrency tickers from the input file while preserving order and empty lines
    with open(input_file, "r") as file:
        lines = [line.strip() for line in file]  # Preserve original lines (including empty lines)

    # Convert datetime strings to timestamps
    dt_format = "%Y-%m-%d %H:%M:%S"
    timestamp1 = int(datetime.strptime(datetime1, dt_format).timestamp())
    timestamp2 = int(datetime.strptime(datetime2, dt_format).timestamp())

    # Fetch all Bybit trading pairs and their current prices
    bybit_url = "https://api.bybit.com/v5/market/tickers"
    bybit_params = {"category": "spot"}
    bybit_response = requests.get(bybit_url, params=bybit_params)
    bybit_response.raise_for_status()
    bybit_data = bybit_response.json()

    if bybit_data["retCode"] != 0:
        raise ValueError(f"Bybit API Error: {bybit_data['retMsg']}")

    bybit_prices = {
        item["symbol"]: Decimal(item["lastPrice"])
        for item in bybit_data["result"]["list"]
    }

    # Function to fetch historical price (replace this with an actual API if available)
    def fetch_historical_price(symbol, timestamp):
        # Placeholder: Replace with real API logic to fetch historical price
        url = f"https://api.bybit.com/v5/market/historical-prices"
        params = {"symbol": symbol, "timestamp": timestamp}
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if "price" in data:
                return Decimal(data["price"])
        return None  # Return None if the price could not be fetched

    # Create the output data
    output_data = []

    for line in lines:
        if not line:  # Handle empty lines
            output_data.append([])
        else:
            ticker = line.upper()
            symbol_usdt = f"{ticker}USDT"  # Format as trading pairs
            symbol_busd = f"{ticker}BUSD"  # Alternative stablecoin pair

            # Try to get current price from Bybit
            current_price = bybit_prices.get(symbol_usdt) or bybit_prices.get(symbol_busd)
            if not current_price:
                output_data.append([ticker, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
                continue

            # Fetch historical prices
            price_datetime1 = fetch_historical_price(symbol_usdt, timestamp1) or fetch_historical_price(symbol_busd, timestamp1)
            price_datetime2 = fetch_historical_price(symbol_usdt, timestamp2) or fetch_historical_price(symbol_busd, timestamp2)

            if price_datetime1 is None or price_datetime2 is None:
                output_data.append([ticker, current_price, "N/A", "N/A", "N/A", "N/A"])
                continue

            # Calculate percentage differences
            perc_diff1 = ((current_price - price_datetime1) / price_datetime1) * 100
            perc_diff2 = ((current_price - price_datetime2) / price_datetime2) * 100

            # Append data
            output_data.append([
                ticker,
                f"{price_datetime1:.6f}",
                f"{price_datetime2:.6f}",
                f"{current_price:.6f}",
                f"{perc_diff1:.2f}%",
                f"{perc_diff2:.2f}%"
            ])

    # Write the output data to a CSV file with tab delimiter
    with open(output_file, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter="\t")  # Tab as delimiter
        csvwriter.writerow(["Ticker", "Price (Datetime1)", "Price (Datetime2)", "Current Price", "Perc Diff (Current - Datetime1)", "Perc Diff (Current - Datetime2)"])
        for row in output_data:
            csvwriter.writerow(row)

    print(f"Prices with percentage differences exported to {output_file}")

# Input and output file paths
input_file = "crypto_historical_tickers.txt"  # New input file name for this script
output_file = "crypto_historical_prices_with_percentages.csv"  # Output file name

# Specify datetimes for comparison
datetime1 = "2024-11-01 12:00:00"  # Replace with your desired datetime1
datetime2 = "2024-11-15 12:00:00"  # Replace with your desired datetime2

fetch_prices_with_differences(input_file, output_file, datetime1, datetime2)
