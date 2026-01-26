import pandas as pd
import json
from src.config import get_gemini_model
from src.models import UnifiedTransaction
from datetime import datetime
import pytz

def smart_csv_load(file_path: str) -> pd.DataFrame:
    """
    Loads a CSV file and uses Gemini to infer the schema if standard columns are not found.
    """
    df = pd.read_csv(file_path)
    
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
            "time": "timestamp",
            "coin": "asset",
            "asset": "asset",
            "symbol": "asset",
            "amount": "amount",
            "balance": "amount",
            "transaction fee": "fee",
            "fee": "fee",
            "transaction hash": "tx_id",
            "txid": "tx_id",
            "hash": "tx_id",
            "type": "tx_type",
            "transaction type": "tx_type",
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
    """
    transactions = []
    
    # Ensure required columns exist after mapping
    required_cols = ['timestamp', 'asset', 'amount']
    if not all(col in df.columns for col in required_cols):
        print(f"Missing required columns: {[c for c in required_cols if c not in df.columns]}")
        return []

    for _, row in df.iterrows():
        try:
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

            tx = UnifiedTransaction(
                timestamp=timestamp,
                asset=str(row['asset']),
                amount=float(str(row['amount']).replace(',', '')),
                fee=float(str(row.get('fee', 0)).replace(',', '')),
                tx_id=str(row.get('tx_id', '')),
                tx_type=str(row.get('tx_type', 'UNKNOWN')),
                source='CEX',
                price_krw=float(str(row.get('price_krw', 0)).replace(',', '')) if 'price_krw' in row else None
            )
            transactions.append(tx)
        except Exception as e:
            print(f"Error parsing CSV row: {e}")
            continue
            
    return transactions
