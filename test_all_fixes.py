#!/usr/bin/env python3
"""
Test all three fixes:
1. Deduplication of CSV rows
2. Ordiscan links only for real blockchain tx_ids
3. Asset tags in SALE patterns
"""

import requests
import json

print('🧪 TESTING ALL FIXES')
print('=' * 80)

# Step 1: Upload CSV (should deduplicate)
print('\n1. Testing CSV Deduplication...')
with open('import/Xverse Import transactions - Sheet1.csv', 'rb') as f:
    response = requests.post('http://localhost:8000/api/upload', 
                            files={'file': ('test.csv', f, 'text/csv')})
    count = response.json().get("count")
    print(f'   ✅ Uploaded: {count} transactions (after deduplication)')

# Step 2: Fetch blockchain data
print('\n2. Fetching blockchain data...')
response = requests.post('http://localhost:8000/api/fetch-blockchain', json={
    'wallet_address': 'bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql',
    'chain': 'bitcoin',
    'from_date': '2025-01-01',
    'to_date': '2026-01-30'
})
blockchain_count = response.json().get("count")
print(f'   ✅ Fetched: {blockchain_count} blockchain transactions')

# Step 3: Run analysis
print('\n3. Running analysis...')
response = requests.post('http://localhost:8000/api/analyze')
data = response.json()

if 'detail' in data:
    print(f'   ❌ Error: {data["detail"]}')
    exit(1)

suggestions = data.get('correction_suggestions', [])
print(f'   ✅ Found: {len(suggestions)} correction suggestions')

# TEST 1: Check for duplicates in affected_transactions
print('\n' + '=' * 80)
print('TEST 1: DUPLICATE TRANSACTIONS')
print('=' * 80)

duplicates_found = False
for suggestion in suggestions:
    txs = suggestion.get('affected_transactions', [])
    if len(txs) > 1:
        # Check for exact duplicates
        tx_sigs = []
        for tx in txs:
            sig = (tx.get('date'), tx.get('time'), tx.get('type'), 
                  tx.get('amount'), tx.get('source'))
            tx_sigs.append(sig)
        
        if len(tx_sigs) != len(set(tx_sigs)):
            duplicates_found = True
            print(f'\n❌ DUPLICATE FOUND in {suggestion.get("pattern")} pattern:')
            for i, tx in enumerate(txs):
                print(f'  [{i+1}] {tx.get("date")} {tx.get("time")} | '
                      f'{tx.get("type")} | {tx.get("amount")} BTC | '
                      f'Source: {tx.get("source")}')

if not duplicates_found:
    print('✅ No duplicate transactions found!')

# TEST 2: Check Ordiscan links
print('\n' + '=' * 80)
print('TEST 2: ORDISCAN LINKS')
print('=' * 80)

total_links = 0
bad_links = 0
good_links = 0

for suggestion in suggestions:
    for action in suggestion.get('recommended_actions', []):
        ordiscan_link = action.get('ordiscan_link')
        if ordiscan_link:
            total_links += 1
            # Check if it contains fake identifiers
            if 'XVERSE_' in ordiscan_link or 'CEX_' in ordiscan_link:
                bad_links += 1
                print(f'\n❌ BAD LINK in {suggestion.get("pattern")} pattern:')
                print(f'   Link: {ordiscan_link}')
                print(f'   TxID: {action.get("transaction", {}).get("tx_id", "N/A")[:60]}')
            else:
                good_links += 1

print(f'\n📊 Ordiscan Link Summary:')
print(f'   Total links: {total_links}')
print(f'   ✅ Good links (real tx hashes): {good_links}')
print(f'   ❌ Bad links (fake identifiers): {bad_links}')

if bad_links == 0 and total_links > 0:
    print('\n✅ All Ordiscan links are valid!')
elif total_links == 0:
    print('\n⚠️  No Ordiscan links found (this might be expected if no blockchain txs)')

# TEST 3: Check asset tags in SALE patterns
print('\n' + '=' * 80)
print('TEST 3: ASSET TAGS IN SALE PATTERNS')
print('=' * 80)

sale_patterns = [s for s in suggestions if s.get('pattern') == 'SALE']
print(f'\nFound {len(sale_patterns)} SALE patterns')

blockchain_sales_with_tags = 0
blockchain_sales_without_tags = 0

for sale in sale_patterns[:10]:  # Check first 10
    for tx in sale.get('affected_transactions', []):
        if tx.get('source') == 'BLOCKCHAIN':
            metadata = tx.get('metadata', {})
            asset_type = metadata.get('asset_type')
            
            if asset_type:
                blockchain_sales_with_tags += 1
                print(f'\n✅ Blockchain SALE with asset tag:')
                print(f'   Date: {tx.get("date")} {tx.get("time")}')
                print(f'   Asset Type: {asset_type}')
                print(f'   Inscription ID: {metadata.get("inscription_id", "N/A")[:40]}...')
                print(f'   Rune Name: {metadata.get("rune_name", "N/A")}')
            else:
                blockchain_sales_without_tags += 1
                print(f'\n⚠️  Blockchain SALE without asset tag:')
                print(f'   Date: {tx.get("date")} {tx.get("time")}')
                print(f'   TxID: {tx.get("tx_id", "N/A")[:40]}...')

print(f'\n📊 SALE Pattern Asset Tags:')
print(f'   ✅ Blockchain sales WITH tags: {blockchain_sales_with_tags}')
print(f'   ⚠️  Blockchain sales WITHOUT tags: {blockchain_sales_without_tags}')

if blockchain_sales_without_tags == 0 and blockchain_sales_with_tags > 0:
    print('\n✅ All blockchain SALE patterns have asset tags!')

print('\n' + '=' * 80)
print('ALL TESTS COMPLETE')
print('=' * 80)
