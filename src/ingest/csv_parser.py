import pandas as pd
import json
from src.config import get_gemini_model
from src.models import UnifiedTransaction
from datetime import datetime
import pytz

def smart_csv_load(file_path: str) -> pd.DataFrame:
    """
    Loads a CSV file and uses Gemini to infer the schema if standard columns are not found.
    Handles special cases like Xverse wallet format with separate Date/Time columns.
    """
    df = pd.read_csv(file_path)
    
    # Special handling for Xverse format: combine Date and Time columns
    if 'Date' in df.columns and 'Time' in df.columns:
        print("Detected Xverse format with separate Date and Time columns. Combining...")
        df['timestamp'] = df['Date'] + ' ' + df['Time']
        df = df.drop(columns=['Date', 'Time'])
    
    # Special handling for Xverse: extract currency from Amount column if needed
    if 'Amount' in df.columns and 'Currency' in df.columns:
        print("Processing Xverse Amount and Currency columns...")
        for idx, row in df.iterrows():
            amount_val = str(row['Amount'])
            currency_val = str(row['Currency'])
            
            # If Currency is empty but Amount contains currency info
            if (pd.isna(row['Currency']) or currency_val.strip() == '' or currency_val == 'nan'):
                # Check if amount has currency embedded (e.g., "0.00052,BTC" or "0.00052 BTC")
                if ',' in amount_val and len(amount_val.split(',')) == 2:
                    parts = amount_val.split(',')
                    df.at[idx, 'Amount'] = parts[0].strip()
                    df.at[idx, 'Currency'] = parts[1].strip()
                elif ' ' in amount_val:
                    parts = amount_val.rsplit(' ', 1)  # Split from right to get last word
                    if len(parts) == 2 and parts[1].isalpha():
                        df.at[idx, 'Amount'] = parts[0].strip()
                        df.at[idx, 'Currency'] = parts[1].strip()

    
    # Standard columns we look for
    standard_columns = ['timestamp', 'asset', 'amount', 'fee', 'tx_id', 'tx_type']
    
    # Check if headers match standard schema (case-insensitive)
    headers = [h.lower() for h in df.columns]
    if all(col in headers for col in standard_columns):
        return df
    
    # If not, use Gemini to map columns
    mapping = infer_schema_with_gemini(list(df.columns))
    
    # Fallback: If Gemini fails (empty mapping), try manual mapping for common headers
    if not mapping:
        print("Gemini inference failed or returned empty. Trying manual fallback...")
        common_mappings = {
            "date (utc)": "timestamp",
            "date": "timestamp",
            "datetime": "timestamp",
            "time": "timestamp",
            "coin": "asset",
            "asset": "asset",
            "symbol": "asset",
            "currency": "asset",
            "amount": "amount",
            "balance": "amount",
            "quantity": "amount",
            "transaction fee": "fee",
            "fee": "fee",
            "transaction hash": "tx_id",
            "txid": "tx_id",
            "hash": "tx_id",
            "tx hash": "tx_id",
            "type": "tx_type",
            "transaction type": "tx_type",
            "action": "tx_type",
            "price": "price_krw",
            "krw": "price_krw"
        }
        
        mapping = {}
        for col in df.columns:
            col_lower = col.lower().strip()
            if col_lower in common_mappings:
                mapping[col] = common_mappings[col_lower]
        
        print(f"Manual fallback mapping: {mapping}")

    # Rename columns based on mapping
    df = df.rename(columns=mapping)
    return df

def infer_schema_with_gemini(headers: list[str]) -> dict:
    """
    Uses Gemini to map unknown CSV headers to the standard schema.
    """
    model = get_gemini_model()
    
    prompt = f"""
    Analyze these CSV headers and map them to the following standard schema fields:
    - timestamp: Date/time of transaction
    - asset: Cryptocurrency symbol (e.g., BTC, ETH)
    - amount: Quantity transacted
    - fee: Transaction fee
    - tx_id: Transaction Hash / ID
    - tx_type: Type of transaction (Buy, Sell, etc.)
    - price_krw: Price in KRW (optional)

    Input Headers: {headers}

    Return ONLY a JSON object where keys are the Input Headers and values are the standard schema fields. 
    If a header does not map to any standard field, do not include it in the JSON.
    Example: {{"Date (UTC)": "timestamp", "Coin": "asset"}}
    """
    
    try:
        response = model.generate_content(prompt)
        # Clean up response to ensure valid JSON
        text = response.text.strip()
        if text.startswith('```json'):
            text = text[7:-3]
        return json.loads(text)
    except Exception as e:
        print(f"Error inferring schema: {e}")
        return {}

