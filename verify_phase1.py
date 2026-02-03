
import asyncio
from src.reconciliation.blockchain import BlockchainClient
from src.models import UnifiedTransaction

def print_tx_details(tx):
    print(f"\n--- TX: {tx.tx_id[:8]}... ---")
    print(f"Asset: {tx.asset}")
    print(f"Amount: {tx.amount}")
    print(f"Metadata: {tx.metadata}")
    print(f"Witness Data (Count): {len(tx.witness_data) if tx.witness_data else 0}")
    if tx.witness_data:
        print(f"First Witness Item: {tx.witness_data[0][:50]}...")

def test_fetch():
    # Test address known to have some inscriptions/runes activity or just normal txs
    # Using a random active address or one from previous contexts if available.
    # Let's use a known high-activity address or just check the code logic by mocking if possible, 
    # but a real fetch is better.
    # Using a generic address for test (Binance Hot Wallet or similar for heavy data) or just the user's if known.
    # I'll use a hardcoded address that likely has witness data (e.g. an Ordinals wallet).
    # Since I don't have a specific one, I will try to fetch for a known Ordinal/runes burn address or similar
    # or just rely on the fact that most SegWit txs have witness data.
    
    test_address = "bc1p0q7059732732957327592385" # Dummy, might not work. 
    # Better: Use the client to fetch whatever is latest if possible, or just unit test the logic.
    # Actually, let's just use the `BlockchainClient` and mock the response data structure to verify the parsing logic 
    # without hitting the API to avoid address issues, 
    # OR better, use a real address if I can find one in the context.
    # I see `bc1p...` addresses in the user's previous logs? No.
    
    # Let's perform a "Dry Run" verification of the code logic via a mock since I don't have a guaranteed address.
    
    client = BlockchainClient()
    
    # Mock Response data
    mock_tx_data = [{
        "txid": "test_tx_id_123",
        "status": {"block_time": 1678888888},
        "vin": [
            {
                "prevout": {"value": 1000, "scriptpubkey_address": "my_address"},
                "witness": ["30440220...", "01"] # Mock witness
            }
        ],
        "vout": [
            {"value": 500, "scriptpubkey_address": "my_address"}
        ],
        "fee": 100
    }]
    
    # We need to temporarily monkeypatch requests.get to return this mock
    import requests
    from unittest.mock import MagicMock
    
    mock_response = MagicMock()
    mock_response.json.return_value = mock_tx_data
    mock_response.status_code = 200
    
    original_get = requests.get
    requests.get = MagicMock(return_value=mock_response)
    
    print("Testing fetch with mocked witness data...")
    transactions = client._fetch_bitcoin_transactions("my_address")
    
    for tx in transactions:
        print_tx_details(tx)
        if tx.witness_data and "30440220..." in tx.witness_data:
            print("SUCCESS: Witness data correctly extracted!")
        else:
            print("FAILURE: Witness data missing or incorrect.")

if __name__ == "__main__":
    test_fetch()
