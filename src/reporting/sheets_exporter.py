"""
Google Sheets Exporter for CoinLedger Universal Manual Import Template

This module handles:
1. Google Sheets API client initialization
2. Transaction pattern to template format mapping
3. Rune/Ordinal metadata fetching from APIs
4. Writing formatted data to Google Sheets
5. Applying conditional formatting for review items
"""

import os
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import requests
import time

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.models import UnifiedTransaction


# Google Sheets API Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
CREDENTIALS_PATH = 'credentials.json'

# API Configuration
UNISAT_API_BASE = "https://open-api.unisat.io/v1/indexer"
ORDINALS_API_BASE = "https://ordinals.com"

# Universal Import Template Headers (exact order per guideline)
TEMPLATE_HEADERS = [
    "Date (UTC)",
    "Platform",
    "Asset Sent",
    "Amount Sent",
    "Asset Received",
    "Amount Received",
    "Fee Currency",
    "Fee Amount",
    "Type",
    "Description",
    "TxHash"
]


class SheetsExporter:
    """Google Sheets exporter for CoinLedger Universal Import Template"""
    
    def __init__(self, credentials_path: str = CREDENTIALS_PATH):
        """Initialize Google Sheets API client"""
        self.credentials_path = credentials_path
        self.service = None
        self.unisat_api_key = os.getenv('UNISAT_API_KEY', '')
        
    def init_client(self) -> bool:
        """
        Initialize Google Sheets API client with service account credentials
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print(f"✓ Google Sheets API client initialized successfully")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize Google Sheets API client: {e}")
            return False
    
    def extract_sheet_id(self, sheet_url: str) -> Optional[str]:
        """
        Extract spreadsheet ID from Google Sheets URL
        
        Args:
            sheet_url: Full Google Sheets URL
            
        Returns:
            Spreadsheet ID or None if invalid URL
        """
        # Pattern: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit...
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            return match.group(1)
        return None
    
    def verify_sheet_access(self, sheet_id: str) -> bool:
        """
        Verify that service account has access to the sheet
        
        Args:
            sheet_id: Google Sheets spreadsheet ID
            
        Returns:
            bool: True if accessible, False otherwise
        """
        try:
            # Try to read sheet metadata
            self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            print(f"✓ Sheet access verified")
            return True
        except HttpError as e:
            print(f"✗ Sheet access denied: {e}")
            return False
    
    def format_date_utc(self, timestamp: datetime) -> str:
        """
        Format datetime to CoinLedger required format: mm/dd/yyyy hh:mm:ss
        
        Args:
            timestamp: Python datetime object (assumed UTC)
            
        Returns:
            Formatted date string
        """
        return timestamp.strftime("%m/%d/%Y %H:%M:%S")
    
    def format_amount(self, amount: float) -> str:
        """
        Format amount per CoinLedger guidelines (no currency symbols)
        
        Args:
            amount: Numeric amount
            
        Returns:
            Formatted amount string
        """
        # Remove any negative signs for display (direction determined by column)
        return str(abs(amount))
    
    def fetch_rune_metadata(self, tx_id: str) -> Optional[Dict]:
        """
        Fetch Rune metadata from UniSat API
        
        Args:
            tx_id: Bitcoin transaction ID
            
        Returns:
            Dict with rune_name, amount, divisibility or None if failed
        """
        if not tx_id or len(tx_id) != 64:
            return None
        
        # Try UniSat Rune Event endpoint first
        try:
            url = f"{UNISAT_API_BASE}/runes/event"
            headers = {"Accept": "application/json"}
            if self.unisat_api_key:
                headers['Authorization'] = f"Bearer {self.unisat_api_key}"
            
            params = {'txid': tx_id}
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and data.get('data'):
                    event_list = data['data']
                    if isinstance(event_list, dict) and 'detail' in event_list:
                        event_list = event_list['detail']
                    
                    if not isinstance(event_list, list):
                        event_list = [event_list] if event_list else []
                    
                    for event in event_list:
                        rune_name = event.get('rune') or event.get('runeName') or event.get('symbol')
                        amount = event.get('amount')
                        divisibility = event.get('divisibility', 0)
                        
                        if rune_name and amount:
                            return {
                                'rune_name': rune_name,
                                'amount': str(amount),
                                'divisibility': int(divisibility)
                            }
        except Exception as e:
            print(f"UniSat Rune Event API failed for {tx_id[:8]}: {e}")
        
        # Fallback to standard TX endpoint
        try:
            url = f"{UNISAT_API_BASE}/tx/{tx_id}"
            headers = {"Accept": "application/json"}
            if self.unisat_api_key:
                headers['Authorization'] = f"Bearer {self.unisat_api_key}"
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == 0 and data.get('data'):
                    tx_data = data['data']
                    
                    if 'vout' in tx_data:
                        for vout in tx_data['vout']:
                            if 'runes' in vout and len(vout['runes']) > 0:
                                r = vout['runes'][0]
                                return {
                                    'rune_name': r.get('runeName') or r.get('name'),
                                    'amount': r.get('amount', '0'),
                                    'divisibility': int(r.get('divisibility', 0))
                                }
        except Exception as e:
            print(f"UniSat TX API failed for {tx_id[:8]}: {e}")
        
        return None
    
    def fetch_ordinal_metadata(self, tx_id: str) -> Optional[Dict]:
        """
        Fetch Ordinal metadata (inscription ID)
        
        Args:
            tx_id: Bitcoin transaction ID
            
        Returns:
            Dict with inscription_id or None if failed
        """
        # For now, return None - Ordinals API integration can be added later
        # Most Ordinal transactions will use the tx_id as identifier
        return None
    
    def map_transaction_to_template(
        self, 
        tx: UnifiedTransaction, 
        pattern: Optional[Dict] = None
    ) -> Tuple[List[str], bool]:
        """
        Map a transaction to Universal Import Template row format
        
        Args:
            tx: UnifiedTransaction object
            pattern: Detected pattern dict (optional)
            
        Returns:
            Tuple of (row_data, needs_review)
            - row_data: List of values matching TEMPLATE_HEADERS
            - needs_review: Boolean indicating if row should be highlighted yellow
        """
        needs_review = False
        
        # Initialize row with empty values
        row = [""] * len(TEMPLATE_HEADERS)
        
        # Date (UTC) - Required
        row[0] = self.format_date_utc(tx.timestamp)
        
        # Platform - Optional
        row[1] = tx.source if tx.source != 'BLOCKCHAIN' else "Bitcoin Blockchain"
        
        # TxHash - Optional
        row[10] = tx.tx_id if tx.tx_id else ""
        
        # Map based on pattern if available
        if pattern:
            pattern_type = pattern.get('pattern', '')
            
            if pattern_type == 'MINT_BUY':
                # Trade: BTC → Rune/Ordinal
                row[2] = "BTC"  # Asset Sent
                row[3] = self.format_amount(abs(tx.amount))  # Amount Sent
                
                # Try to fetch Rune metadata
                rune_data = self.fetch_rune_metadata(tx.tx_id) if tx.tx_id else None
                if rune_data:
                    row[4] = rune_data['rune_name']  # Asset Received
                    row[5] = rune_data['amount']  # Amount Received
                else:
                    # Use placeholder and mark for review
                    row[4] = "Runes_#"
                    row[5] = "1"
                    needs_review = True
                
                row[8] = "Trade"  # Type
                row[9] = "Mint/Buy Rune or Ordinal"  # Description
            
            elif pattern_type == 'BULK_MINT':
                # Trade: BTC → Multiple Runes/Ordinals
                row[2] = "BTC"
                row[3] = self.format_amount(abs(tx.amount))
                
                rune_data = self.fetch_rune_metadata(tx.tx_id) if tx.tx_id else None
                if rune_data:
                    row[4] = rune_data['rune_name']
                    row[5] = rune_data['amount']
                else:
                    row[4] = "Runes_#"
                    row[5] = "1"
                    needs_review = True
                
                row[8] = "Trade"
                row[9] = "Bulk Mint - Multiple Runes/Ordinals"
            
            elif pattern_type == 'FIAT_ONRAMP':
                # Trade: Fiat → BTC
                # Asset Sent is empty (fiat)
                row[4] = "BTC"  # Asset Received
                row[5] = self.format_amount(tx.amount)  # Amount Received
                row[8] = "Trade"
                row[9] = "Fiat On-Ramp Purchase"
            
            elif pattern_type == 'SALE':
                # Trade: Rune/Ordinal → BTC
                rune_data = self.fetch_rune_metadata(tx.tx_id) if tx.tx_id else None
                if rune_data:
                    row[2] = rune_data['rune_name']  # Asset Sent
                    row[3] = rune_data['amount']  # Amount Sent
                else:
                    row[2] = "Ordinals_#"
                    row[3] = "1"
                    needs_review = True
                
                row[4] = "BTC"  # Asset Received
                row[5] = self.format_amount(tx.amount)  # Amount Received
                row[8] = "Trade"
                row[9] = "Sale of Rune/Ordinal"
            
            elif pattern_type == 'RUNE_RECEIVE':
                # Income: Airdrop/Gift
                rune_data = self.fetch_rune_metadata(tx.tx_id) if tx.tx_id else None
                if rune_data:
                    row[4] = rune_data['rune_name']  # Asset Received
                    row[5] = rune_data['amount']  # Amount Received
                else:
                    row[4] = "Runes_#"
                    row[5] = "1"
                    needs_review = True
                
                row[8] = "Airdrop"  # Type
                row[9] = "Received Rune/Ordinal"
            
            elif pattern_type == 'GAS_FEE':
                # Withdrawal: Fee only
                row[2] = "BTC"  # Asset Sent
                row[3] = self.format_amount(abs(tx.amount))  # Amount Sent
                row[8] = "Withdrawal"  # Type
                row[9] = "Network Fee"
            
            elif pattern_type == 'SELF_TRANSFER':
                # Skip - non-taxable
                return None, False
        
        else:
            # No pattern detected - basic mapping
            if tx.tx_type in ['Deposit', 'Receive']:
                row[4] = tx.asset  # Asset Received
                row[5] = self.format_amount(tx.amount)  # Amount Received
                row[8] = "Deposit"
                row[9] = "Blockchain Deposit"
            elif tx.tx_type in ['Withdrawal', 'Send']:
                row[2] = tx.asset  # Asset Sent
                row[3] = self.format_amount(abs(tx.amount))  # Amount Sent
                row[8] = "Withdrawal"
                row[9] = "Blockchain Withdrawal"
        
        return row, needs_review
    
    def write_to_sheet(
        self, 
        sheet_id: str, 
        data: List[List[str]], 
        review_indices: List[int],
        sheet_name: str = "Sheet1"
    ) -> bool:
        """
        Write data to Google Sheets and apply formatting
        
        Args:
            sheet_id: Google Sheets spreadsheet ID
            data: List of rows (each row is a list of values)
            review_indices: List of row indices that need yellow highlighting
            sheet_name: Name of the sheet tab (default: Sheet1)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Append data to sheet
            range_name = f"{sheet_name}!A:K"  # A-K covers all 11 columns
            
            body = {
                'values': data
            }
            
            print(f"Attempting to write {len(data)} rows to sheet {sheet_id}")
            print(f"First row sample: {data[0] if data else 'No data'}")
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            print(f"✓ Wrote {len(data)} rows to Google Sheets")
            print(f"API Response: {result}")
            
            # Apply yellow highlighting to review rows
            if review_indices:
                self.apply_review_highlighting(sheet_id, review_indices, sheet_name)
            
            return True
            
        except HttpError as e:
            print(f"✗ Failed to write to Google Sheets")
            print(f"Error Status: {e.resp.status if hasattr(e, 'resp') else 'Unknown'}")
            print(f"Error Reason: {e.reason if hasattr(e, 'reason') else 'Unknown'}")
            print(f"Error Details: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"✗ Unexpected error writing to Google Sheets: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def apply_review_highlighting(
        self, 
        sheet_id: str, 
        row_indices: List[int],
        sheet_name: str = "Sheet1"
    ) -> bool:
        """
        Apply yellow background color to rows requiring review
        
        Args:
            sheet_id: Google Sheets spreadsheet ID
            row_indices: List of row indices (0-based) to highlight
            sheet_name: Name of the sheet tab
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get sheet ID (not spreadsheet ID)
            sheet_metadata = self.service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheets = sheet_metadata.get('sheets', [])
            target_sheet_id = 0
            
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    target_sheet_id = sheet['properties']['sheetId']
                    break
            
            # Build batch update request for yellow highlighting
            requests = []
            for row_idx in row_indices:
                requests.append({
                    'repeatCell': {
                        'range': {
                            'sheetId': target_sheet_id,
                            'startRowIndex': row_idx,
                            'endRowIndex': row_idx + 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 11  # All columns
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {
                                    'red': 1.0,
                                    'green': 1.0,
                                    'blue': 0.0
                                }
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                })
            
            if requests:
                body = {'requests': requests}
                self.service.spreadsheets().batchUpdate(
                    spreadsheetId=sheet_id,
                    body=body
                ).execute()
                
                print(f"✓ Applied yellow highlighting to {len(row_indices)} rows")
            
            return True
            
        except HttpError as e:
            print(f"✗ Failed to apply highlighting: {e}")
            return False


def export_transactions_to_sheets(
    transactions: List[UnifiedTransaction],
    patterns: List[Dict],
    sheet_url: str
) -> Dict:
    """
    Main export function - analyzes transactions and exports to Google Sheets
    
    Args:
        transactions: List of UnifiedTransaction objects
        patterns: List of detected pattern dicts
        sheet_url: Google Sheets URL
        
    Returns:
        Dict with status, row_count, review_count, errors
    """
    exporter = SheetsExporter()
    
    # Initialize client
    if not exporter.init_client():
        return {
            'status': 'error',
            'message': 'Failed to initialize Google Sheets API client'
        }
    
    # Extract sheet ID
    sheet_id = exporter.extract_sheet_id(sheet_url)
    if not sheet_id:
        return {
            'status': 'error',
            'message': 'Invalid Google Sheets URL'
        }
    
    # Verify access
    if not exporter.verify_sheet_access(sheet_id):
        return {
            'status': 'error',
            'message': 'Cannot access Google Sheet. Ensure service account has Editor permissions.'
        }
    
    # Map transactions to template rows
    rows = []
    review_indices = []
    
    # Create pattern lookup by transaction ID and timestamp
    pattern_map = {}
    for pattern in patterns:
        affected_txs = pattern.get('affected_transactions', [])
        for tx in affected_txs:
            # Create unique key for each transaction
            if hasattr(tx, 'tx_id') and hasattr(tx, 'timestamp'):
                key = f"{tx.tx_id}_{tx.timestamp.isoformat()}"
                pattern_map[key] = pattern
    
    print(f"Created pattern map with {len(pattern_map)} transaction mappings")
    
    for tx in transactions:
        # Try to find matching pattern
        key = f"{tx.tx_id}_{tx.timestamp.isoformat()}"
        pattern = pattern_map.get(key)
        
        row_data, needs_review = exporter.map_transaction_to_template(tx, pattern)
        
        if row_data:  # Skip None (e.g., SELF_TRANSFER)
            rows.append(row_data)
            if needs_review:
                review_indices.append(len(rows) - 1)
    
    print(f"Mapped {len(rows)} transactions to template rows ({len(review_indices)} need review)")
    
    # Write to sheet
    if not exporter.write_to_sheet(sheet_id, rows, review_indices):
        return {
            'status': 'error',
            'message': 'Failed to write data to Google Sheets'
        }
    
    return {
        'status': 'success',
        'row_count': len(rows),
        'review_count': len(review_indices),
        'message': f'Successfully exported {len(rows)} transactions ({len(review_indices)} need review)'
    }

