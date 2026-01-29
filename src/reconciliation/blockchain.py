import requests
import json
from datetime import datetime
from typing import List, Optional
import pytz
from src.models import UnifiedTransaction
from src.config import QUICKNODE_RPC_URL

class BlockchainClient:
    """
    Client to fetch transactions from blockchain.
    Uses Blockstream API for Bitcoin (free, supports all address types).
    """
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or QUICKNODE_RPC_URL
        self.blockstream_api = "https://blockstream.info/api"
        
    def fetch_transactions(self, wallet_address: str, chain: str = 'bitcoin') -> List[UnifiedTransaction]:
        """
        Fetches transactions for a wallet address.
        Supports Bitcoin addresses: bc1p (Taproot), bc1q (SegWit), legacy (1xxx, 3xxx)
        """
        print(f"Fetching transactions for {wallet_address} on {chain}...")
        
        # For Bitcoin, use Blockstream API
        if chain.lower() in ['bitcoin', 'btc']:
            return self._fetch_bitcoin_transactions(wallet_address)
        else:
            print(f"Warning: Chain '{chain}' not yet implemented. Returning empty list.")
            return []

    def _fetch_bitcoin_transactions(self, address: str) -> List[UnifiedTransaction]:
        """
        Fetches Bitcoin transactions using Blockstream API with pagination.
        Supports all Bitcoin address formats.
        Detects Ordinals and Runes protocols.
        Fetches ALL transactions, not just the first 25.
        """
        try:
            transactions = []
            last_seen_txid = None
            page = 1
            
            while True:
                # Build URL with pagination
                if last_seen_txid:
                    url = f"{self.blockstream_api}/address/{address}/txs/chain/{last_seen_txid}"
                else:
                    url = f"{self.blockstream_api}/address/{address}/txs"
                
                print(f"Fetching page {page} from: {url}")
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                txs_data = response.json()
                
                # FIXED: Check for empty response instead of < 25
                if not txs_data or len(txs_data) == 0:
                    print(f"No more transactions found. Total pages: {page - 1}")
                    break
                
                print(f"Received {len(txs_data)} transactions on page {page}")
                
                for tx in txs_data:
                    # Determine if this is incoming or outgoing
                    tx_id = tx.get('txid', '')
                    
                    # Get timestamp
                    block_time = tx.get('status', {}).get('block_time', 0)
                    if block_time == 0:
                        # Unconfirmed transaction, use current time
                        timestamp = datetime.now(tz=pytz.UTC)
                    else:
                        timestamp = datetime.fromtimestamp(block_time, tz=pytz.UTC)
                    
                    # Calculate net amount for this address
                    inputs_from_address = sum(
                        vin.get('prevout', {}).get('value', 0) 
                        for vin in tx.get('vin', []) 
                        if vin.get('prevout', {}).get('scriptpubkey_address') == address
                    )
                    
                    outputs_to_address = sum(
                        vout.get('value', 0) 
                        for vout in tx.get('vout', []) 
                        if vout.get('scriptpubkey_address') == address
                    )
                    
                    # Net amount in satoshis, convert to BTC
                    net_amount_satoshis = outputs_to_address - inputs_from_address
                    net_amount_btc = net_amount_satoshis / 100_000_000
                    
                    # Determine transaction type
                    if net_amount_btc > 0:
                        tx_type = "Deposit"
                    elif net_amount_btc < 0:
                        tx_type = "Withdrawal"
                    else:
                        tx_type = "Internal"  # Self-transfer or complex tx
                    
                    # Calculate fee (total fee divided by number of inputs, rough estimate)
                    fee_satoshis = tx.get('fee', 0)
                    fee_btc = fee_satoshis / 100_000_000
                    
                    # ENHANCED: Detect Ordinals and Runes
                    asset_type = self._detect_asset_type(tx, outputs_to_address)
                    
                    unified_tx = UnifiedTransaction(
                        timestamp=timestamp,
                        asset='BTC',
                        amount=net_amount_btc,
                        fee=fee_btc if net_amount_btc < 0 else 0,  # Only count fee for outgoing
                        tx_id=tx_id,
                        tx_type=tx_type,
                        source='BLOCKCHAIN',
                        price_krw=None,
                        metadata={'asset_type': asset_type}  # Add asset type metadata
                    )
                    
                    transactions.append(unified_tx)
                
                # Set last_seen_txid for next page
                last_seen_txid = txs_data[-1].get('txid')
                page += 1
                
                # Safety limit to prevent infinite loops
                if page > 1000:
                    print("Warning: Reached safety limit of 1000 pages")
                    break
            
            # Sort by timestamp descending (newest first)
            transactions.sort(key=lambda x: x.timestamp, reverse=True)
            
            print(f"Successfully parsed {len(transactions)} Bitcoin transactions across {page - 1} pages")
            return transactions
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching Bitcoin transactions: {e}")
            return []
        except Exception as e:
            print(f"Error parsing Bitcoin transactions: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _detect_asset_type(self, tx: dict, outputs_to_address: int) -> str:
        """
        Detect if transaction involves Ordinals or Runes protocols.
        
        Ordinals: Typically dust amounts (546 sats, 330 sats, etc.)
        Runes: Uses OP_RETURN with specific protocol markers (0x52 = 'R')
        """
        # Check for Runes protocol
        # Runes uses OP_RETURN outputs with protocol marker
        for vout in tx.get('vout', []):
            scriptpubkey = vout.get('scriptpubkey', '')
            scriptpubkey_type = vout.get('scriptpubkey_type', '')
            
            # Runes protocol check: OP_RETURN starting with 0x52 ('R')
            if scriptpubkey_type == 'op_return':
                # Check if it's a Runes protocol transaction
                if scriptpubkey.startswith('6a5d'):  # OP_RETURN + OP_PUSHDATA1
                    # Runes protocol marker check
                    # Format: OP_RETURN OP_PUSHDATA1 [length] 'R' [rune_data]
                    return 'RUNE'
        
        # Check for Ordinals (dust amounts)
        # Ordinals typically use 546 sats (0.00000546 BTC) or 330 sats
        if outputs_to_address > 0:
            if outputs_to_address == 546 or outputs_to_address == 330 or outputs_to_address <= 1000:
                return 'ORDINAL'
        
        # Regular BTC transaction
        return 'BTC'

    def _make_rpc_call(self, method: str, params: list):
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(self.rpc_url, headers=headers, data=json.dumps(payload))
            return response.json()
        except Exception as e:
            print(f"RPC call failed: {e}")
            return None
