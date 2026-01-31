"""
Ordinals/Runes Pattern Detection for Bitcoin Tax Correction

Detects 5 specific patterns where CoinLedger misclassifies Ordinals/Runes transactions:
1. Mint/Buy: Withdrawal + Dust Deposit
2. Gas Fee: Small unpaired withdrawal
3. Sale: Large unpaired deposit
4. Self Transfer: Between own wallets
5. Bulk Mint: 1 withdrawal + multiple dust deposits

Reference: ENHANCED_RECONCILIATION_LOGIC.md
"""

from typing import List, Dict, Optional, Tuple
from datetime import timedelta
from src.models import UnifiedTransaction

# Dust thresholds in BTC
DUST_THRESHOLDS = {
    "primary": 0.00000546,    # 546 sats (most common)
    "secondary": 0.00000330,  # 330 sats
    "max": 0.00001            # 10,000 sats (flexible upper bound)
}

def is_dust(amount: float) -> bool:
    """Check if amount is considered dust (Ordinal/Rune wrapper)"""
    return abs(amount) <= DUST_THRESHOLDS["max"]

def get_ordiscan_link(tx_id: str) -> Optional[str]:
    """
    Generate Ordiscan URL for transaction verification.
    Only returns a link for real blockchain transaction hashes.
    Returns None for CEX-generated identifiers (e.g., XVERSE_...).
    """
    if not tx_id:
        return None
    
    # Check if this is a fake CEX identifier
    if tx_id.startswith('XVERSE_') or tx_id.startswith('CEX_') or '_' in tx_id[:20]:
        return None
    
    # Check if it looks like a real Bitcoin tx hash (64 hex characters)
    if len(tx_id) == 64 and all(c in '0123456789abcdefABCDEF' for c in tx_id):
        return f"https://ordiscan.com/tx/{tx_id}"
    
    return None

def group_transactions_by_txid(transactions: List[UnifiedTransaction]) -> Dict[str, List[UnifiedTransaction]]:
    """Group transactions by TxID for pattern detection"""
    groups = {}
    
    for tx in transactions:
        if tx.tx_id:
            if tx.tx_id not in groups:
                groups[tx.tx_id] = []
            groups[tx.tx_id].append(tx)
    
    return groups

def group_transactions_by_time(transactions: List[UnifiedTransaction], window_minutes: int = 5) -> Dict[str, List[UnifiedTransaction]]:
    """Group transactions by time window (for transactions without TxID)"""
    groups = {}
    
    for tx in transactions:
        # Round to time buckets
        time_key = int(tx.timestamp.timestamp() / (window_minutes * 60))
        key = f"time_{time_key}"
        
        if key not in groups:
            groups[key] = []
        groups[key].append(tx)
    
    return groups

def detect_mint_buy_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    Scenario 1: Mint/Buy Pattern
    Pattern: [Withdrawal (large) + Deposit (dust)] in same TxID/timeframe
    
    CoinLedger Error: Separate Withdrawal + Deposit, dust appears as income
    Reality: Withdrawal = cost, Deposit = wrapper for Ordinal/Rune
    """
    # Separate by type
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: withdrawal(s) exist + all deposits are dust
    if withdrawals and deposits and all(is_dust(d.amount) for d in deposits):
        # Single mint/buy
        if len(deposits) == 1:
            return {
                "pattern": "MINT_BUY",
                "confidence": 0.9,
                "severity": "HIGH",
                "tax_impact": "ESTABLISHES_COST_BASIS",
                "affected_transactions": tx_group,
                "corrections": [
                    {
                        "tx": deposits[0],
                        "action": "IGNORE",
                        "reason": "Dust wrapper for Ordinal/Rune (not taxable income)",
                        "warning": "⚠️ Do NOT delete - mark as 'Ignored' in CoinLedger"
                    },
                    {
                        "tx": withdrawals[0],
                        "action": "CHANGE_TO_TRADE",
                        "sent_asset": "BTC",
                        "sent_amount": abs(withdrawals[0].amount),
                        "received_asset": "ORDINAL/RUNE",
                        "received_quantity": 1,
                        "ordiscan_link": get_ordiscan_link(deposits[0].tx_id) if deposits[0].tx_id else None,
                        "requires_ordiscan": True,
                        "transaction": deposits[0]  # Include blockchain deposit for asset tags
                    }
                ]
            }
    
    return None

def detect_bulk_mint_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    Scenario 5: Bulk Mint Pattern
    Pattern: [Withdrawal 1x + Deposit Nx] - one withdrawal, multiple dust deposits
    
    CoinLedger Error: Multiple deposits appear as separate income
    Reality: Minting multiple Ordinals/Runes in one transaction
    """
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: 1 withdrawal + multiple dust deposits
    if len(withdrawals) == 1 and len(deposits) > 1:
        if all(is_dust(d.amount) for d in deposits):
            # Find first blockchain deposit for Ordiscan link and metadata
            blockchain_deposit = next((d for d in deposits if d.source == 'BLOCKCHAIN'), deposits[0])
            
            return {
                "pattern": "BULK_MINT",
                "confidence": 0.95,
                "severity": "HIGH",
                "tax_impact": "ESTABLISHES_COST_BASIS",
                "affected_transactions": tx_group,
                "corrections": [
                    *[{
                        "tx": d,
                        "action": "IGNORE",
                        "reason": f"Dust wrapper {i+1}/{len(deposits)} for bulk mint",
                        "warning": "⚠️ Do NOT delete - mark as 'Ignored' in CoinLedger"
                    } for i, d in enumerate(deposits)],
                    {
                        "tx": withdrawals[0],
                        "action": "CHANGE_TO_TRADE",
                        "sent_asset": "BTC",
                        "sent_amount": abs(withdrawals[0].amount),
                        "received_asset": "ORDINAL/RUNE",
                        "received_quantity": len(deposits),
                        "ordiscan_link": get_ordiscan_link(blockchain_deposit.tx_id) if blockchain_deposit.tx_id else None,
                        "requires_ordiscan": True,
                        "transaction": blockchain_deposit  # Use blockchain deposit for asset tags
                    }
                ]
            }
    
    return None

