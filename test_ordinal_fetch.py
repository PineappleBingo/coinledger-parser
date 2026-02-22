import requests
import json

url = "http://127.0.0.1:8000/api/fetch-rune-info"
payload = {
    "tx_id": "2f8de5d7107b160cb4c1d0e47b4d4ce138266c8ab443e41b5fc303e46f5444ca",
    "wallet_addresses": ["bc1qunuzd4zttc3435k5f3x4fzyy5kcl58j9wxx7y4"]
}
headers = {"Content-Type": "application/json"}

try:
    res = requests.post(url, json=payload, timeout=15)
    if res.status_code == 200:
        print(json.dumps(res.json(), indent=2))
    else:
        print(f"Error {res.status_code}: {res.text}")
except Exception as e:
    print(f"Failed: {e}")