def normalize_csv_data(df: pd.DataFrame) -> list[UnifiedTransaction]:
    """
    Normalizes the DataFrame into UnifiedTransaction objects.
    Handles edge cases like empty amounts, scientific notation, and missing tx_id.
    """
    transactions = []
    
    # Ensure required columns exist after mapping
    required_cols = ['timestamp', 'asset', 'amount']
    if not all(col in df.columns for col in required_cols):
        print(f"Missing required columns: {[c for c in required_cols if c not in df.columns]}")
        return []

    for idx, row in df.iterrows():
        try:
            # Skip rows with empty amounts
            if pd.isna(row['amount']) or str(row['amount']).strip() == '':
                print(f"Skipping row {idx}: empty amount")
                continue
            
            # Skip rows with empty or invalid assets
            if pd.isna(row['asset']) or str(row['asset']).strip() == '':
                print(f"Skipping row {idx}: empty asset")
                continue
                
            # Parse Timestamp
            ts = row['timestamp']
            if isinstance(ts, str):
                timestamp = pd.to_datetime(ts).to_pydatetime()
            else:
                timestamp = ts
                
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.UTC)
            else:
                timestamp = timestamp.astimezone(pytz.UTC)

            # Parse amount (handle scientific notation and commas)
            amount_str = str(row['amount']).replace(',', '').strip()
            try:
                amount = float(amount_str)
            except ValueError:
                print(f"Skipping row {idx}: invalid amount '{amount_str}'")
                continue
            
            # Parse fee (handle empty/missing values)
            fee_val = row.get('fee', 0)
            if pd.isna(fee_val) or str(fee_val).strip() == '':
                fee = 0.0
            else:
                try:
                    fee = float(str(fee_val).replace(',', ''))
                except ValueError:
                    fee = 0.0
            
            # Parse tx_id (generate placeholder if missing)
            tx_id_val = row.get('tx_id', '')
            if pd.isna(tx_id_val) or str(tx_id_val).strip() == '':
                # Generate a unique ID based on timestamp and amount
                tx_id = f"XVERSE_{timestamp.strftime('%Y%m%d%H%M%S')}_{abs(amount)}"
            else:
                tx_id = str(tx_id_val)

            tx = UnifiedTransaction(
                timestamp=timestamp,
                asset=str(row['asset']).strip(),
                amount=amount,
                fee=fee,
                tx_id=tx_id,
                tx_type=str(row.get('tx_type', 'UNKNOWN')),
                source='CEX',
                price_krw=float(str(row.get('price_krw', 0)).replace(',', '')) if 'price_krw' in row and not pd.isna(row.get('price_krw')) else None
            )
            transactions.append(tx)
        except Exception as e:
            print(f"Error parsing CSV row {idx}: {e}")
            continue
    
    # Deduplicate transactions (CSV may have duplicate rows)
    print(f"Parsed {len(transactions)} transactions from {len(df)} rows")
    
    # Remove duplicates based on timestamp, type, amount, and asset
    seen = set()
    deduplicated = []
    duplicates_removed = 0
    
    for tx in transactions:
        # Create a signature for the transaction
        signature = (
            tx.timestamp.isoformat(),
            tx.tx_type,
            tx.amount,
            tx.asset
        )
        
        if signature not in seen:
            seen.add(signature)
            deduplicated.append(tx)
        else:
            duplicates_removed += 1
    
    if duplicates_removed > 0:
        print(f"⚠️  Removed {duplicates_removed} duplicate transactions from CSV")
    
    print(f"Successfully parsed {len(deduplicated)} unique transactions")
    return deduplicated

