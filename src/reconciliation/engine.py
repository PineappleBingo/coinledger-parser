import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List, Tuple, Dict
from src.models import UnifiedTransaction
from src.config import get_gemini_model
from src.reconciliation.ordinals_detector import (
    group_transactions_by_txid,
    group_transactions_by_time,
    detect_patterns
)

class ReconciliationEngine:
    def __init__(self):
        pass
    
    def reconcile_with_corrections(self, source_a: List[UnifiedTransaction], source_b: List[UnifiedTransaction], my_wallets: List[str] = None) -> Dict:
        """
        Enhanced reconciliation with Ordinals/Runes pattern detection
        
        Returns correction suggestions for tax reporting
        """
        if my_wallets is None:
            my_wallets = []
        
        print(f"Reconciling {len(source_a)} CEX transactions with {len(source_b)} blockchain transactions")
        
        # Strategy: Group CEX transactions (source_a) by exact timestamp
        # Then match with blockchain transactions (source_b) that have TxIDs
        
        # Step 1: Group CEX transactions by exact timestamp (down to the minute)
        cex_groups = {}
        for tx in source_a:
            # Create time key: YYYY-MM-DD HH:MM
            time_key = tx.timestamp.strftime("%Y-%m-%d %H:%M")
            if time_key not in cex_groups:
                cex_groups[time_key] = []
            cex_groups[time_key].append(tx)
        
        print(f"Created {len(cex_groups)} CEX transaction groups by timestamp")
        
        # Step 2: For each CEX group, try to find matching blockchain transactions
        all_groups = {}
        for time_key, cex_txs in cex_groups.items():
            # Find blockchain transactions within ±2 minutes of this timestamp
            from datetime import datetime, timedelta
            import pytz
            
            target_time = datetime.strptime(time_key, "%Y-%m-%d %H:%M").replace(tzinfo=pytz.UTC)
            time_window = timedelta(minutes=2)
            
            matching_blockchain_txs = []
            for tx in source_b:
                if abs((tx.timestamp - target_time).total_seconds()) <= time_window.total_seconds():
                    matching_blockchain_txs.append(tx)
            
            # Combine CEX and blockchain transactions for this time window
            combined_group = cex_txs + matching_blockchain_txs
            all_groups[time_key] = combined_group
            
            if matching_blockchain_txs:
                print(f"  {time_key}: {len(cex_txs)} CEX + {len(matching_blockchain_txs)} blockchain = {len(combined_group)} total")
        
        # Step 3: Also add blockchain-only groups (transactions not matched to CEX)
        matched_blockchain_txids = set()
        for group in all_groups.values():
            for tx in group:
                if tx.source == 'BLOCKCHAIN' and tx.tx_id:
                    matched_blockchain_txids.add(tx.tx_id)
        
        # Group unmatched blockchain transactions by TxID
        unmatched_blockchain = [tx for tx in source_b if tx.tx_id and tx.tx_id not in matched_blockchain_txids]
        blockchain_groups = group_transactions_by_txid(unmatched_blockchain)
        
        # Merge blockchain-only groups
        all_groups.update(blockchain_groups)
        
        print(f"Total groups for pattern detection: {len(all_groups)}")
        
        # Detect patterns in each group
        correction_suggestions = []
        for group_key, tx_group in all_groups.items():
            pattern = detect_patterns(tx_group, my_wallets)
            if pattern:
                correction_suggestions.append(pattern)
        
        # Generate summary statistics
        summary = self._generate_summary(correction_suggestions)
        
        return {
            "correction_suggestions": correction_suggestions,
            "summary": summary
        }
    
    def _generate_summary(self, suggestions: List[Dict]) -> Dict:
        """Generate summary statistics for correction suggestions"""
        total = len(suggestions)
        
        by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        by_pattern = {}
        
        for suggestion in suggestions:
            severity = suggestion.get("severity", "MEDIUM")
            pattern = suggestion.get("pattern", "UNKNOWN")
            
            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_pattern[pattern] = by_pattern.get(pattern, 0) + 1
        
        return {
            "total_issues": total,
            "by_severity": by_severity,
            "by_pattern": by_pattern
        }

    def reconcile(self, source_a: List[UnifiedTransaction], source_b: List[UnifiedTransaction]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Original reconciliation method (kept for backward compatibility)
        Reconciles two lists of transactions.
        Source A: CEX Data (CoinLedger)
        Source B: Blockchain Data
        
        Returns:
            (matched, conflicts, missing_in_source_b)
        """
        df_a = pd.DataFrame([t.to_dict() for t in source_a])
        df_b = pd.DataFrame([t.to_dict() for t in source_b])
        
        if df_a.empty:
            return pd.DataFrame(), pd.DataFrame(), df_b
        if df_b.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame() # All missing in B

        # Ensure timestamps are datetime
        df_a['timestamp'] = pd.to_datetime(df_a['timestamp'])
        df_b['timestamp'] = pd.to_datetime(df_b['timestamp'])
        
        matched = []
        conflicts = []
        
        # Track indices of matched transactions in B to find missing ones later
        matched_indices_b = set()
        
        for idx_a, row_a in df_a.iterrows():
            # Tier 1: Exact TxID Match
            # Some CEX exports might not have TxID, skip if empty
            if row_a['tx_id']:
                exact_match = df_b[df_b['tx_id'] == row_a['tx_id']]
                if not exact_match.empty:
                    match_row = exact_match.iloc[0]
                    matched.append({
                        'source_a': row_a.to_dict(),
                        'source_b': match_row.to_dict(),
                        'confidence': 1.0,
                        'match_type': 'EXACT_TXID'
                    })
                    matched_indices_b.add(exact_match.index[0])
                    continue
            
            # Tier 2: Fuzzy Match (Time + Amount)
            # Time window: +/- 30 minutes
            time_window = timedelta(minutes=30)
            time_lower = row_a['timestamp'] - time_window
            time_upper = row_a['timestamp'] + time_window
            
            candidates = df_b[
                (df_b['timestamp'] >= time_lower) & 
                (df_b['timestamp'] <= time_upper) &
                (~df_b.index.isin(matched_indices_b)) # Don't match already matched
            ]
            
            best_match = None
            best_confidence = 0.0
            
            for idx_b, row_b in candidates.iterrows():
                # Amount deviation check (0.1% tolerance)
                if row_a['amount'] == 0: continue
                
                diff = abs(row_a['amount'] - row_b['amount'])
                deviation = diff / abs(row_a['amount'])
                
                if deviation <= 0.001: # 0.1%
                    confidence = 1.0 - (deviation * 100) # Simple confidence score
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = (idx_b, row_b)
            
            if best_match and best_confidence >= 0.9:
                idx_b, row_b = best_match
                matched.append({
                    'source_a': row_a.to_dict(),
                    'source_b': row_b.to_dict(),
                    'confidence': best_confidence,
                    'match_type': 'FUZZY_TIME_AMOUNT'
                })
                matched_indices_b.add(idx_b)
            else:
                # Tier 3: Gemini Semantic Match (Placeholder / Future Implementation)
                # For now, mark as conflict/missing
                conflicts.append({
                    'source_a': row_a.to_dict(),
                    'source_b': None,
                    'issue': 'MISSING_IN_BLOCKCHAIN'
                })

        # Identify missing in A (present in B but not matched)
        missing_in_a_indices = set(df_b.index) - matched_indices_b
        missing_in_a = df_b.loc[list(missing_in_a_indices)]
        
        return pd.DataFrame(matched), pd.DataFrame(conflicts), missing_in_a
