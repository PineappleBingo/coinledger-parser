import unittest
from datetime import datetime, timedelta
import pytz
from src.models import UnifiedTransaction
from src.reconciliation.engine import ReconciliationEngine
from src.reconciliation.anomaly import AnomalyDetector

class TestReconciliation(unittest.TestCase):
    def setUp(self):
        self.engine = ReconciliationEngine()
        self.utc = pytz.UTC
        
        # Base time
        self.t0 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=self.utc)
        
        # Source A (CEX)
        self.tx_a1 = UnifiedTransaction(
            timestamp=self.t0,
            asset="BTC",
            amount=1.0,
            fee=0.001,
            tx_id="0x123",
            tx_type="Buy",
            source="CEX"
        )
        self.tx_a2 = UnifiedTransaction(
            timestamp=self.t0 + timedelta(hours=1),
            asset="ETH",
            amount=5.0,
            fee=0.01,
            tx_id="", # No TxID
            tx_type="Sell",
            source="CEX"
        )
        
        # Source B (Blockchain)
        self.tx_b1 = UnifiedTransaction(
            timestamp=self.t0,
            asset="BTC",
            amount=1.0,
            fee=0.001,
            tx_id="0x123",
            tx_type="Transfer",
            source="BLOCKCHAIN"
        )
        self.tx_b2 = UnifiedTransaction(
            timestamp=self.t0 + timedelta(hours=1, minutes=5), # 5 min diff
            asset="ETH",
            amount=5.0001, # Tiny diff
            fee=0.01,
            tx_id="0x456",
            tx_type="Transfer",
            source="BLOCKCHAIN"
        )
        
    def test_exact_match(self):
        matched, conflicts, missing = self.engine.reconcile([self.tx_a1], [self.tx_b1])
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched.iloc[0]['match_type'], 'EXACT_TXID')
        self.assertTrue(missing.empty)
        
    def test_fuzzy_match(self):
        matched, conflicts, missing = self.engine.reconcile([self.tx_a2], [self.tx_b2])
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched.iloc[0]['match_type'], 'FUZZY_TIME_AMOUNT')
        self.assertGreater(matched.iloc[0]['confidence'], 0.9)
        
    def test_no_match(self):
        tx_unmatched = UnifiedTransaction(
            timestamp=self.t0 + timedelta(days=1),
            asset="SOL",
            amount=100.0,
            fee=0.1,
            tx_id="0x999",
            tx_type="Buy",
            source="CEX"
        )
        matched, conflicts, missing = self.engine.reconcile([tx_unmatched], [self.tx_b1])
        self.assertTrue(matched.empty)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts.iloc[0]['issue'], 'MISSING_IN_BLOCKCHAIN')

class TestAnomalyDetector(unittest.TestCase):
    def setUp(self):
        self.utc = pytz.UTC
        self.t0 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=self.utc)

    def test_high_fee(self):
        tx = UnifiedTransaction(
            timestamp=self.t0,
            asset="BTC",
            amount=0.1,
            fee=0.02, # 20% fee
            tx_id="0xabc",
            tx_type="Buy",
            source="CEX"
        )
        detector = AnomalyDetector([tx])
        anomalies = detector.detect_anomalies()
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['type'], 'FEE_ANOMALY')
        
    def test_duplicate_txid(self):
        tx1 = UnifiedTransaction(timestamp=self.t0, asset="BTC", amount=1, fee=0, tx_id="0xdup", tx_type="Buy", source="CEX")
        tx2 = UnifiedTransaction(timestamp=self.t0, asset="BTC", amount=1, fee=0, tx_id="0xdup", tx_type="Buy", source="CEX")
        
        detector = AnomalyDetector([tx1, tx2])
        anomalies = detector.detect_anomalies()
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]['type'], 'DUPLICATE_TXID')

if __name__ == '__main__':
    unittest.main()
