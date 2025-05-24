import requests
import csv
from decimal import Decimal

def fetch_prices_bybit_and_mexc(input_file, output_file_full, output_file_prices):
    # Read cryptocurrency tickers from the input file while preserving order and empty lines
    with open(input_file, "r") as file:
        lines = [line.strip() for line in file]  # Preserve original lines (including empty lines)

    # Fetch all Bybit trading pairs and their prices
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

    # Fetch all MEXC trading pairs and their prices
    mexc_url = "https://api.mexc.com/api/v3/ticker/price"
    mexc_response = requests.get(mexc_url)
    mexc_response.raise_for_status()
    mexc_data = mexc_response.json()
    mexc_prices = {item["symbol"]: Decimal(item["price"]) for item in mexc_data}

    # Create the output data while preserving input order and empty lines
    output_data_full = []
    output_data_prices = []

    for line in lines:
        if not line:  # Handle empty lines
            output_data_full.append([])
            output_data_prices.append([])  # Leave empty for prices only output
        else:
            ticker = line.upper()
            symbol_usdt = f"{ticker}USDT"  # Format as trading pairs
            symbol_busd = f"{ticker}BUSD"  # Alternative stablecoin pair

            # Try to get price from Bybit first
            if symbol_usdt in bybit_prices:
                price = bybit_prices[symbol_usdt]
                formatted_price = format(price, "f")  # Convert to standard decimal format
                output_data_full.append([ticker, symbol_usdt, formatted_price])
                output_data_prices.append([formatted_price])
            elif symbol_busd in bybit_prices:
                price = bybit_prices[symbol_busd]
                formatted_price = format(price, "f")
                output_data_full.append([ticker, symbol_busd, formatted_price])
                output_data_prices.append([formatted_price])
            # Fallback to MEXC
            elif symbol_usdt in mexc_prices:
                price = mexc_prices[symbol_usdt]
                formatted_price = format(price, "f")
                output_data_full.append([ticker, symbol_usdt, formatted_price])
                output_data_prices.append([formatted_price])
            elif symbol_busd in mexc_prices:
                price = mexc_prices[symbol_busd]
                formatted_price = format(price, "f")
                output_data_full.append([ticker, symbol_busd, formatted_price])
                output_data_prices.append([formatted_price])
            else:
                output_data_full.append([ticker, "N/A", "Not Found"])
                output_data_prices.append([])  # Empty line for "not found" cases

    # Write the full data to a CSV file with tab delimiter
    with open(output_file_full, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter="\t")  # Tab as delimiter
        csvwriter.writerow(["Ticker", "Pair", "Price"])  # Header
        for row in output_data_full:
            csvwriter.writerow(row)

    # Write the prices only to a CSV file with tab delimiter
    with open(output_file_prices, "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter="\t")  # Tab as delimiter
        csvwriter.writerow(["Price"])  # Header
        for row in output_data_prices:
            if row:  # Only write a row if it's not empty
                csvwriter.writerow(row)
            else:
                csvfile.write("\n")  # Write an empty line for empty prices

    print(f"Crypto prices exported to {output_file_full} and {output_file_prices}")

# Input and output file paths
input_file = "fetch_crypto_tickers.txt"  # Update to your input file name
output_file_full = "synchronized_crypto_prices_with_tabs.csv"  # Full output file name
output_file_prices = "fetch_crypto_prices.csv"  # Prices only output file name

fetch_prices_bybit_and_mexc(input_file, output_file_full, output_file_prices)
