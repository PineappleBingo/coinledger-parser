import pandas as pd
from typing import List, Dict
from src.models import UnifiedTransaction

class AnomalyDetector:
    def __init__(self, transactions: List[UnifiedTransaction]):
        self.transactions = transactions
        self.df = pd.DataFrame([t.to_dict() for t in transactions])
        
    def detect_anomalies(self) -> List[Dict]:
        anomalies = []
        
        if self.df.empty:
            return anomalies
            
        # Rule 1: Fee exceeds transaction amount (10% threshold)
        # Filter for transactions where fee and amount are non-zero
        high_fee_mask = (self.df['fee'] > 0) & (self.df['amount'] > 0) & (self.df['fee'] > self.df['amount'] * 0.1)
        high_fee_txs = self.df[high_fee_mask]
        
        for _, row in high_fee_txs.iterrows():
            anomalies.append({
                'type': 'FEE_ANOMALY',
                'severity': 'HIGH',
                'message_kr': '수수료가 거래금액의 10%를 초과합니다',
                'tx_id': row['tx_id']
            })
            
        # Rule 2: Duplicate TxID
        # Ignore empty tx_ids
        valid_tx_ids = self.df[self.df['tx_id'] != '']
        duplicates = valid_tx_ids[valid_tx_ids.duplicated(subset=['tx_id'], keep=False)]
        
        processed_dupes = set()
        for _, row in duplicates.iterrows():
            if row['tx_id'] not in processed_dupes:
                anomalies.append({
                    'type': 'DUPLICATE_TXID',
                    'severity': 'CRITICAL',
                    'message_kr': '동일한 거래ID로 중복 거래가 발견되었습니다',
                    'tx_id': row['tx_id']
                })
                processed_dupes.add(row['tx_id'])
                
        # Rule 3: Timestamp outside tax year (Example: 2025)
        # This would typically be parameterized
        TAX_YEAR = 2025
        # Convert to datetime if not already (it should be from UnifiedTransaction)
        # self.df['timestamp'] is ISO string in to_dict(), need to parse back if using pandas logic strictly
        # But UnifiedTransaction object has datetime. Let's use the list for this check to be safe.
        
        for tx in self.transactions:
            if tx.timestamp.year != TAX_YEAR:
                anomalies.append({
                    'type': 'OUT_OF_RANGE',
                    'severity': 'MEDIUM',
                    'message_kr': f'{TAX_YEAR}년 과세연도 외 거래가 포함되어 있습니다 ({tx.timestamp.year})',
                    'tx_id': tx.tx_id
                })
                
        return anomalies
