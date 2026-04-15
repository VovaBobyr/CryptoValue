# CryptoValue — Optimization Audit Report

**Date:** 2026-04-15  
**Audited files:** `fetch_crypto_prices_current.py`, `fetch_crypto_prices_others.py`, `crypto_data_fetcher_API.py`, `crypto_prices_with_differences.py`, `test.py`, `api_keys.json`, `README.md`

---

## Executive Summary

This is a Python-based personal cryptocurrency price tracker. It fetches daily prices from MEXC (primary), Bybit (fallback), and CoinMarketCap, writes tab-separated CSV output for spreadsheet analysis, and optionally queries exchange accounts via the CCXT library.

**Most urgent issue:** Real API keys for 5 exchange accounts are committed to the repository in plaintext — these should be revoked and rotated immediately.

---

## 1. Code Quality & Modernization

### 🔴 `fetch_crypto_prices_current.py` — Module-level execution, no `__main__` guard
**Lines 131–134:** All file paths and the `fetch_crypto_prices()` call sit at module level. This means the script runs its full logic (including network requests and file writes) on `import`, making it impossible to test or reuse safely.
```python
# Current — runs unconditionally on import
input_file = "crypto_tickers.txt"
fetch_crypto_prices(input_file, output_file, last_run_date_file)
```
**Fix:** Wrap in `if __name__ == "__main__":`. `fetch_crypto_prices_others.py` already does this correctly — use it as the model.

---

### 🔴 `crypto_prices_with_differences.py` — Broken historical price implementation
**Lines 31–41, 99:** The function `fetch_historical_price()` calls a non-existent Bybit endpoint (`/v5/market/historical-prices`) that always returns `None`. The script produces an output file full of `N/A` rows. The entire historical comparison feature is silently non-functional.
**Fix:** Implement using the real Bybit kline endpoint (`/v5/market/kline`) with `interval=1` and the target timestamp, or remove the script until it is properly implemented.

---

### 🟡 `fetch_crypto_prices_current.py` — Function-attribute cache is an anti-pattern
**Lines 72–83:** Bybit prices are cached by setting `fetch_crypto_prices.bybit_prices` as an attribute on the function object. This is fragile and surprising to any reader.
```python
if not hasattr(fetch_crypto_prices, "bybit_prices"):
    ...
    fetch_crypto_prices.bybit_prices = {...}
```
**Fix:** Use a local variable passed as a parameter, or hoist the Bybit fetch to the same level as the MEXC fetch (as done in `fetch_crypto_prices_others.py`).

---

### 🟡 `fetch_crypto_prices_others.py` — Python 3.10+ syntax used in a 3.8+ project
**Line 209:** `def fmt_price(v: Decimal | None)` uses the `X | Y` union type syntax, which requires Python 3.10+. The README specifies Python 3.8+.
**Fix:** Change to `Optional[Decimal]` from `typing`, or use `Union[Decimal, None]`.

---

### 🟡 Two scripts doing the same job
`fetch_crypto_prices_current.py` and `fetch_crypto_prices_others.py` implement the same workflow. The `_others` version is strictly more capable (it adds BTC.D, OTHERS.D, and OTHERSX10.D support). The `_current` version is now just a subset duplicate.
**Fix:** Retire `fetch_crypto_prices_current.py` and use `fetch_crypto_prices_others.py` as the single canonical daily runner. Update README accordingly.

---

### 🟡 `fetch_crypto_prices_current.py` — Date appended to header row inconsistently
**Line 122:**
```python
csvwriter.writerow([
    "Ticker", "YestDayPrice", ..., "CurrYestPriceDiff", today_date  # ← extra column!
])
```
The date is appended as an extra column in the header of `_current`, but the `_others` version (line 288) does not include it. This makes the two outputs structurally incompatible and can break spreadsheet imports.
**Fix:** Remove `today_date` from the header row.

---

