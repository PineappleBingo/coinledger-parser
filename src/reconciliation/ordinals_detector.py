"""
Ordinals/Runes Pattern Detection for Bitcoin Tax Correction

Detects 6 specific patterns where CoinLedger misclassifies Ordinals/Runes transactions:
1. Bulk Mint: 1 withdrawal + multiple dust deposits
2. Mint/Buy: Withdrawal + Dust Deposit
3. Self Transfer: Between own wallets
4. Gas Fee: Small unpaired withdrawal
5. Rune/Ordinal Receive: Deposit with Rune/Ordinal metadata (NOT taxable)
6. Sale: Large unpaired deposit (BTC payment from selling Ordinal/Rune)

Reference: ENHANCED_RECONCILIATION_LOGIC.md
"""

from typing import List, Dict, Optional, Tuple
from datetime import timedelta
from datetime import timedelta
from src.models import UnifiedTransaction
from src.reconciliation.runestone_parser import RunestoneParser

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

def get_rune_links(tx_id: str, rune_name: str = None) -> Dict[str, str]:
    """
    Generate Rune verification URLs for transaction.
    Returns links to Ordinals.com and Hiro for Rune verification.
    """
    links = {}
    
    if tx_id and len(tx_id) == 64:
        # UniSat transaction link (Preferred for Runes)
        links['unisat'] = f"https://unisat.io/tx/{tx_id}"
        
        # Ordiscan link
        links['ordiscan'] = f"https://ordiscan.com/tx/{tx_id}"
    
    if rune_name and not rune_name.startswith('RUNE_'):
        # Ordinals.com Rune page (only if we have real Rune name, not placeholder)
        links['ordinals'] = f"https://ordinals.com/rune/{rune_name}"
    
    return links

def is_potential_marketplace_tx(tx: UnifiedTransaction) -> bool:
    """
    Check if a blockchain transaction looks like a Marketplace/Magic Eden trade.
    Heuristics:
    1. Has Witness Data (SegWit/Taproot)
    2. Multiple Inputs/Outputs (PSBT structure common in ME)
    3. Not a simple self-transfer (1 in, 2 out)
    """
    if not tx.witness_data:
        return False
        
    # Magic Eden / Marketplaces usually use PSBTs which result in multiple inputs signing
    # A simple transfer usually has 1 or 2 inputs.
    # A marketplace trade often has: Seller Input + Buyer Input + Service Fee Input?
    # Actually, simpler heuristic:
    # If it has witness data and is NOT a simple 1-input-2-output transfer, it's a candidate.
    
    # We don't have input count in UnifiedTransaction (only net amount/fee). 
    # But we can check witness data length.
    # Standard Taproot/Segwit spend might have 1 witness item (signature).
    # PSBT might have more.
    if len(tx.witness_data) >= 2:
        return True
        
    return False

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
                        "action": "CHANGE_TO_TRADE",
                        "sent_asset": "BTC",
                        "sent_amount": abs(withdrawals[0].amount),
                        "received_asset": "ORDINAL/RUNE",
                        "received_quantity": 1,
                        "ordiscan_link": get_ordiscan_link(deposits[0].tx_id) if deposits[0].tx_id else None,
                        "requires_ordiscan": True,
                        "transaction": deposits[0],
                        "verification_links": get_ordiscan_link(deposits[0].tx_id) if deposits[0].tx_id else None,
                        "mempool_link": f"https://mempool.space/tx/{deposits[0].tx_id}" if deposits[0].tx_id else None
                    },
                    {
                        "tx": withdrawals[0],
                        "action": "IGNORE",
                        "reason": "BTC payment for Ordinal/Rune mint (cost basis on companion row)",
                        "warning": "⚠️ Do NOT delete - mark as 'Ignored' in CoinLedger"
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
                    {
                        "tx": blockchain_deposit,
                        "action": "CHANGE_TO_TRADE",
                        "sent_asset": "BTC",
                        "sent_amount": abs(withdrawals[0].amount),
                        "received_asset": "ORDINAL/RUNE",
                        "received_quantity": len(deposits),
                        "ordiscan_link": get_ordiscan_link(blockchain_deposit.tx_id) if blockchain_deposit.tx_id else None,
                        "requires_ordiscan": True,
                        "transaction": blockchain_deposit,
                        "verification_links": get_ordiscan_link(blockchain_deposit.tx_id) if blockchain_deposit.tx_id else None,
                        "mempool_link": f"https://mempool.space/tx/{blockchain_deposit.tx_id}" if blockchain_deposit.tx_id else None
                    },
                    *[{
                        "tx": d,
                        "action": "IGNORE",
                        "reason": f"Dust wrapper {i+1}/{len(deposits)} for bulk mint",
                        "warning": "⚠️ Do NOT delete - mark as 'Ignored' in CoinLedger"
                    } for i, d in enumerate(deposits) if d is not blockchain_deposit],
                    {
                        "tx": withdrawals[0],
                        "action": "IGNORE",
                        "reason": "BTC payment for bulk Ordinal/Rune mint (cost basis on companion row)",
                        "warning": "⚠️ Do NOT delete - mark as 'Ignored' in CoinLedger"
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
                    "reason": "Network cost without asset acquisition - tax deductible expense",
                    "mempool_link": f"https://mempool.space/tx/{withdrawals[0].tx_id}" if withdrawals[0].tx_id else None
                }]
            }
    
    return None

