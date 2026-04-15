import os
import csv
import requests
from decimal import Decimal, InvalidOperation
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ========== Налаштування ==========
CMC_API_KEY = os.environ.get("CMC_API_KEY", "")  # set CMC_API_KEY in .env — see .env.example
NEW_TV_STYLE_OTHERS_TICKER = "OTHERSX10.D"  # назва нового індексу "все, крім ТОП-10"

MEXC_TICKER_URL = "https://api.mexc.com/api/v3/ticker/price"
BYBIT_TICKER_URL = "https://api.bybit.com/v5/market/tickers"
CMC_GLOBAL_URL  = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
CMC_LISTINGS_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
# ===================================

def read_last_run_date(path: str):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip() or None

def write_last_run_date(path: str, date_str: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(date_str)

def load_previous_data(output_file: str):
    prev = {}
    if not os.path.exists(output_file):
        return prev
    with open(output_file, "r", encoding="utf-8") as csvfile:
        r = csv.reader(csvfile, delimiter="\t")
        header = next(r, None)
        for row in r:
            if not row or len(row) < 5 or not (row[0].strip()):
                continue
            try:
                prev[row[0]] = {
                    "YestDayPrice": Decimal(row[1]) if row[1] != "N/A" else None,
                    "StartDayPrice": Decimal(row[2]) if row[2] != "N/A" else None,
                    "OldPrice": Decimal(row[3]) if row[3] != "N/A" else None,
                    "NewPrice": Decimal(row[4]) if row[4] != "N/A" else None,
                }
            except InvalidOperation:
                continue
    return prev

def fetch_mexc_prices():
    resp = requests.get(MEXC_TICKER_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return {item["symbol"]: Decimal(item["price"]) for item in data}

def fetch_bybit_prices():
    params = {"category": "spot"}
    resp = requests.get(BYBIT_TICKER_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if data.get("retCode") != 0:
        return {}
    return {item["symbol"]: Decimal(item["lastPrice"]) for item in data["result"]["list"]}

def fetch_cmc_global():
    """Повертає dict із глобальних метрик CMC або None"""
    if not CMC_API_KEY:
        return None
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    resp = requests.get(CMC_GLOBAL_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json().get("data", {})

def fetch_cmc_top_list(limit=10):
    """Повертає список топ-коінів (dict) за капіталізацією з їх market_cap у USD."""
    if not CMC_API_KEY:
        return []
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {
        "start": 1,
        "limit": limit,
        "sort": "market_cap",
        "convert": "USD",
    }
    resp = requests.get(CMC_LISTINGS_URL, headers=headers, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    return data

def fetch_cmc_dominance(cache: dict):
    """
    Заповнює cache['btc_dom'], cache['eth_dom'] (Decimal %) якщо ще не заповнено.
    """
    if cache.get("btc_dom") is not None and cache.get("eth_dom") is not None:
        return
    g = fetch_cmc_global()
    if not g:
        cache["btc_dom"] = None
        cache["eth_dom"] = None
        return
    btc = g.get("btc_dominance")
    eth = g.get("eth_dominance")
    try:
        cache["btc_dom"] = Decimal(str(btc)) if btc is not None else None
        cache["eth_dom"] = Decimal(str(eth)) if eth is not None else None
    except Exception:
        cache["btc_dom"] = None
        cache["eth_dom"] = None

def fetch_cmc_others_ex_top10_percent(cache: dict):
    """
    Рахує % частку ринку, що НЕ входить у ТОП-10 за капою.
    Використовує:
      - total_market_cap із global
      - суму market_cap ТОП-10 із listings/latest
    Повертає Decimal або None.
    Кешується в cache['others_ex_top10_pct'].
    """
    if cache.get("others_ex_top10_pct") is not None:
        return

    # Глобальні метрики (total market cap)
    g = fetch_cmc_global()
    if not g:
        cache["others_ex_top10_pct"] = None
        return

    total_cap = None
    try:
        total_cap = Decimal(str(g["quote"]["USD"]["total_market_cap"]))
    except Exception:
        cache["others_ex_top10_pct"] = None
        return

    # ТОП-10
    top_list = fetch_cmc_top_list(limit=10)
    try:
        top10_cap = Decimal("0")
        for c in top_list:
            mc = c.get("quote", {}).get("USD", {}).get("market_cap")
            if mc is not None:
                top10_cap += Decimal(str(mc))
    except Exception:
        cache["others_ex_top10_pct"] = None
        return

    if total_cap is None or total_cap == 0:
        cache["others_ex_top10_pct"] = None
        return

    others_pct = (Decimal("1") - (top10_cap / total_cap)) * Decimal("100")
    cache["others_ex_top10_pct"] = others_pct

def get_price_for_special_ticker(t: str,
                                 mexc_prices: dict,
                                 bybit_prices: dict,
                                 cmc_cache: dict):
    """
    Обробка спец-індексів і крос-пари:
      - BTC.D           -> домінування BTC (%)
      - OTHERS.D        -> 100 - BTC.d - ETH.d (%)
      - OTHERSX10.D     -> % ринку поза ТОП-10 (TV-стиль)
      - ETHBTC          -> ціна крос-пари
    """
    if t == "ETHBTC":
        return mexc_prices.get("ETHBTC") or bybit_prices.get("ETHBTC")

    if t == "BTC.D":
        fetch_cmc_dominance(cmc_cache)
        return cmc_cache.get("btc_dom")

    if t == "OTHERS.D":
        fetch_cmc_dominance(cmc_cache)
        btc = cmc_cache.get("btc_dom")
        eth = cmc_cache.get("eth_dom")
        if btc is None:
            return None
        return (Decimal("100") - btc - (eth or Decimal("0")))

    if t == NEW_TV_STYLE_OTHERS_TICKER:
        fetch_cmc_others_ex_top10_percent(cmc_cache)
        return cmc_cache.get("others_ex_top10_pct")

    return None

def get_price_for_ticker(ticker: str,
                         mexc_prices: dict,
                         bybit_prices: dict,
                         cmc_cache: dict):
    t = ticker.strip().upper()
    if not t:
        return None

    # Спецові тікери/індекси
    special = get_price_for_special_ticker(t, mexc_prices, bybit_prices, cmc_cache)
    if special is not None:
        return special

    # Звичайні монети -> USDT/BUSD
    for suffix in ("USDT", "BUSD"):
        sym = f"{t}{suffix}"
        price = mexc_prices.get(sym)
        if price is not None:
            return price
        price = bybit_prices.get(sym)
        if price is not None:
            return price

    return None

def fmt_price(v: Decimal | None):
    return f"{v:.6f}" if v is not None else "N/A"

def fmt_pct(v: Decimal | None):
    return f"{v:.2f}" if v is not None else "N/A"  # без символу %

def main():
    input_file = "crypto_tickers.txt"
    output_file = "fetch_crypto_prices.csv"
    last_run_file = "lastrundate.txt"

    # 1) список тікерів (зберігаємо порожні рядки)
    with open(input_file, "r", encoding="utf-8") as f:
        tickers_raw = [line.rstrip("\n") for line in f]

    # Fail fast if CMC tickers are requested but the API key is missing
    CMC_TICKERS = {"BTC.D", "ETH.D", "OTHERS.D", NEW_TV_STYLE_OTHERS_TICKER}
    active_tickers = {line.strip().upper() for line in tickers_raw if line.strip()}
    if active_tickers & CMC_TICKERS and not CMC_API_KEY:
        raise EnvironmentError(
            f"Ticker list includes CMC-backed indices {active_tickers & CMC_TICKERS} "
            "but CMC_API_KEY is not set.\n"
            "Add CMC_API_KEY to your .env file — see .env.example."
        )

    # 2) джерела цін
    mexc_prices = fetch_mexc_prices()
    bybit_prices = fetch_bybit_prices()
    cmc_cache = {}

    # 3) визначаємо перший запуск дня
    today_str = str(datetime.now().date())
    last_run_str = read_last_run_date(last_run_file)
    is_new_day = (last_run_str != today_str)

    # 4) читаємо попередні дані
    prev = load_previous_data(output_file)

    # 5) формуємо вихід
    rows = []
    for line in tickers_raw:
        if not line.strip():
            rows.append([])
            continue

        ticker = line.strip().upper()
        new_price = get_price_for_ticker(ticker, mexc_prices, bybit_prices, cmc_cache)

        if new_price is None:
            rows.append([ticker, "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])
            continue

        prev_row = prev.get(ticker, {})
        yest = prev_row.get("YestDayPrice")
        start = prev_row.get("StartDayPrice")
        oldp = prev_row.get("NewPrice")  # "OldPrice" = попередній NewPrice

        # Новий день: переносимо вчорашній Start у Yest, і фіксуємо новий Start
        if is_new_day:
            yest = prev_row.get("StartDayPrice")
            start = new_price
        else:
            if start is None:
                start = new_price

        if oldp is None:
            oldp = new_price

        price_diff = None
        if oldp and oldp != 0:
            price_diff = (new_price - oldp) * Decimal(100) / oldp

        curr_yest_diff = None
        if yest and yest != 0:
            curr_yest_diff = (new_price - yest) * Decimal(100) / yest

        rows.append([
            ticker,
            fmt_price(yest),
            fmt_price(start),
            fmt_price(oldp),
            fmt_price(new_price),
            fmt_pct(price_diff),
            fmt_pct(curr_yest_diff),
        ])

    # 6) запис TSV
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["Ticker", "YestDayPrice", "StartDayPrice", "OldPrice", "NewPrice", "PriceDiff", "CurrYestPriceDiff"])
        for r in rows:
            w.writerow(r)

    # 7) оновлюємо дату останнього запуску
    with open(last_run_file, "w", encoding="utf-8") as f:
        f.write(today_str)

if __name__ == "__main__":
    main()