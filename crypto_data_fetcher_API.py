import ccxt
import time
import json
import os


# Load API keys from an external JSON file
def load_api_keys(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"API keys file not found: {file_path}")
    with open(file_path, 'r') as file:
        return json.load(file)


# Initialize exchanges
def initialize_exchanges(api_keys):
    exchange_classes = {
        'binance': ccxt.binance,
        'bybit': ccxt.bybit,
        'mexc': ccxt.mexc,
        'bitget': ccxt.bitget,
    }
    exchanges = {}
    for name, keys in api_keys.items():
        if name == "bybit" and isinstance(keys, dict):  # Handle multiple ByBit accounts
            exchanges[name] = {}
            for account_name, account_keys in keys.items():
                exchange = exchange_classes[name]()
                exchange.apiKey = account_keys['apiKey']
                exchange.secret = account_keys['secret']
                exchanges[name][account_name] = exchange
        else:
            exchange = exchange_classes[name]()
            exchange.apiKey = keys['apiKey']
            exchange.secret = keys['secret']
            exchanges[name] = exchange
    return exchanges


# Fetch balances and calculate USDT value
def fetch_balances(exchange):
    try:
        balances = exchange.fetch_balance()
        total_usdt_value = 0
        for currency, data in balances['total'].items():
            if data > 0:
                ticker = f"{currency}/USDT"
                try:
                    price = exchange.fetch_ticker(ticker)['last']
                    value = data * price
                except Exception:
                    value = 0  # Handle currencies without USDT pairs
                total_usdt_value += value
        return total_usdt_value, balances['total']
    except Exception as e:
        print(f"Error fetching balances for {exchange.name}: {e}")
        return 0, {}


# Fetch trades from the last 7 days
def fetch_trades(exchange):
    try:
        one_week_ago = int(time.time() * 1000) - 7 * 24 * 60 * 60 * 1000
        markets = exchange.load_markets()
        trades = []
        for symbol in markets:
            try:
                trades += exchange.fetch_my_trades(symbol, since=one_week_ago)
            except Exception:
                continue
        return trades
    except Exception as e:
        print(f"Error fetching trades for {exchange.name}: {e}")
        return []


def main():
    api_keys_file = 'api_keys.json'
    api_keys = load_api_keys(api_keys_file)
    exchanges = initialize_exchanges(api_keys)

    for name, exchange in exchanges.items():
        print(f"\n=== {name.upper()} ===")

        if name == "bybit" and isinstance(exchange, dict):  # Handle multiple ByBit accounts
            for account_name, account_exchange in exchange.items():
                print(f"\n--- Account: {account_name} ---")

                # Fetch balances
                usdt_value, balances = fetch_balances(account_exchange)
                print(f"Total Value in USDT: {usdt_value}")
                print("Balances:", balances)

                # Fetch trades
                trades = fetch_trades(account_exchange)
                print(f"Trades in the last 7 days ({len(trades)} total):")
                for trade in trades:
                    print({
                        'symbol': trade['symbol'],
                        'price': trade['price'],
                        'amount': trade['amount'],
                        'timestamp': account_exchange.iso8601(trade['timestamp'])
                    })
        else:
            # Fetch balances
            usdt_value, balances = fetch_balances(exchange)
            print(f"Total Value in USDT: {usdt_value}")
            print("Balances:", balances)

            # Fetch trades
            trades = fetch_trades(exchange)
            print(f"Trades in the last 7 days ({len(trades)} total):")
            for trade in trades:
                print({
                    'symbol': trade['symbol'],
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'timestamp': exchange.iso8601(trade['timestamp'])
                })


if __name__ == "__main__":
    main()