### 🟢 BUSD pairs referenced in code (deprecated)
**`fetch_crypto_prices_current.py` lines 64, 86; `fetch_crypto_prices_others.py` lines 198–204; `crypto_prices_with_differences.py` lines 51–55:** BUSD fallback is checked for every ticker, but Binance retired BUSD in December 2023 — no exchange lists BUSD pairs anymore.
**Fix:** Remove all `symbol_busd` / `BUSD` checks to reduce dead code.

---

### 🟢 `test.py` is committed debug code
`test.py` is 13 lines of exploratory API inspection with no assertions, no test framework, and no documented purpose.
**Fix:** Either delete it or convert it into a proper `pytest` test with assertions.

---

## 2. Performance

### 🔴 `crypto_data_fetcher_API.py::fetch_trades` — Fetches all market symbols individually
**Lines 64–70:** `exchange.load_markets()` returns hundreds of symbols, and the code calls `exchange.fetch_my_trades(symbol, ...)` for every one of them in a loop. On Bybit this is 800+ sequential API requests per account (3 Bybit accounts = 2400+ calls), taking many minutes and likely hitting rate limits.
```python
for symbol in markets:
    trades += exchange.fetch_my_trades(symbol, since=one_week_ago)
```
**Fix:** Most exchanges support filtering trades by time without iterating symbols. For Bybit, use `exchange.fetch_my_trades(None, since=one_week_ago)` (CCXT supports this for exchanges that allow it). Alternatively limit to only symbols in `crypto_tickers.txt`.

---

### 🔴 `crypto_data_fetcher_API.py::fetch_balances` — One ticker fetch per held currency
**Lines 48–53:** Each non-zero balance triggers its own `exchange.fetch_ticker(ticker)` call, making N sequential HTTP requests for N held currencies.
**Fix:** Use `exchange.fetch_tickers(symbols)` to batch-fetch all prices in a single call, or fetch the full ticker list once and look up prices from it.

---

### 🟡 `fetch_crypto_prices_others.py` — `fetch_cmc_global()` called twice
**Lines 94, 121:** `fetch_cmc_dominance()` and `fetch_cmc_others_ex_top10_percent()` each call `fetch_cmc_global()` independently. If both special tickers (e.g. `BTC.D` and `OTHERSX10.D`) are in the ticker list, CoinMarketCap's global endpoint is hit twice.
**Fix:** Move the global data into the top-level `cmc_cache` dict so it is fetched once and reused.

---

### 🟡 `fetch_crypto_prices_current.py` — No timeout on MEXC request
**Line 14:**
```python
response = requests.get(mexc_url)  # no timeout
```
Without a timeout the script can hang indefinitely if MEXC is slow. `fetch_crypto_prices_others.py` correctly uses `timeout=20`.
**Fix:** Add `timeout=20` (or a configurable constant).

---

### 🟢 No HTTP session / connection pooling
All scripts create bare `requests.get()` calls. For scripts making multiple requests to the same host (Bybit, CMC), using a `requests.Session()` would reuse the TCP connection and be slightly faster.

---

## 3. Architecture & Structure

### 🟡 Hardcoded file paths at module level
**`fetch_crypto_prices_current.py` lines 131–133; `crypto_prices_with_differences.py` lines 91–97:** Paths and configuration live at the global scope outside any function, making the scripts path-sensitive to the working directory and untestable without side effects.
**Fix:** Move all path/config variables inside `main()` or accept them as CLI arguments (e.g. via `argparse`).

---

### 🟡 Output file written even when all prices fail
**`fetch_crypto_prices_current.py` lines 119–125:** The CSV is opened for writing unconditionally. If the MEXC fetch at line 14 raises an exception, the file write never happens — that's fine. But if MEXC returns data while all tickers somehow resolve to `N/A`, the file is overwritten with empty data, destroying the previous run's values.
**Fix:** Collect `output_data` first; only write to file if at least one valid price row was produced.

---

