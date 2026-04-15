import ccxt
import time
import os
from dotenv import load_dotenv

load_dotenv()


def load_api_keys():
    """Load exchange API credentials from environment variables.

    All variables must be set before running this script — either as OS
    environment variables or in a .env file in the project root.
    See .env.example for the full list.
    """
    required = {
        "BINANCE_API_KEY": os.environ.get("BINANCE_API_KEY"),
        "BINANCE_SECRET": os.environ.get("BINANCE_SECRET"),
        "BYBIT_MAIN_API_KEY": os.environ.get("BYBIT_MAIN_API_KEY"),
        "BYBIT_MAIN_SECRET": os.environ.get("BYBIT_MAIN_SECRET"),
        "BYBIT_STRATEGICCHECK_API_KEY": os.environ.get("BYBIT_STRATEGICCHECK_API_KEY"),
        "BYBIT_STRATEGICCHECK_SECRET": os.environ.get("BYBIT_STRATEGICCHECK_SECRET"),
        "BYBIT_SCALPING_API_KEY": os.environ.get("BYBIT_SCALPING_API_KEY"),
        "BYBIT_SCALPING_SECRET": os.environ.get("BYBIT_SCALPING_SECRET"),
        "MEXC_API_KEY": os.environ.get("MEXC_API_KEY"),
        "MEXC_SECRET": os.environ.get("MEXC_SECRET"),
        "BITGET_API_KEY": os.environ.get("BITGET_API_KEY"),
        "BITGET_SECRET": os.environ.get("BITGET_SECRET"),
    }
    missing = [name for name, val in required.items() if not val]
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Copy .env.example to .env and fill in your credentials."
        )

    return {
        "binance": {
            "apiKey": required["BINANCE_API_KEY"],
            "secret": required["BINANCE_SECRET"],
        },
        "bybit": {
            "main": {
                "apiKey": required["BYBIT_MAIN_API_KEY"],
                "secret": required["BYBIT_MAIN_SECRET"],
            },
            "strategicCheck": {
                "apiKey": required["BYBIT_STRATEGICCHECK_API_KEY"],
                "secret": required["BYBIT_STRATEGICCHECK_SECRET"],
            },
            "scalping": {
                "apiKey": required["BYBIT_SCALPING_API_KEY"],
                "secret": required["BYBIT_SCALPING_SECRET"],
            },
        },
        "mexc": {
            "apiKey": required["MEXC_API_KEY"],
            "secret": required["MEXC_SECRET"],
        },
        "bitget": {
            "apiKey": required["BITGET_API_KEY"],
            "secret": required["BITGET_SECRET"],
        },
    }


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
    api_keys = load_api_keys()
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
