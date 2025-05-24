# 🪙 Crypto Daily Price Tracker

This project helps you track the **daily prices** of your selected cryptocurrency tickers from major exchanges (**MEXC** as primary, **Bybit** as fallback). It collects current prices, compares them with previous values, and saves historical diffs — so you can analyze market movement day by day.

---

## 🚀 Features

- 📥 Custom list of tracked crypto tickers
- 📊 Compares:
  - Current price vs. **previous run**
  - Current price vs. **start of the day**
  - Current price vs. **yesterday**
- 🗂️ Outputs tab-separated CSV for use in your own Excel or LibreOffice tracking table
- 🔁 Automatic fallback from MEXC to Bybit if a coin is not available
- 💾 Preserves empty lines for organized formatting

---

## 🛠️ Setup Instructions

### 1. 📦 Requirements

- Python 3.8+
- Python package: `requests`

Install `requests`:

``bash
pip install requests

## 📂 Step 2: Open Output in Excel or LibreOffice Calc

After running the script, you will see a file named:

fetch_crypto_prices.csv

This file contains up-to-date price information for each ticker in your list.

### 📄 Columns in the Output

The file is **tab-delimited** (`.tsv`) and includes the following columns:

| Column Name           | Description                                                                 |
|------------------------|-----------------------------------------------------------------------------|
| `Ticker`              | Crypto ticker symbol (e.g. `BTC`, `ETH`)                                    |
| `YestDayPrice`        | Price from the start of **yesterday**                                       |
| `StartDayPrice`       | Price from the first run **today**                                          |
| `OldPrice`            | Price from the **previous run** (today)                                     |
| `NewPrice`            | Current fetched price                                                       |
| `PriceDiff`           | % difference between `NewPrice` and `OldPrice`                              |
| `CurrYestPriceDiff`   | % difference between `NewPrice` and `YestDayPrice`                          |

### 📝 Example Output
Ticker YestDayPrice StartDayPrice OldPrice NewPrice PriceDiff CurrYestPriceDiff
BTC 42300.00 42650.00 42710.00 42840.00 0.30 1.28
ETH 2180.00 2200.00 2210.00 2225.00 0.68 2.06


> ✅ Tip: You can open the file in **Excel** or **LibreOffice Calc** by choosing "Tab" as the delimiter during import.

## 📋 Step 3: Copy & Paste into Your `statistics_template.csv`

Once `fetch_crypto_prices.csv` is open in Excel or LibreOffice Calc, you'll want to **copy the data** (starting from the `YestDayPrice` column) and **paste it into your tracking sheet** `statistics_template.csv`.

### 🎯 Where to Paste

You should paste the data into the `statistics_template.csv` starting from the `YestDayPrice` column. The columns must align as follows:

| From `fetch_crypto_prices.csv` | To `statistics_template.csv`   |
|-------------------------------|--------------------------------|
| `YestDayPrice`                | YestDayPrice                   |
| `StartDayPrice`               | StartDayPrice                  |
| `OldPrice`                    | OldPrice                       |
| `NewPrice`                    | NewPrice                       |
| `PriceDiff`                   | DiffFromPrev                   |
| `CurrYestPriceDiff`           | DiffFromYest                   |

> 📌 Be careful to align rows by ticker name if your template contains additional columns before `YestDayPrice`.

---

### ✂️ Copy Example

Let’s say your `fetch_crypto_prices.csv` looks like this:
YestDayPrice StartDayPrice OldPrice NewPrice PriceDiff CurrYestPriceDiff
42300.00 42650.00 42710.00 42840.00 0.30 1.28
2180.00 2200.00 2210.00 2225.00 0.68 2.06

You would **copy this block** (excluding `Ticker`), and paste it into your `statistics_template.csv` starting at the `YestDayPrice` column.

## ✍️ Step 4: Update Formulas in Your `statistics_template.csv`

After pasting the fresh data from `fetch_crypto_prices.csv` into your `statistics_template.csv` (starting at `YestDayPrice`), you need to **update calculated columns**.

These columns are not auto-filled by the script, but are important for daily monitoring:

---

### 🟨 `DiffFromMorn`

Shows the price movement **since the start of the day**:

``excel
=NewPrice - StartDayPrice

This tells you how the price changed between the first check of the day and now.

🟩 % from Buy
=(NewPrice - Buy Price) / Buy Price * 100
This requires that you have correctly entered your Buy Price for each coin.

📌 Example Setup
Buy Price	StartDayPrice	NewPrice	DiffFromMorn	% from Buy
22000	42650.00	42840.00	=42840-42650	=(42840-22000)/22000*100

✅ Tip: Set formulas once in the first row, then drag down for the rest of your coins.
🧠 You can also add conditional formatting (e.g. green for gain, red for loss).

Now your personal spreadsheet is fully updated with today's market movements!

## ⚙️ Step 5: (Optional) Automate Your Workflow
To make your daily tracking smoother, you can automate some steps to save time and reduce manual effort.

---

### ⏰ Option 1: Schedule Daily Script Run

You can schedule the script to run automatically every morning.

#### 🪟 Windows (Task Scheduler)

1. Open **Task Scheduler**
2. Create new task:
   - **Trigger**: Daily at 08:00 AM
   - **Action**: Run
     ```bash
     python path\to\fetch_crypto_prices_current.py
     ```
3. Ensure the Python environment and working directory are correct.

#### 🐧 Linux (cron)

``bash
0 8 * * * /usr/bin/python3 /path/to/fetch_crypto_prices_current.py

📌 Make sure file paths and Python binary locations are correct.


📊 Option 3: Enhance Your Template with Excel Formulas
Add a timestamp column (e.g. =TODAY()).

Use conditional formatting for:

PriceDiff > 5% → green

PriceDiff < -5% → red

Add a sparkline column for weekly trend visualization.

🚀 Bonus: Advanced Extensions
🔔 Email yourself the CSV or summary (using SMTP or SendGrid)

📱 Send alerts to Telegram/Discord on big price changes

☁️ Export to Google Sheets using gspread