### 🟢 Stale / experimental output files committed to repo
`combined_crypto_prices.csv`, `synchronized_crypto_prices.csv`, `synchronized_crypto_prices_with_empty_lines.csv`, and `synchronized_crypto_prices_with_tabs.csv` appear to be experimental outputs from earlier development iterations. They add noise to the repository.
**Fix:** Delete these files and add `*.csv` (or the specific filenames) to `.gitignore`.

---

### 🟢 `lastrundate.txt` committed to repo
State files like `lastrundate.txt` are runtime artefacts. Committing them causes spurious diffs every time the script runs, and creates merge conflicts when used across multiple machines.
**Fix:** Add `lastrundate.txt` to `.gitignore`.

---

## 4. Dependencies

### 🔴 No `requirements.txt`
There is no `requirements.txt`, `setup.py`, or `pyproject.toml`. The README only lists `requests` but the project also needs `ccxt` for `crypto_data_fetcher_API.py`.
**Fix:** Create `requirements.txt`:
```
requests>=2.31.0
ccxt>=4.0.0
```

---

### 🟡 No pinned dependency versions
`ccxt` in particular has breaking API changes across major versions. Without pinned versions, `pip install` on a new machine may pull an incompatible version.
**Fix:** Pin versions in `requirements.txt` (e.g. `ccxt==4.3.x`).

---

### 🟢 `ccxt` not mentioned in README setup instructions
The README's setup section only mentions `pip install requests`, meaning `crypto_data_fetcher_API.py` will fail on a fresh install with `ModuleNotFoundError`.
**Fix:** Update README to include `pip install requests ccxt`.

---

## 5. Error Handling & Resilience

### 🔴 No retry logic for transient API failures
All API calls in all scripts have no retry mechanism. A single transient network error (connection reset, 429 rate-limit, 503) will abort the entire run, potentially leaving the CSV in a partially-written state.
**Fix:** Wrap API calls in a simple retry loop with exponential backoff, or use `urllib3.util.retry.Retry` via a `requests.Session`.

---

### 🟡 `fetch_balances` silently drops USDT holdings
**`crypto_data_fetcher_API.py` lines 47–52:** The code tries `exchange.fetch_ticker("USDT/USDT")` which always fails. The `except Exception: value = 0` swallows the error and USDT holdings are counted as $0, making the total USDT value incorrect.
**Fix:** Skip the price lookup when `currency == "USDT"` (or any stablecoin) and count it at face value (1.0).

---

### 🟡 `fetch_crypto_prices_current.py` — `is_new_day` logic has a subtle bug
**Lines 97–106:** `curr_yest_price_diff` is calculated using `yest_day_price` *before* `yest_day_price` is reassigned on line 106 (for the new-day case). This means on a new day, `curr_yest_price_diff` correctly uses yesterday's start price. But the intermediate variable name `yest_day_price` is overwritten, which is confusing and error-prone if the logic is ever reordered.
**Fix:** In `_others`, this is already cleaner. Retire `_current` (see point in §1).

---

### 🟢 `crypto_prices_with_differences.py` — No error raised for broken API
**Lines 36–40:** When `fetch_historical_price` fails, it returns `None` silently. The caller checks for `None` and writes `N/A`, but there is no log message telling the user *why* every row is `N/A`. A first-time user would be confused.
**Fix:** Either implement the endpoint properly or raise a `NotImplementedError` with a message explaining the feature is incomplete.

---

## 6. Readability & Maintainability

### 🔴 CoinMarketCap API key hardcoded in source
**`fetch_crypto_prices_others.py` line 8:**
```python
CMC_API_KEY = "952df909-9520-4b32-8380-9aa6a658db87"
```
A real API key is hardcoded in source and will be committed to version control.
**Fix:** Read from environment variable: `CMC_API_KEY = os.environ.get("CMC_API_KEY", "")`.

---

### 🟡 Mixed comment languages
`fetch_crypto_prices_others.py` has all comments in Ukrainian (e.g. `# Налаштування`, `# список тікерів`, `# джерела цін`). The other three files use English. This inconsistency makes the codebase harder to navigate.
**Fix:** Standardize to one language — either translate Ukrainian comments to English or the reverse.

