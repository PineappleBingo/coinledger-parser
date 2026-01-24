import requests
import json
from datetime import datetime
from typing import List, Optional
from src.models import UnifiedTransaction
from src.config import QUICKNODE_RPC_URL

class BlockchainClient:
    """
    Client to fetch transactions from blockchain via RPC.
    Note: Standard JSON-RPC (eth_getLogs) requires block ranges. 
    For a full history, an indexer API is usually preferred.
    This implementation provides a basic structure.
    """
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or QUICKNODE_RPC_URL
        
    def fetch_transactions(self, wallet_address: str, chain: str = 'ethereum') -> List[UnifiedTransaction]:
        """
        Fetches transactions for a wallet address.
        """
        if not self.rpc_url:
            print("Warning: No RPC URL configured. Returning empty list.")
            return []

        # TODO: Implement actual RPC calls or Indexer API calls here.
        # For 'Track B' (local/free), fetching *all* history via raw RPC is complex/slow.
        # We will simulate this or expect the user to provide a 'blockchain export' for now
        # if we strictly follow the 'Free RPC' constraint without an indexer.
        
        # Placeholder for actual implementation
        print(f"Fetching transactions for {wallet_address} on {chain} via {self.rpc_url}...")
        
        # In a real implementation, we would:
        # 1. Get current block number
        # 2. Iterate backwards or use eth_getLogs for Transfer events
        # 3. Parse logs/blocks to UnifiedTransaction
        
        return []

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
