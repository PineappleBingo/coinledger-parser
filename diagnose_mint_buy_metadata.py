#!/usr/bin/env python3
"""
Diagnostic script to check if MINT_BUY pattern has proper metadata
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ingest.csv_parser import smart_csv_load
from reconciliation.blockchain import BlockchainClient
from reconciliation.engine import reconcile_with_corrections

print("=" * 80)
print("MINT_BUY Pattern Metadata Diagnostic")
print("=" * 80)

# Load CSV
print("\n1. Loading CSV...")
csv_path = 'import/Xverse Import transactions - Sheet1.csv'
cex_txs = smart_csv_load(csv_path)
print(f"   ✓ Loaded {len(cex_txs)} CEX transactions")

# Fetch blockchain data
print("\n2. Fetching blockchain data...")
client = BlockchainClient()
wallet = 'bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql'
blockchain_txs = client.fetch_transactions([wallet])
print(f"   ✓ Fetched {len(blockchain_txs)} blockchain transactions")

# Check metadata on blockchain deposits
print("\n3. Checking metadata on blockchain deposits...")
ordinal_count = 0
rune_count = 0
btc_count = 0

for tx in blockchain_txs:
    if tx.tx_type == 'Deposit' and hasattr(tx, 'metadata') and tx.metadata:
        asset_type = tx.metadata.get('asset_type', 'UNKNOWN')
        if asset_type == 'ORDINAL':
            ordinal_count += 1
            print(f"\n   🎨 ORDINAL Deposit Found:")
            print(f"      TX ID: {tx.tx_id[:20]}...")
            print(f"      Amount: {tx.amount} BTC")
            print(f"      Metadata: {tx.metadata}")
        elif asset_type == 'RUNE':
            rune_count += 1
            print(f"\n   🔮 RUNE Deposit Found:")
            print(f"      TX ID: {tx.tx_id[:20]}...")
            print(f"      Amount: {tx.amount} BTC")
            print(f"      Metadata: {tx.metadata}")
        else:
            btc_count += 1

print(f"\n   Summary:")
print(f"   - ORDINAL deposits: {ordinal_count}")
print(f"   - RUNE deposits: {rune_count}")
print(f"   - BTC deposits: {btc_count}")

# Run reconciliation
print("\n4. Running reconciliation...")
suggestions = reconcile_with_corrections(cex_txs, blockchain_txs)
print(f"   ✓ Found {len(suggestions)} patterns")

# Check MINT_BUY patterns
print("\n5. Checking MINT_BUY patterns...")
mint_buy_patterns = [s for s in suggestions if s.get('pattern') == 'MINT_BUY']
print(f"   Found {len(mint_buy_patterns)} MINT_BUY patterns")

for idx, pattern in enumerate(mint_buy_patterns, 1):
    print(f"\n   Pattern #{idx}:")
    print(f"   Confidence: {pattern.get('confidence')}")
    
    # Check corrections
    corrections = pattern.get('corrections', [])
    for corr_idx, correction in enumerate(corrections, 1):
        action = correction.get('action')
        print(f"\n      Correction {corr_idx}: {action}")
        
        if 'transaction' in correction:
            tx = correction['transaction']
            print(f"         Transaction included: YES")
            print(f"         TX ID: {tx.tx_id[:20]}...")
            print(f"         Type: {tx.tx_type}")
            print(f"         Has metadata: {hasattr(tx, 'metadata') and bool(tx.metadata)}")
            
            if hasattr(tx, 'metadata') and tx.metadata:
                print(f"         Metadata: {tx.metadata}")
                
                # Check what frontend needs
                asset_type = tx.metadata.get('asset_type')
                inscription_id = tx.metadata.get('inscription_id')
                rune_name = tx.metadata.get('rune_name')
                
                print(f"\n         Frontend Checks:")
                print(f"         - asset_type == 'ORDINAL': {asset_type == 'ORDINAL'}")
                print(f"         - has inscription_id: {bool(inscription_id)}")
                print(f"         - has rune_name: {bool(rune_name)}")
                
                if asset_type == 'ORDINAL' and inscription_id:
                    print(f"         ✓ OrdinalPreview SHOULD display")
                elif rune_name:
                    print(f"         ✓ RunePreview SHOULD display")
                else:
                    print(f"         ✗ No preview will display (missing metadata)")
            else:
                print(f"         ✗ NO METADATA - Preview will NOT display")
        else:
            print(f"         Transaction included: NO")

print("\n" + "=" * 80)
print("Diagnostic Complete")
print("=" * 80)
