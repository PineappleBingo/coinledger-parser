import pandas as pd
import numpy as np
from datetime import timedelta
from typing import List, Tuple, Dict
from src.models import UnifiedTransaction
from src.config import get_gemini_model

class ReconciliationEngine:
    def __init__(self):
        pass

    def reconcile(self, source_a: List[UnifiedTransaction], source_b: List[UnifiedTransaction]) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
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
                deviation = diff / row_a['amount']
                
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