def detect_sale_pattern(tx_group: List[UnifiedTransaction], my_wallets: List[str], all_blockchain_txs: List[UnifiedTransaction] = None) -> Optional[Dict]:
    """
    Scenario 3: Sale Pattern
    Pattern: [Deposit (large)] with no matching Withdrawal
    
    CoinLedger Error: Records as simple Deposit (not taxable)
    Reality: Proceeds from selling Ordinal/Rune
    """
    if all_blockchain_txs is None:
        all_blockchain_txs = []
        
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: deposit only, not dust, not from own wallet
    if deposits and not withdrawals:
        if not is_dust(deposits[0].amount):
            # Try to extract asset name from metadata
            deposit_tx = deposits[0]
            asset_name = "ORDINAL/RUNE (specify which asset was sold)"
            deposit_time = deposit_tx.timestamp
            
            # The deposit is BTC (payment), but we need to find the outgoing Ordinal/Rune
            # Search ALL blockchain transactions for an Ordinal withdrawal around the same time
            ordinal_tx = None
            
            # First, search in the current tx_group
            for tx in tx_group:
                if hasattr(tx, 'metadata') and tx.metadata:
                    if tx.metadata.get('asset_type') in ['ORDINAL', 'RUNE']:
                        ordinal_tx = tx
                        break
            
            # If not found in group, search ALL blockchain transactions within 48-hour window
            if not ordinal_tx and all_blockchain_txs:
                from datetime import timedelta
                time_window = timedelta(hours=48)
                
                for tx in all_blockchain_txs:
                    # Look for withdrawals with Ordinal/Rune metadata
                    if tx.tx_type in ['Withdrawal', 'Send']:
                        if hasattr(tx, 'metadata') and tx.metadata:
                            if tx.metadata.get('asset_type') in ['ORDINAL', 'RUNE']:
                                # Check if it's within the time window
                                time_diff = abs((tx.timestamp - deposit_time).total_seconds())
                                if time_diff < time_window.total_seconds():
                                    ordinal_tx = tx
                                    break
            
            # If we found an Ordinal/Rune transaction, use its metadata
            if ordinal_tx and hasattr(ordinal_tx, 'metadata') and ordinal_tx.metadata:
                if ordinal_tx.metadata.get('inscription_id'):
                    asset_name = f"Ordinal {ordinal_tx.metadata['inscription_id'][:16]}..."
                elif ordinal_tx.metadata.get('rune_name'):
                    asset_name = ordinal_tx.metadata['rune_name']
                elif ordinal_tx.metadata.get('asset_type') == 'ORDINAL':
                    asset_name = "Ordinal (check transaction details)"
                elif ordinal_tx.metadata.get('asset_type') == 'RUNE':
                    asset_name = "Rune (check transaction details)"
            # Fallback: check deposit metadata (less likely but possible)
            elif hasattr(deposit_tx, 'metadata') and deposit_tx.metadata:
                if deposit_tx.metadata.get('inscription_id'):
                    asset_name = f"Ordinal {deposit_tx.metadata['inscription_id'][:16]}..."
                elif deposit_tx.metadata.get('rune_name'):
                    asset_name = deposit_tx.metadata['rune_name']
                elif deposit_tx.metadata.get('asset_type') == 'ORDINAL':
                    asset_name = "Ordinal (check transaction details)"
                elif deposit_tx.metadata.get('asset_type') == 'RUNE':
                    asset_name = "Rune (check transaction details)"
            
            # Generate verification links
            verification_links = {}
            tx_for_links = ordinal_tx if ordinal_tx else deposits[0]
            
            if ordinal_tx and hasattr(ordinal_tx, 'metadata') and ordinal_tx.metadata:
                asset_type = ordinal_tx.metadata.get('asset_type')
                if asset_type == 'RUNE':
                    rune_name = ordinal_tx.metadata.get('rune_name', '')
                    verification_links = get_rune_links(ordinal_tx.tx_id, rune_name)
                elif asset_type == 'ORDINAL':
                    ordiscan_link = get_ordiscan_link(ordinal_tx.tx_id)
                    if ordiscan_link:
                        verification_links['ordiscan'] = ordiscan_link
            
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
                    "ordiscan_link": verification_links.get('ordiscan') or get_ordiscan_link(deposits[0].tx_id),
                    "hiro_link": verification_links.get('hiro'),
                    "ordinals_link": verification_links.get('ordinals'),
                    "requires_user_input": True,
                    "reason": "Profit from selling Ordinal/Rune - taxable event",
                    "transaction": ordinal_tx if ordinal_tx else deposits[0],  # Use Ordinal tx if found, else deposit
                    "mempool_link": f"https://mempool.space/tx/{deposits[0].tx_id}" if deposits[0].tx_id else None
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

