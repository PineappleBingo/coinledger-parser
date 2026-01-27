#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/pineapplebingodev/gitprojects/coinledger-parser')

from src.reconciliation.blockchain import BlockchainClient

# Test with one of the user's addresses to see full pagination
address = "bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql"

print(f"Testing FULL transaction history fetch for: {address}")
print(f"{'='*80}\n")

client = BlockchainClient()

try:
    transactions = client.fetch_transactions(address, 'bitcoin')
    
    print(f"\n{'='*80}")
    print(f"✅ Successfully fetched {len(transactions)} total transactions")
    print(f"{'='*80}")
    
    if transactions:
        print(f"\nDate range:")
        print(f"  Oldest: {transactions[-1].timestamp}")
        print(f"  Newest: {transactions[0].timestamp}")
        
        print(f"\nFirst 5 transactions (newest first):")
        for i, tx in enumerate(transactions[:5]):
            print(f"{i+1}. {tx.timestamp} | {tx.tx_type:12} | {tx.amount:12.8f} BTC")
        
        print(f"\nLast 5 transactions (oldest):")
        for i, tx in enumerate(transactions[-5:]):
            print(f"{len(transactions)-4+i}. {tx.timestamp} | {tx.tx_type:12} | {tx.amount:12.8f} BTC")
        
        # Count by year
        from collections import Counter
        years = Counter(tx.timestamp.year for tx in transactions)
        print(f"\nTransactions by year:")
        for year in sorted(years.keys()):
            print(f"  {year}: {years[year]} transactions")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
