#!/usr/bin/env python3
"""
Test script to verify Ordinals and Runes metadata extraction
"""

from src.reconciliation.blockchain import BlockchainClient
from datetime import datetime
import json

def test_ordinals_runes_extraction():
    """Test inscription ID and Rune name extraction with real data"""
    
    client = BlockchainClient()
    address = 'bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql'
    
    print("=" * 70)
    print("ORDINALS & RUNES METADATA EXTRACTION TEST")
    print("=" * 70)
    print(f"\nFetching transactions for: {address[:30]}...")
    
    txs = client._fetch_bitcoin_transactions(address)
    
    # Categorize transactions
    ordinals = [tx for tx in txs if tx.metadata.get('asset_type') == 'ORDINAL']
    runes = [tx for tx in txs if tx.metadata.get('asset_type') == 'RUNE']
    btc = [tx for tx in txs if tx.metadata.get('asset_type') == 'BTC']
    
    print(f"\n📊 SUMMARY")
    print(f"{'─' * 70}")
    print(f"Total Transactions: {len(txs)}")
    print(f"  🎨 Ordinals: {len(ordinals)} ({len(ordinals)/len(txs)*100:.1f}%)")
    print(f"  🔮 Runes:    {len(runes)} ({len(runes)/len(txs)*100:.1f}%)")
    print(f"  💰 BTC:      {len(btc)} ({len(btc)/len(txs)*100:.1f}%)")
    
    # Test Ordinals
    print(f"\n🎨 ORDINALS SAMPLE (First 3)")
    print(f"{'─' * 70}")
    for i, tx in enumerate(ordinals[:3], 1):
        inscription_id = tx.metadata.get('inscription_id', 'N/A')
        print(f"\n{i}. {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Amount: {tx.amount:,.8f} BTC")
        print(f"   Type: {tx.tx_type}")
        print(f"   TxID: {tx.tx_id[:16]}...")
        print(f"   ✅ Inscription ID: {inscription_id}")
        print(f"   🔗 Link: https://ordinals.com/inscription/{inscription_id}")
    
    # Test Runes
    print(f"\n🔮 RUNES SAMPLE (First 3)")
    print(f"{'─' * 70}")
    for i, tx in enumerate(runes[:3], 1):
        rune_name = tx.metadata.get('rune_name', 'N/A')
        print(f"\n{i}. {tx.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Amount: {tx.amount:,.8f} BTC")
        print(f"   Type: {tx.tx_type}")
        print(f"   TxID: {tx.tx_id[:16]}...")
        print(f"   ✅ Rune Name: {rune_name}")
        print(f"   🔗 Link: https://ordinals.com/rune/{rune_name}")
    
    # Verification
    print(f"\n✅ VERIFICATION RESULTS")
    print(f"{'─' * 70}")
    
    ordinals_with_inscription_id = sum(1 for tx in ordinals if tx.metadata.get('inscription_id'))
    runes_with_name = sum(1 for tx in runes if tx.metadata.get('rune_name'))
    
    print(f"Ordinals with Inscription ID: {ordinals_with_inscription_id}/{len(ordinals)} ({ordinals_with_inscription_id/len(ordinals)*100:.1f}%)")
    print(f"Runes with Token Name: {runes_with_name}/{len(runes)} ({runes_with_name/len(runes)*100:.1f}%)")
    
    # Export sample data
    sample_data = {
        'summary': {
            'total': len(txs),
            'ordinals': len(ordinals),
            'runes': len(runes),
            'btc': len(btc)
        },
        'ordinals_sample': [
            {
                'date': tx.timestamp.isoformat(),
                'amount': tx.amount,
                'tx_id': tx.tx_id,
                'inscription_id': tx.metadata.get('inscription_id'),
                'link': f"https://ordinals.com/inscription/{tx.metadata.get('inscription_id')}"
            }
            for tx in ordinals[:5]
        ],
        'runes_sample': [
            {
                'date': tx.timestamp.isoformat(),
                'amount': tx.amount,
                'tx_id': tx.tx_id,
                'rune_name': tx.metadata.get('rune_name'),
                'link': f"https://ordinals.com/rune/{tx.metadata.get('rune_name')}"
            }
            for tx in runes[:5]
        ]
    }
    
    with open('test_results_ordinals_runes.json', 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    print(f"\n📄 Sample data exported to: test_results_ordinals_runes.json")
    print(f"\n{'=' * 70}")
    print("TEST COMPLETE ✅")
    print(f"{'=' * 70}\n")

if __name__ == '__main__':
    test_ordinals_runes_extraction()