def detect_patterns(tx_group: List[UnifiedTransaction], my_wallets: List[str] = None, all_blockchain_txs: List[UnifiedTransaction] = None) -> Optional[Dict]:
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
    if all_blockchain_txs is None:
        all_blockchain_txs = []
    
    # DEBUG: Log what group we're analyzing
    with open("debug_log.txt", "a") as f:
        f.write(f"\n=== detect_patterns CALLED ===\n")
        f.write(f"tx_group has {len(tx_group)} transactions:\n")
        for tx in tx_group:
            metadata_str = str(tx.metadata) if tx.metadata else "None"
            witness_len = len(tx.witness_data) if tx.witness_data else 0
            f.write(f"  - {tx.source}: {tx.tx_type} {tx.amount} {tx.asset} | metadata={metadata_str} | witness_len={witness_len}\n")
    
    # Try patterns in priority order
    
    # Priority 0a: Cross-Reference Magic Eden / Mint (Unmatched CEX + Loose Blockchain)
    # Check this FIRST to override generic "Fiat On-Ramp" logic for unmatched deposits
    pattern = detect_magic_eden_or_mint_cross_ref(tx_group, all_blockchain_txs)
    if pattern: 
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    # Priority 1: Bulk Mint (most specific - CEX Withdrawal + Multiple Dust Deposits)
    # MUST run before FIAT_ONRAMP to catch mint transactions
    pattern = detect_bulk_mint_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    # Priority 2: Mint/Buy (CEX Withdrawal + Single Dust Deposit)
    # MUST run before FIAT_ONRAMP to catch mint transactions
    pattern = detect_mint_buy_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern

    # Priority 3: Rune Cenotaph (Burn)
    pattern = detect_runes_cenotaph_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    # Priority 4: Fiat On-Ramp (Missing Blockchain Tx)
    # Now only catches truly unmatched deposits/withdrawals that aren't mints
    pattern = detect_fiat_onramp_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    pattern = detect_self_transfer_pattern(tx_group, my_wallets)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    pattern = detect_gas_fee_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    # Check for Isolated Marketplace Buy (Taproot wallet only)
    pattern = detect_isolated_marketplace_buy(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
        
    # Check for simple Rune/Ordinal RECEIVE before SALE
    # This prevents misclassifying Rune deposits as sales
    pattern = detect_rune_receive_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    pattern = detect_sale_pattern(tx_group, my_wallets, all_blockchain_txs)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern
    
    # BRC-20 Transfer
    pattern = detect_brc20_transfer_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern

    # Magic Eden / Marketplace Trade (Enhanced PSBT)
    pattern = detect_nft_trade_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern

    # Generic PSBT Swap (Partial)
    pattern = detect_psbt_pattern(tx_group)
    if pattern:
        with open("debug_log.txt", "a") as f:
            f.write(f"  -> MATCHED: {pattern.get('pattern')}\n")
        return pattern

    with open("debug_log.txt", "a") as f:
        f.write(f"  -> NO MATCH (returning None)\n")
    return None

def detect_fiat_onramp_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    V2 Pattern P0: Fiat On-Ramp
    Scenario: CEX shows a Deposit, but no Blockchain transaction was found (Unmatched).
    User likely bought crypto on the CEX/On-ramp.
    """
    # Check if this group only has CEX transactions
    has_blockchain = any(t.source == 'BLOCKCHAIN' for t in tx_group)
    
    if not has_blockchain:
        # All transactions are CEX deposits?
        cex_deposits = [t for t in tx_group if t.source == 'CEX' and t.tx_type in ['Deposit', 'Receive', 'Buy']]
        
        if cex_deposits:
            # P0 Refinement: Check asset type
            # If asset is not BTC (e.g. ORDI, SATS, RUNE), likely an asset transfer, not fiat on-ramp
            tx = cex_deposits[0]
            asset = tx.asset.upper()
            
            # Heuristic: Known BRC-20s or generic "RUNE" logic
            # If asset is BTC, assume potential Fiat On-Ramp
            is_btc_like = asset in ['BTC', 'BITCOIN', 'WBTC'] 
            
            if is_btc_like:
                return {
                    "pattern": "FIAT_ONRAMP",
                    "confidence": 0.8,
                    "severity": "MEDIUM", 
                    "tax_impact": "ESTABLISHES_COST_BASIS",
                    "affected_transactions": tx_group,
                    "corrections": [{
                        "tx": tx,
                        "action": "CHANGE_TO_BUY",
                        "reason": "Deposit without blockchain source - likely Fiat On-Ramp purchase",
                        "note": "Verify if you bought this with USD/Fiat. If so, ensure cost basis is set."
                    }]
                }
            else:
                # It's an asset (ORDI, SATS, etc.) but no blockchain tx found
                return {
                    "pattern": "UNMATCHED_ASSET_TRANSFER",
                    "confidence": 0.7,
                    "severity": "MEDIUM",
                    "tax_impact": "REVIEW_REQUIRED",
                    "affected_transactions": tx_group,
                    "corrections": [{
                        "tx": tx,
                        "action": "REVIEW",
                        "reason": f"Unmatched deposit of {asset}. Likely a wallet transfer, not a Fiat purchase.",
                        "note": "CoinLedger missed the blockchain source. Check if you transferred this from another wallet."
                    }]
                }
    return None

def detect_runes_cenotaph_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    V2 Pattern P2: Runes Cenotaph
    Scenario: Malformed Runes transaction which burns the assets.
    """
    blockchain_txs = [t for t in tx_group if t.source == 'BLOCKCHAIN']
    parser = RunestoneParser()
    
    for tx in blockchain_txs:
        # Placeholder logic based on Phase 2 plan (Unit tested parser availability):
        # In a real scenario we would pass raw payload.
        # Here we just want to ensure we return verification links if we DO match.
        pass 
        
    return None

def detect_brc20_transfer_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    V2 Pattern P4: BRC-20 Transfer Inscription
    Scenario: Witness data contains {"p":"brc-20", "op":"transfer"}.
    This is just the 'transfer inscription', not the actual movement.
    """
    for tx in tx_group:
        if hasattr(tx, 'witness_data') and tx.witness_data:
            for witness_item in tx.witness_data:
                try:
                    bytes_data = bytes.fromhex(witness_item)
                    text = bytes_data.decode('utf-8', errors='ignore')
                    if "brc-20" in text and "transfer" in text:
                         return {
                            "pattern": "BRC20_TRANSFER_INSCRIBE",
                            "confidence": 0.95,
                            "severity": "LOW",
                            "tax_impact": "NOT_TAXABLE",
                            "affected_transactions": tx_group,
                            "corrections": [{
                                "tx": tx,
                                "action": "IGNORE_OR_INTERNAL",
                                "reason": "BRC-20 Transfer Inscription - preparation step, not a taxable event yet",
                                "mempool_link": f"https://mempool.space/tx/{tx.tx_id}",
                                "ordiscan_link": get_ordiscan_link(tx.tx_id)
                            }]
                        }
                except:
                    continue
    return None

def detect_psbt_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    V2 Pattern P3: PSBT / Marketplace Swap
    Scenario: Multiple inputs with signatures (witnesses) indicating multiple parties.
    """
    # Use witness data count as simple heuristic for now
    for tx in tx_group:
         if tx.source == 'BLOCKCHAIN' and hasattr(tx, 'witness_data') and tx.witness_data:
             # Very rough heuristic: If we see many witness items, it *might* be multisig/PSBT
             if len(tx.witness_data) > 4: # Arbitrary threshold for complex tx
                 return {
                     "pattern": "POTENTIAL_MARKETPLACE_SWAP",
                     "confidence": 0.4, # Low confidence without deep SIGHASH analysis
                     "severity": "MEDIUM",
                     "tax_impact": "REVIEW_REQUIRED",
                     "affected_transactions": tx_group,
                     "corrections": [{
                         "tx": tx,
                         "action": "REVIEW",
                         "reason": "Complex transaction with multiple signatures - potential marketplace swap",
                         "mempool_link": f"https://mempool.space/tx/{tx.tx_id}"
                     }]
                 }
    return None
def detect_isolated_marketplace_buy(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    Scenario: User bought an Ordinal/Rune on a marketplace (like Magic Eden)
    but only connected their taproot (receiving) wallet to CoinLedger.
    
    Pattern: [Deposit of Dust containing Ordinal] WITH marketplace PSBT signatures/structure.
    
    CoinLedger Error: Records as a non-taxable Deposit (Income).
    Reality: It is a Purchase, establishing cost basis. The user needs to manually input the amount spent.
    """
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: single deposit, no withdrawal, is dust
    if len(deposits) == 1 and not withdrawals and is_dust(deposits[0].amount):
        deposit_tx = deposits[0]
        
        # Check if this deposit has Rune/Ordinal metadata
        if hasattr(deposit_tx, 'metadata') and deposit_tx.metadata:
            asset_type = deposit_tx.metadata.get('asset_type')
            
            if asset_type in ['ORDINAL', 'RUNE']:
                # Is it a complex PSBT?
                if is_potential_marketplace_tx(deposit_tx):
                    asset_name = "Unknown Asset"
                    
                    if asset_type == 'ORDINAL':
                        inscription_id = deposit_tx.metadata.get('inscription_id', '')
                        asset_name = f"Ordinal {inscription_id[:16]}..." if inscription_id else "Ordinal"
                    elif asset_type == 'RUNE':
                        rune_name = deposit_tx.metadata.get('rune_name', '')
                        asset_name = rune_name if rune_name else "Rune"
                    
                    # Generate verification links
                    verification_links = {}
                    if asset_type == 'RUNE':
                        rune_name = deposit_tx.metadata.get('rune_name', '')
                        verification_links = get_rune_links(deposit_tx.tx_id, rune_name)
                    elif asset_type == 'ORDINAL':
                        ordiscan_link = get_ordiscan_link(deposit_tx.tx_id)
                        if ordiscan_link:
                            verification_links['ordiscan'] = ordiscan_link

                    return {
                        "pattern": "MAGIC_EDEN_BUY_ISOLATED",
                        "confidence": 0.85,
                        "severity": "HIGH",
                        "tax_impact": "ESTABLISHES_COST_BASIS",
                        "affected_transactions": tx_group,
                        "corrections": [{
                            "tx": deposit_tx,
                            "action": "CHANGE_TO_BUY_ISOLATED",
                            "reason": f"Isolated Marketplace Trade - {asset_name} received via PSBT",
                            "note": "Payment wallet not connected! Please manually enter the BTC purchase price.",
                        }]
                    }
    return None

def detect_rune_receive_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    Scenario: Rune/Ordinal Receive Pattern
    Pattern: [Deposit with Rune/Ordinal metadata] - receiving a Rune/Ordinal, not a sale
    
    This is NOT taxable - only taxable when sold later
    """
    withdrawals = [t for t in tx_group if t.tx_type in ['Withdrawal', 'Send']]
    deposits = [t for t in tx_group if t.tx_type in ['Deposit', 'Receive']]
    
    # Check pattern: deposit only (no withdrawal)
    if deposits and not withdrawals:
        deposit_tx = deposits[0]
        
        # Check if this deposit has Rune/Ordinal metadata
        if hasattr(deposit_tx, 'metadata') and deposit_tx.metadata:
            asset_type = deposit_tx.metadata.get('asset_type')
            
            if asset_type in ['ORDINAL', 'RUNE']:
                # This is receiving a Rune/Ordinal, not a sale
                asset_name = "Unknown Asset"
                
                if asset_type == 'ORDINAL':
                    inscription_id = deposit_tx.metadata.get('inscription_id', '')
                    asset_name = f"Ordinal {inscription_id[:16]}..." if inscription_id else "Ordinal"
                elif asset_type == 'RUNE':
                    rune_name = deposit_tx.metadata.get('rune_name', '')
                    asset_name = rune_name if rune_name else "Rune"
                
                # Generate verification links
                verification_links = {}
                if asset_type == 'RUNE':
                    rune_name = deposit_tx.metadata.get('rune_name', '')
                    verification_links = get_rune_links(deposit_tx.tx_id, rune_name)
                elif asset_type == 'ORDINAL':
                    # For Ordinals, use ordiscan link
                    ordiscan_link = get_ordiscan_link(deposit_tx.tx_id)
                    if ordiscan_link:
                        verification_links['ordiscan'] = ordiscan_link
                
                return {
                    "pattern": "RUNE_RECEIVE",
                    "confidence": 0.95,
                    "severity": "LOW",
                    "tax_impact": "NOT_TAXABLE",
                    "affected_transactions": tx_group,
                    "corrections": [{
                        "tx": deposit_tx,
                        "action": "NO_ACTION_NEEDED",
                        "reason": f"Received {asset_name} - not taxable until sold",
                        "note": "This is an incoming Rune/Ordinal. No tax event occurs until you sell it.",
                        "transaction": deposit_tx,  # Include for asset tags and preview
                        "verification_links": verification_links,  # Add verification links
                        "ordiscan_link": verification_links.get('ordiscan'),  # For compatibility
                        "hiro_link": verification_links.get('hiro'),
                        "ordinals_link": verification_links.get('ordinals')
                    }]
                }
    
    return None

def detect_nft_trade_pattern(tx_group: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    V2 Pattern: NFT Marketplace Trade (Magic Eden, etc.)
    Replaces generic 'Swap' with specific 'Buy' or 'Sale' actions when clear.
    """
    # Needs to be a complex transaction (mix of inputs/outputs)
    if len(tx_group) < 2:
        return None
        
    # Calculate Net Changes for User
    net_btc = 0
    assets_received = []
    assets_sent = []
    
    for tx in tx_group:
        if tx.asset == 'BTC':
            net_btc += tx.amount
        else:
            if tx.amount > 0:
                assets_received.append(tx)
            else:
                assets_sent.append(tx)
                
    # Logic: Did we swap BTC for an Asset (Buy) or Asset for BTC (Sale)?
    
    # CASE 1: NFT BUY (User paid BTC, received Asset)
    # Net BTC must be negative (payment + fee)
    # Must have received at least one Asset
    if net_btc < 0 and len(assets_received) > 0 and len(assets_sent) == 0:
        asset_names = ", ".join([t.asset for t in assets_received])
        main_asset = assets_received[0]
        
        return {
            "pattern": "NFT_MARKETPLACE_BUY",
            "confidence": 0.9,
            "severity": "HIGH",
            "tax_impact": "ESTABLISHES_COST_BASIS",
            "affected_transactions": tx_group,
            "corrections": [{
                "tx": main_asset,
                "action": "CHANGE_TO_BUY",
                "reason": f"Bought {asset_names} on Marketplace (e.g. Magic Eden)",
                "note": f"Paid {abs(net_btc):.8f} BTC. Ensure cost basis is allocated to {asset_names}.",
                "verification_links": get_rune_links(main_asset.tx_id, main_asset.metadata.get('rune_name')) if main_asset.metadata.get('rune_name') else {},
                "ordiscan_link": get_ordiscan_link(main_asset.tx_id),
                "unisat_link": f"https://unisat.io/tx/{main_asset.tx_id}"
            }]
        }

    # CASE 2: NFT SALE (User sold Asset, received BTC)
    # Net BTC must be positive (revenue)
    # Must have sent at least one Asset
    if net_btc > 0 and len(assets_received) == 0 and len(assets_sent) > 0:
        asset_names = ", ".join([t.asset for t in assets_sent])
        main_asset = assets_sent[0]
        
        return {
            "pattern": "NFT_MARKETPLACE_SALE",
            "confidence": 0.9,
            "severity": "HIGH",
            "tax_impact": "TAXABLE_INCOME",
            "affected_transactions": tx_group,
            "corrections": [{
                "tx": main_asset,
                "action": "CHANGE_TO_TRADE",
                "sent_asset": asset_names,
                "sent_amount": abs(main_asset.amount),
                "received_asset": "BTC",
                "received_quantity": net_btc,
                "reason": f"Sold {asset_names} on Marketplace (e.g. Magic Eden)",
                "note": "Taxable event. Profit/Loss calculated against original cost basis.",
                "verification_links": get_rune_links(main_asset.tx_id, main_asset.metadata.get('rune_name')) if main_asset.metadata.get('rune_name') else {},
                "ordiscan_link": get_ordiscan_link(main_asset.tx_id),
                "unisat_link": f"https://unisat.io/tx/{main_asset.tx_id}"
            }]
        }
        
    return None

def detect_magic_eden_or_mint_cross_ref(tx_group: List[UnifiedTransaction], all_blockchain_txs: List[UnifiedTransaction]) -> Optional[Dict]:
    """
    V2 Pattern: Magic Eden / Mint Cross-Reference
    Scenario: Unmatched CEX/Wallet transactions that align with "loose" blockchain transactions.
    
    Problem: CEX says "Deposit 0.01 BTC" (Unmatched). CoinLedger sees "Fiat On-Ramp".
    Reality: It matches a nearby Blockchain "Withdrawal/Buy" (Mint or ME Buy) that wasn't grouped.
    """
    
    # DEBUG: Log entry point
    with open("debug_log.txt", "a") as f:
        f.write(f"\n=== detect_magic_eden_or_mint_cross_ref CALLED ===\n")
        f.write(f"tx_group has {len(tx_group)} transactions\n")
        for tx in tx_group:
            f.write(f"  - {tx.source}: {tx.tx_type} {tx.amount} {tx.asset} @ {tx.timestamp}\n")
        f.write(f"all_blockchain_txs has {len(all_blockchain_txs)} transactions\n")
    
    # 1. Identify Unmatched CEX/Wallet Activity
    # We are looking for groups that FAILED to match with blockchain initially (likely single-sided)
    has_blockchain = any(t.source == 'BLOCKCHAIN' for t in tx_group)
    
    with open("debug_log.txt", "a") as f:
        f.write(f"has_blockchain in tx_group: {has_blockchain}\n")
    
    if has_blockchain:
        with open("debug_log.txt", "a") as f:
            f.write(f"SKIPPING: tx_group already has blockchain tx\n")
        return None # Already matched
        
    cex_txs = [t for t in tx_group if t.source != 'BLOCKCHAIN']
    if not cex_txs:
        with open("debug_log.txt", "a") as f:
            f.write(f"SKIPPING: No CEX transactions in tx_group\n")
        return None
        
    main_tx = cex_txs[0]
    
    with open("debug_log.txt", "a") as f:
        f.write(f"main_tx: {main_tx.tx_type} {main_tx.amount} {main_tx.asset}\n")
    
    # CASE A: CEX Withdrawal (Paying BTC) -> Linked to Blockchain Mint/Buy
    if main_tx.tx_type in ['Withdrawal', 'Send'] and main_tx.asset == 'BTC':
        with open("debug_log.txt", "a") as f:
            f.write(f"CASE A: CEX Withdrawal detected\n")
        
        # Search for loose blockchain transactions near this time
        time_window = timedelta(hours=1) # 1 hour variance
        
        candidates = []
        for b_tx in all_blockchain_txs:
            diff = abs((b_tx.timestamp - main_tx.timestamp).total_seconds())
            if diff < time_window.total_seconds():
                candidates.append(b_tx)
                with open("debug_log.txt", "a") as f:
                    f.write(f"  Candidate: {b_tx.tx_id[:8]} diff={diff}s type={b_tx.tx_type}\n")
                
        with open("debug_log.txt", "a") as f:
            f.write(f"  Found {len(candidates)} candidates within 1 hour\n")
                
        # Analyze candidates
        for cand in candidates:
            is_marketplace = is_potential_marketplace_tx(cand)
            with open("debug_log.txt", "a") as f:
                f.write(f"  Checking candidate {cand.tx_id[:8]}: is_potential_marketplace_tx={is_marketplace}\n")
                f.write(f"    witness_data length: {len(cand.witness_data) if cand.witness_data else 0}\n")
            
            if is_marketplace:
                return {
                    "pattern": "NFT_MARKETPLACE_BUY_CROSSREF",
                    "confidence": 0.85,
                    "severity": "HIGH",
                    "tax_impact": "ESTABLISHES_COST_BASIS",
                    "affected_transactions": tx_group + [cand],
                    "corrections": [{
                        "tx": main_tx,
                        "action": "CHANGE_TO_BUY",
                        "reason": "Matched CEX Payment to Magic Eden/Marketplace Transaction",
                        "note": f"Linked to blockchain tx {cand.tx_id[:8]}...",
                        "verification_links": get_rune_links(cand.tx_id),
                        "ordiscan_link": get_ordiscan_link(cand.tx_id),
                        "transaction": cand
                    }]
                }

    # CASE B: CEX Deposit (Receiving Proceeds) -> Linked to Blockchain Sale
    if main_tx.tx_type in ['Deposit', 'Receive'] and main_tx.asset == 'BTC':
        with open("debug_log.txt", "a") as f:
            f.write(f"CASE B: CEX Deposit detected\n")
        
        time_window = timedelta(hours=6) # 6 hour variance
        
        candidates = []
        for b_tx in all_blockchain_txs:
             diff = abs((b_tx.timestamp - main_tx.timestamp).total_seconds())
             if diff < time_window.total_seconds():
                 candidates.append((b_tx, diff))
                 
                 # Log close matches
                 if diff < 7200:
                     with open("debug_log.txt", "a") as f:
                         f.write(f"  Candidate: {b_tx.tx_id[:8]} diff={diff}s\n")
                         f.write(f"    Type: {b_tx.tx_type}, Metadata: {b_tx.metadata}\n")
                     
                 # If we see a blockchain tx that is an Ordinal/Rune leaving wallet
                 if b_tx.tx_type in ['Withdrawal', 'Send'] and b_tx.metadata.get('asset_type') in ['ORDINAL', 'RUNE']:
                     with open("debug_log.txt", "a") as f:
                         f.write(f"  MATCH FOUND! {b_tx.tx_id[:8]} is Ordinal/Rune sale\n")
                     
                     return {
                        "pattern": "NFT_MARKETPLACE_SALE_CROSSREF",
                        "confidence": 0.85,
                        "severity": "HIGH",
                        "tax_impact": "TAXABLE_INCOME",
                        "affected_transactions": tx_group + [b_tx],
                        "corrections": [{
                            "tx": main_tx,
                            "action": "CHANGE_TO_TRADE",
                            "sent_asset": b_tx.metadata.get('rune_name') or "Ordinal/Rune",
                            "sent_amount": 1,
                            "received_asset": "BTC",
                            "received_quantity": main_tx.amount,
                            "reason": "Proceeds from Magic Eden/Marketplace Sale",
                            "note": f"Matched BTC deposit to Ordinal sale {b_tx.tx_id[:8]}",
                            "verification_links": get_rune_links(b_tx.tx_id, b_tx.metadata.get('rune_name')),
                            "ordiscan_link": get_ordiscan_link(b_tx.tx_id),
                            "transaction": b_tx
                        }]
                     }
        
        with open("debug_log.txt", "a") as f:
            f.write(f"  Checked {len(candidates)} candidates, no match found\n")
                     
    return None
