#!/usr/bin/env python3
# Direct test of the upload logic
import sys
sys.path.insert(0, '/home/pineapplebingodev/gitprojects/coinledger-parser')

import pandas as pd
from src.ingest.csv_parser import smart_csv_load, normalize_csv_data

file_path = "import/Xverse Import transactions - Sheet1.csv"

try:
    print("Step 1: Reading original CSV...")
    original_df = pd.read_csv(file_path)
    original_data = original_df.to_dict('records')
    print(f"  ✓ Read {len(original_data)} rows")
    print(f"  Columns: {list(original_df.columns)}")
    
    print("\nStep 2: Processing with smart_csv_load...")
    df = smart_csv_load(file_path)
    print(f"  ✓ Processed, columns: {list(df.columns)}")
    
    print("\nStep 3: Normalizing data...")
    transactions = normalize_csv_data(df)
    print(f"  ✓ Normalized {len(transactions)} transactions")
    
    print("\n✅ All steps completed successfully!")
    print(f"Original data count: {len(original_data)}")
    print(f"Normalized transaction count: {len(transactions)}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
