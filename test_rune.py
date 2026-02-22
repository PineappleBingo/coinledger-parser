import requests, os, json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('UNISAT_API_KEY')
tx_id = '63ef790f31f7c7dcaf49f49b052d9e63fccfd9ce9ab920bacedbde86585f5297'
headers = {'Authorization': f'Bearer {api_key}'}

res = requests.get(f'https://open-api.unisat.io/v1/indexer/tx/{tx_id}', headers=headers, timeout=10)
if res.status_code == 200:
    data = res.json().get('data', {})
    print("VOUT:", json.dumps(data.get('vout', []), indent=2))
else:
    print(f"Error {res.status_code}: {res.text}")