def detect_gas_fee_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    Scenario 2: Gas Fee Pattern
    Pattern: [Withdrawal (small)] with no matching Deposit
    
    CoinLedger Error: Records as Withdrawal (potential taxable event)
    Reality: Network fee for failed transaction or inscription
    """
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: small withdrawal only, no deposits
    if withdrawals and not deposits:
        if abs(withdrawals[0].amount) < 0.0005:  # Less than 50,000 sats
            return {
                "pattern": "GAS_FEE",
                "confidence": 0.8,
                "severity": "LOW",
                "tax_impact": "TAX_DEDUCTIBLE",
                "affected_transactions": tx_group,
                "corrections": [{
                    "tx": withdrawals[0],
                    "action": "CHANGE_TO_FEE",
                    "reason": "Network cost without asset acquisition - tax deductible expense"
                }]
            }
    
    return None

def detect_sale_pattern(tx_group: List[UnifiedTransaction], my_wallets: List[str]) -> Optional[Dict]:
    """
    Scenario 3: Sale Pattern
    Pattern: [Deposit (large)] with no matching Withdrawal
    
    CoinLedger Error: Records as simple Deposit (not taxable)
    Reality: Proceeds from selling Ordinal/Rune
    """
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: deposit only, not dust, not from own wallet
    if deposits and not withdrawals:
        if not is_dust(deposits[0].amount):
            # Try to extract asset name from metadata
            deposit_tx = deposits[0]
            asset_name = "ORDINAL/RUNE (specify which asset was sold)"
            
            # Check if we have metadata about what was sold
            if hasattr(deposit_tx, 'metadata') and deposit_tx.metadata:
                if deposit_tx.metadata.get('inscription_id'):
                    asset_name = f"Ordinal {deposit_tx.metadata['inscription_id'][:16]}..."
                elif deposit_tx.metadata.get('rune_name'):
                    asset_name = deposit_tx.metadata['rune_name']
                elif deposit_tx.metadata.get('asset_type') == 'ORDINAL':
                    asset_name = "Ordinal (check transaction details)"
                elif deposit_tx.metadata.get('asset_type') == 'RUNE':
                    asset_name = "Rune (check transaction details)"
            
            return {
                "pattern": "SALE",
                "confidence": 0.7,
                "severity": "HIGH",
                "tax_impact": "TAXABLE_INCOME",
                "affected_transactions": tx_group,
                "corrections": [{
                    "tx": deposits[0],
                    "action": "CHANGE_TO_TRADE",
                    "sent_asset": asset_name,
                    "sent_amount": "USER_INPUT_REQUIRED",
                    "received_asset": "BTC",
                    "received_amount": deposits[0].amount,
                    "ordiscan_link": get_ordiscan_link(deposits[0].tx_id) if deposits[0].tx_id else None,
                    "requires_user_input": True,
                    "reason": "Profit from selling Ordinal/Rune - taxable event",
                    "transaction": deposits[0]  # Include deposit for asset tags
                }]
            }
    
    return None

def detect_self_transfer_pattern(tx_group: List[UnifiedTransaction], my_wallets: List[str]) -> Optional[Dict]:
    """
    Scenario 4: Self Transfer Pattern
    Pattern: [Withdrawal A + Deposit B] between own wallets, similar amounts
    
    CoinLedger Error: Records as two separate taxable events
    Reality: Moving funds between own wallets (non-taxable)
    """
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: 1 withdrawal + 1 deposit, similar amounts
    if len(withdrawals) == 1 and len(deposits) == 1:
        w, d = withdrawals[0], deposits[0]
        
        # Check if amounts are similar (within 0.0001 BTC for fees)
        if abs(abs(w.amount) - d.amount) < 0.0001:
            return {
                "pattern": "SELF_TRANSFER",
                "confidence": 0.85,
                "severity": "MEDIUM",
                "tax_impact": "NON_TAXABLE",
                "affected_transactions": tx_group,
                "corrections": [{
                    "txs": [w, d],
                    "action": "MERGE_AS_TRANSFER",
                    "reason": "Moving funds between own wallets - not a taxable event"
                }]
            }
    
    return None

def detect_patterns(tx_group: List[UnifiedTransaction], my_wallets: List[str] = None) -> Optional[Dict]:
    """
    Main pattern detection function - tries all 5 scenarios in priority order
    
    Priority:
    1. Bulk Mint (most specific)
    2. Mint/Buy
    3. Self Transfer
    4. Gas Fee
    5. Sale (least specific, requires user input)
    """
    if my_wallets is None:
        my_wallets = []
    
    # Try patterns in priority order
    pattern = detect_bulk_mint_pattern(tx_group)
    if pattern:
        return pattern
    
    pattern = detect_mint_buy_pattern(tx_group)
    if pattern:
        return pattern
    
    pattern = detect_self_transfer_pattern(tx_group, my_wallets)
    if pattern:
        return pattern
    
    pattern = detect_gas_fee_pattern(tx_group)
    if pattern:
        return pattern
    
    pattern = detect_sale_pattern(tx_group, my_wallets)
    if pattern:
        return pattern
    
    return None
