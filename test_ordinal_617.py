import requests
import json

url = "http://127.0.0.1:8000/api/fetch-rune-info"
payload = {
    "tx_id": "617b41e6241616f7eb50b42ab9602a0a1c5fb88d61958bc79da34692faa6bcef"
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
