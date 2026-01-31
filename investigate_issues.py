#!/usr/bin/env python3
"""
Investigate the three reported issues:
1. Duplicate transactions at same timestamp
2. Incorrect Ordiscan links (using CSV IDs instead of tx hashes)
3. Missing asset tags in SALE patterns
"""

import requests
import json

print('🔍 INVESTIGATING REPORTED ISSUES')
print('=' * 80)

# Step 1: Upload CSV
print('\n1. Uploading CSV...')
with open('import/Xverse Import transactions - Sheet1.csv', 'rb') as f:
    response = requests.post('http://localhost:8000/api/upload', 
                            files={'file': ('test.csv', f, 'text/csv')})
    print(f'   ✅ Uploaded: {response.json().get("count")} transactions')

# Step 2: Fetch blockchain data
print('\n2. Fetching blockchain data...')
response = requests.post('http://localhost:8000/api/fetch-blockchain', json={
    'wallet_address': 'bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql',
    'chain': 'bitcoin',
    'from_date': '2025-01-01',
    'to_date': '2026-01-30'
})
print(f'   ✅ Fetched: {response.json().get("count")} transactions')

# Step 3: Run analysis
print('\n3. Running analysis...')
response = requests.post('http://localhost:8000/api/analyze')
data = response.json()

if 'detail' in data:
    print(f'   ❌ Error: {data["detail"]}')
    exit(1)

suggestions = data.get('correction_suggestions', [])
print(f'   ✅ Found: {len(suggestions)} correction suggestions')

# ISSUE 1: Investigate duplicate transactions
print('\n' + '=' * 80)
print('ISSUE 1: DUPLICATE TRANSACTIONS')
print('=' * 80)

duplicates_found = False
for suggestion in suggestions:
    if suggestion.get('pattern') == 'SALE':
        txs = suggestion.get('affected_transactions', [])
        if len(txs) > 1:
            # Check if they're actually duplicates (same timestamp, amount, type)
            tx_signatures = []
            for tx in txs:
                sig = (tx.get('date'), tx.get('time'), tx.get('type'), 
                      tx.get('amount'), tx.get('source'))
                tx_signatures.append(sig)
            
            # If we have duplicate signatures, that's the issue
            if len(tx_signatures) != len(set(tx_signatures)):
                duplicates_found = True
                print(f'\n⚠️ DUPLICATE FOUND:')
                for i, tx in enumerate(txs):
                    print(f'  [{i+1}] {tx.get("date")} {tx.get("time")} | '
                          f'{tx.get("type")} | {tx.get("amount")} BTC | '
                          f'Source: {tx.get("source")} | '
                          f'TxID: {tx.get("tx_id", "N/A")[:40]}...')

if not duplicates_found:
    print('✅ No exact duplicates found')
    print('   (Multiple transactions at same time from different sources is expected)')

# ISSUE 2: Investigate Ordiscan links
print('\n' + '=' * 80)
print('ISSUE 2: ORDISCAN LINKS')
print('=' * 80)

bad_links = []
for suggestion in suggestions:
    for action in suggestion.get('recommended_actions', []):
        ordiscan_link = action.get('ordiscan_link', '')
        if ordiscan_link:
            # Check if it contains "XVERSE" (CSV identifier) instead of real tx hash
            if 'XVERSE' in ordiscan_link or len(ordiscan_link.split('/')[-1]) < 40:
                bad_links.append({
                    'pattern': suggestion.get('pattern'),
                    'link': ordiscan_link,
                    'tx_id': action.get('transaction', {}).get('tx_id', 'N/A')
                })

if bad_links:
    print(f'\n⚠️ FOUND {len(bad_links)} BAD ORDISCAN LINKS:')
    for item in bad_links[:5]:
        print(f'  Pattern: {item["pattern"]}')
        print(f'  Bad Link: {item["link"]}')
        print(f'  Actual TxID: {item["tx_id"][:60]}...')
        print()
else:
    print('✅ All Ordiscan links look correct')

# ISSUE 3: Check asset tags in SALE patterns
print('=' * 80)
print('ISSUE 3: ASSET TAGS IN SALE PATTERNS')
print('=' * 80)

sale_patterns = [s for s in suggestions if s.get('pattern') == 'SALE']
print(f'\nFound {len(sale_patterns)} SALE patterns')

missing_tags = []
for sale in sale_patterns[:5]:
    for tx in sale.get('affected_transactions', []):
        metadata = tx.get('metadata', {})
        asset_type = metadata.get('asset_type')
        
        if not asset_type and tx.get('source') == 'BLOCKCHAIN':
            missing_tags.append({
                'date': tx.get('date'),
                'time': tx.get('time'),
                'amount': tx.get('amount'),
                'tx_id': tx.get('tx_id', 'N/A')[:40],
                'metadata': metadata
            })

if missing_tags:
    print(f'\n⚠️ FOUND {len(missing_tags)} BLOCKCHAIN TXS WITHOUT ASSET TAGS:')
    for item in missing_tags[:3]:
        print(f'  {item["date"]} {item["time"]} | {item["amount"]} BTC')
        print(f'  TxID: {item["tx_id"]}...')
        print(f'  Metadata: {item["metadata"]}')
        print()
else:
    print('✅ All blockchain transactions have asset tags')

print('=' * 80)
print('INVESTIGATION COMPLETE')
print('=' * 80)
