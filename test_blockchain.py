#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pineapplebingodev/gitprojects/coinledger-parser')

from src.reconciliation.blockchain import BlockchainClient

# Test with the user's Bitcoin addresses
addresses = [
    "bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql",  # Taproot
    "bc1qeezvh8psmu32tylqxlkpwjf3854n8cp6vv5lk8",  # SegWit
    "383pcVpTUPdTcj4pPnYhhqQds6JLh25rpy"  # Legacy
]

client = BlockchainClient()

for address in addresses:
    print(f"\n{'='*80}")
    print(f"Testing address: {address}")
    print(f"{'='*80}")
    
    try:
        transactions = client.fetch_transactions(address, 'bitcoin')
        print(f"\n✅ Successfully fetched {len(transactions)} transactions")
        
        if transactions:
            print(f"\nFirst 3 transactions (sorted by date descending):")
            for i, tx in enumerate(transactions[:3]):
                print(f"\n{i+1}. {tx.timestamp} | {tx.tx_type} | {tx.amount} BTC | {tx.tx_id[:16]}...")
        else:
            print("\n⚠️  No transactions found for this address")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