---

### 🟡 Magic number for 7-day timestamp offset
**`crypto_data_fetcher_API.py` line 63:**
```python
one_week_ago = int(time.time() * 1000) - 7 * 24 * 60 * 60 * 1000
```
The intent is clear but the inline arithmetic is noisy.
**Fix:**
```python
ONE_WEEK_MS = 7 * 24 * 60 * 60 * 1000
one_week_ago = int(time.time() * 1000) - ONE_WEEK_MS
```

---

### 🟢 No docstrings on public functions
None of the functions in `fetch_crypto_prices_current.py` or `crypto_data_fetcher_API.py` have docstrings. `fetch_crypto_prices_others.py` has partial Ukrainian docstrings.
**Fix:** Add one-line English docstrings to each function describing its purpose, parameters, and return value.

---

## 7. Testing

### 🔴 No automated test suite
There are zero unit tests, zero integration tests, and no test framework configured. The only "test" is `test.py`, which prints raw API output and requires a live network connection.

Critical logic that is untested:
- New-day detection and `YestDayPrice`/`StartDayPrice` rollover
- Price difference percentage calculations
- `N/A` handling when prices are unavailable
- CSV read/write round-tripping
- `OTHERS.D` dominance calculation

**Fix:** Add `pytest` and write tests for the calculation logic using mock/fixture data. The day-rollover logic especially deserves table-driven tests covering: first run, same-day re-run, new-day run, and missing previous data.

---

### 🟡 No offline/mock mode
All scripts make live network calls. There is no way to run them in a sandboxed or offline mode for development or CI.
**Fix:** Introduce simple fixture JSON files for API responses (MEXC, Bybit, CMC), and pass them as parameters or via a `--dry-run` flag.

---

## 8. Security

### 🔴 Real API keys committed to the repository
**`api_keys.json`:** This file contains live API credentials for:
- Binance (1 account)
- Bybit (3 accounts: main, strategicCheck, scalping)
- MEXC (1 account)
- Bitget (1 account)

These appear to be real keys based on their format and length. If this repository has ever been pushed to GitHub (the remote is `https://github.com/VovaBobyr/CryptoValue.git`), these keys are publicly exposed and should be considered compromised.

**Immediate action required:**
1. Revoke and regenerate all 6 API keys on each exchange immediately.
2. Remove `api_keys.json` from git history (`git filter-repo` or BFG Repo Cleaner).
3. Add `api_keys.json` to `.gitignore`.
4. Move credentials to environment variables or a secrets manager.

---

### 🔴 No `.gitignore` at project root
The repository has no `.gitignore` at root level, meaning CSV output files, the API keys file, the last-run state file, and `__pycache__` directories are all tracked by git.

**Fix:** Create a `.gitignore`:
```
api_keys.json
*.csv
lastrundate.txt
__pycache__/
*.pyc
.env
```

---

### 🟡 CoinMarketCap API key hardcoded in source (also a security issue)
Covered in §6 above. The key `952df909-9520-4b32-8380-9aa6a658db87` in `fetch_crypto_prices_others.py` line 8 is hardcoded and will be committed.
**Fix:** Use `os.environ.get("CMC_API_KEY")`.

---

### 🟡 No input validation on ticker file
**`fetch_crypto_prices_current.py` line 10; `fetch_crypto_prices_others.py` line 222:** Ticker symbols are read from a text file and passed directly into f-strings that form API query parameters (e.g., `f"{ticker}USDT"`). If the ticker file were tampered with, a malicious string like `../../etc/passwd` or a URL-injection string could be inserted.
**Fix:** Validate that each ticker matches `[A-Z0-9.]+` before use.

---

### 🟢 No HTTPS certificate verification override detected
All `requests.get()` calls use the default `verify=True` (good). No issues here, but worth noting explicitly as some scripts in crypto tooling disable certificate verification.

