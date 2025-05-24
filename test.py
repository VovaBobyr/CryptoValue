import requests
import json

bybit_url = "https://api.bybit.com/v5/market/tickers"
bybit_params = {"category": "spot"}
response = requests.get(bybit_url, params=bybit_params)

if response.status_code == 200:
    data = response.json()
    print(json.dumps(data, indent=4))  # Pretty-print the response
else:
    print(f"Error: {response.status_code}, {response.text}")
