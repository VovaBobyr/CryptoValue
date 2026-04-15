# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

A personal daily cryptocurrency price tracker. It fetches spot prices from MEXC (primary) and Bybit (fallback), computes percentage changes relative to three reference points (previous run, start of day, yesterday's open), and writes a tab-separated CSV for manual copy-paste into a personal spreadsheet (`statistics_template.csv`).

A second entry point (`fetch_crypto_prices_others.py`) extends this with CoinMarketCap-sourced indices: `BTC.D`, `ETH.D`, `OTHERS.D`, `OTHERSX10.D`.

A separate utility (`crypto_data_fetcher_API.py`) queries live exchange account balances and recent trade history via the CCXT library.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in real API keys
```

## Running the scripts

```bash
# Daily price fetch (primary, no API key needed)
python fetch_crypto_prices_others.py

# Daily price fetch (simpler version, no CMC indices)
python fetch_crypto_prices_current.py

# Exchange account balances + 7-day trade history (requires all exchange keys in .env)
python crypto_data_fetcher_API.py

# Historical price comparison (NOTE: historical fetch is unimplemented — always returns N/A)
python crypto_prices_with_differences.py
```

There is no test suite and no linter configured.

## Architecture

### State machine for daily price tracking

The core logic in both `fetch_crypto_prices_current.py` and `fetch_crypto_prices_others.py` maintains four price columns per ticker by comparing today's date against `lastrundate.txt`:

- **Same-day run**: `OldPrice` ← previous `NewPrice`; `StartDayPrice` and `YestDayPrice` preserved.
- **First run of a new day** (`is_new_day = True`): `YestDayPrice` ← previous `StartDayPrice`; `StartDayPrice` ← current price.

The output CSV (`fetch_crypto_prices.csv`) is both the state store (read at the start) and the output (overwritten at the end). Losing it resets all reference prices.

### Two entry points, one canonical script

`fetch_crypto_prices_others.py` is the current, more capable version. `fetch_crypto_prices_current.py` is an older subset — it lacks CMC indices and uses a function-attribute cache anti-pattern for Bybit prices. Prefer `_others` for any new work.

### Special tickers in `crypto_tickers.txt`

Four tickers are handled outside normal MEXC/Bybit lookup:

| Ticker | Source |
|---|---|
| `BTC.D` | CoinMarketCap global metrics (`btc_dominance`) |
| `ETH.D` | CoinMarketCap global metrics (`eth_dominance`) |
| `OTHERS.D` | 100 − BTC.D − ETH.D |
| `OTHERSX10.D` | (total_market_cap − top10_market_cap) / total_market_cap × 100 |

If any of these appear in the ticker list and `CMC_API_KEY` is unset, the script raises `EnvironmentError` at startup before making any network calls.

### Empty lines in ticker files are intentional

`crypto_tickers.txt` uses blank lines as visual separators, and the scripts preserve them as empty rows in the output CSV. This maps to blank rows in the user's spreadsheet groups. Do not strip blank lines when processing this file.

### Environment variables (via `.env`)

All credentials are loaded with `python-dotenv`. See `.env.example` for the full list. Key groups:
- `CMC_API_KEY` — CoinMarketCap (optional unless CMC tickers are active)
- `BINANCE_*`, `BYBIT_MAIN_*`, `BYBIT_STRATEGICCHECK_*`, `BYBIT_SCALPING_*`, `MEXC_*`, `BITGET_*` — exchange credentials for `crypto_data_fetcher_API.py` only

Price-fetching scripts (`_current`, `_others`) use only public API endpoints and need no exchange credentials.

### Output format

Tab-separated, 7 columns: `Ticker | YestDayPrice | StartDayPrice | OldPrice | NewPrice | PriceDiff | CurrYestPriceDiff`. `PriceDiff` and `CurrYestPriceDiff` are percentage values without a `%` symbol, formatted to 2 decimal places. Prices are formatted to 6 decimal places.