---

## Summary Table

| # | File | Severity | Category | Issue |
|---|------|----------|----------|-------|
| 1 | `api_keys.json` | 🔴 High | Security | Real exchange API keys committed to repo |
| 2 | (root) | 🔴 High | Security | No `.gitignore` — secrets not excluded |
| 3 | `fetch_crypto_prices_others.py:8` | 🔴 High | Security | CoinMarketCap API key hardcoded in source |
| 4 | `crypto_data_fetcher_API.py:64-70` | 🔴 High | Performance | Fetches trades for every market symbol (800+ API calls) |
| 5 | `crypto_prices_with_differences.py:31-41` | 🔴 High | Code Quality | Historical price feature is silently broken (placeholder) |
| 6 | `fetch_crypto_prices_current.py:131-134` | 🔴 High | Code Quality | No `__main__` guard — runs on import |
| 7 | All scripts | 🔴 High | Resilience | No retry logic for API failures |
| 8 | (root) | 🔴 High | Dependencies | No `requirements.txt` |
| 9 | All scripts | 🔴 High | Testing | No automated test suite |
| 10 | `crypto_data_fetcher_API.py:48-53` | 🟡 Medium | Performance | One HTTP call per held currency (should batch) |
| 11 | `fetch_crypto_prices_others.py:94,121` | 🟡 Medium | Performance | CMC global API called twice per run |
| 12 | `fetch_crypto_prices_current.py:14` | 🟡 Medium | Resilience | No HTTP timeout on MEXC request |
| 13 | `fetch_crypto_prices_current.py` vs `_others` | 🟡 Medium | Architecture | Two duplicate scripts; `_current` is a subset of `_others` |
| 14 | `fetch_crypto_prices_others.py:209` | 🟡 Medium | Code Quality | Python 3.10+ syntax (`X \| Y`) in a 3.8+ project |
| 15 | `fetch_crypto_prices_current.py:122` | 🟡 Medium | Code Quality | `today_date` appended to header — breaks CSV structure |
| 16 | `crypto_data_fetcher_API.py:47-52` | 🟡 Medium | Resilience | USDT holdings counted as $0 (fetch_ticker fails silently) |
| 17 | `fetch_crypto_prices_others.py` | 🟡 Medium | Readability | Comments in Ukrainian; rest of project is English |
| 18 | (root) | 🟡 Medium | Dependencies | No pinned dependency versions |
| 19 | All scripts | 🟡 Medium | Testing | No offline/mock mode — all tests require live API |
| 20 | `fetch_crypto_prices_current.py:119-125` | 🟡 Medium | Resilience | Output CSV written even if all prices are `N/A` |
| 21 | `fetch_crypto_prices_current.py:72-83` | 🟡 Medium | Code Quality | Function-attribute cache is an anti-pattern |
| 22 | `crypto_prices_with_differences.py:91-97` | 🟡 Medium | Architecture | Config at module level, not in `main()` |
| 23 | `fetch_crypto_prices_others.py:8` | 🟡 Medium | Readability | CoinMarketCap key should be env var |
| 24 | `crypto_data_fetcher_API.py:63` | 🟢 Low | Readability | Magic number `7 * 24 * 60 * 60 * 1000` — use named constant |
| 25 | All scripts | 🟢 Low | Readability | No docstrings on functions |
| 26 | All scripts | 🟢 Low | Code Quality | BUSD fallback logic is dead code (BUSD retired 2023) |
| 27 | `test.py` | 🟢 Low | Code Quality | Debug script committed with no assertions |
| 28 | `lastrundate.txt` | 🟢 Low | Architecture | State file committed — causes spurious diffs |
| 29 | (root) | 🟢 Low | Architecture | Experimental output CSVs committed (synchronized_*, combined_*) |
| 30 | `README.md` | 🟢 Low | Dependencies | Missing `ccxt` in setup instructions |

---

*No code changes have been made. Awaiting prioritization before any modifications.*
