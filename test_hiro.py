import requests, json

tx_id = '63ef790f31f7c7dcaf49f49b052d9e63fccfd9ce9ab920bacedbde86585f5297'
url = f"https://api.hiro.so/runes/v1/transactions/{tx_id}/activity"
headers = {"Accept": "application/json"}
res = requests.get(url, headers=headers)
print("HIRO ACTIVITY:", json.dumps(res.json(), indent=2))
