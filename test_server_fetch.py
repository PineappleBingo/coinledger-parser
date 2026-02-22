import requests
import json

url = "http://127.0.0.1:8000/api/fetch-rune-info"
payload = {
    "tx_id": "63ef790f31f7c7dcaf49f49b052d9e63fccfd9ce9ab920bacedbde86585f5297",
    "wallet_addresses": ["bc1plplq5phekh034tvfrsrw2sxte0xgs94g2es9hk5tauhktkwwfyzswkyj65"]
}
headers = {"Content-Type": "application/json"}

res = requests.post(url, json=payload, timeout=15)
if res.status_code == 200:
    print(json.dumps(res.json(), indent=2))
else:
    print(f"Error {res.status_code}: {res.text}")
