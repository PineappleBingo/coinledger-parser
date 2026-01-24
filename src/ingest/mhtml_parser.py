import re
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
from src.models import UnifiedTransaction

def extract_transactions_from_mhtml(file_path: str) -> pd.DataFrame:
    """
    Extracts transactions from a CoinLedger MHTML export file.
    
    Args:
        file_path: Path to the MHTML file.
        
    Returns:
        DataFrame containing the extracted transactions.
    """
    with open(file_path, 'rb') as f:
        content = f.read()

    # Try decoding with different encodings
    soup = None
    for encoding in ['utf-8', 'euc-kr', 'cp949', 'latin-1']:
        try:
            soup = BeautifulSoup(content.decode(encoding), 'lxml')
            break
        except UnicodeDecodeError:
            continue
    
    if not soup:
        raise ValueError("Could not decode MHTML file with supported encodings.")

    # Find the transaction table
    # Look for a table with class containing 'transaction', 'history', or 'ledger'
    table = soup.find('table', class_=re.compile(r'transaction|tx-history|ledger-table', re.I))
    
    if not table:
        # Fallback: Look for table with headers that look like transaction data
        for t in soup.find_all('table'):
            headers = [th.get_text(strip=True).lower() for th in t.find_all('th')]
            if any(x in headers for x in ['date', 'asset', 'amount', 'type']):
                table = t
                break
    
    if not table:
        raise ValueError("No transaction table found in MHTML file.")

    # Extract headers
    headers = [th.get_text(strip=True) for th in table.find_all('th')]
    
    # Extract rows
    rows = []
    for tr in table.find_all('tr')[1:]:  # Skip header row
        cells = tr.find_all('td')
        if len(cells) == len(headers):
            rows.append([cell.get_text(strip=True) for cell in cells])
            
    df = pd.DataFrame(rows, columns=headers)
    return df

def normalize_mhtml_data(df: pd.DataFrame) -> list[UnifiedTransaction]:
    """
    Normalizes the extracted DataFrame into a list of UnifiedTransaction objects.
    Assumes standard CoinLedger columns or similar.
    """
    transactions = []
    
    # Map columns (basic mapping, can be enhanced with AI later if needed)
    # CoinLedger typical columns: Date, Type, Asset, Amount, Currency, Price, Fee, TxHash
    
    col_map = {
        'date': next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), None),
        'type': next((c for c in df.columns if 'type' in c.lower()), None),
        'asset': next((c for c in df.columns if 'asset' in c.lower() or 'coin' in c.lower()), None),
        'amount': next((c for c in df.columns if 'amount' in c.lower()), None),
        'fee': next((c for c in df.columns if 'fee' in c.lower()), None),
        'tx_id': next((c for c in df.columns if 'hash' in c.lower() or 'id' in c.lower()), None),
    }
    
    for _, row in df.iterrows():
        try:
            # Parse Date (Assume UTC or convert)
            timestamp_str = row[col_map['date']]
            # Try parsing various formats
            try:
                timestamp = pd.to_datetime(timestamp_str).to_pydatetime()
            except:
                continue # Skip invalid dates
            
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=pytz.UTC) # Assume UTC if not specified
            else:
                timestamp = timestamp.astimezone(pytz.UTC)

            # Parse Amount and Fee
            amount_str = str(row[col_map['amount']]).replace(',', '')
            amount = float(amount_str) if amount_str else 0.0
            
            fee_str = str(row.get(col_map['fee'], '0')).replace(',', '')
            fee = float(fee_str) if fee_str and fee_str.lower() != 'nan' else 0.0

            tx = UnifiedTransaction(
                timestamp=timestamp,
                asset=row[col_map['asset']],
                amount=amount,
                fee=fee,
                tx_id=row.get(col_map['tx_id'], ''),
                tx_type=row[col_map['type']],
                source='CEX'
            )
            transactions.append(tx)
        except Exception as e:
            print(f"Error parsing row: {row} - {e}")
            continue
            
    return transactions
