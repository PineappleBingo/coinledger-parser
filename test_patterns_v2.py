
import unittest
from datetime import datetime
from src.models import UnifiedTransaction
from src.reconciliation.ordinals_detector import (
    detect_fiat_onramp_pattern,
    detect_runes_cenotaph_pattern,
    detect_brc20_transfer_pattern,
    detect_psbt_pattern
)

class TestPatternsV2(unittest.TestCase):
    def setUp(self):
        self.ts = datetime.now()

    def test_p0_fiat_onramp(self):
        # Scenario: CEX Only deposit, no blockchain source
        tx_group = [
            UnifiedTransaction(
                timestamp=self.ts,
                asset='BTC',
                amount=0.1,
                fee=0,
                tx_id='cex_dep_1',
                tx_type='Deposit',
                source='CEX'
            )
        ]
        result = detect_fiat_onramp_pattern(tx_group)
        self.assertIsNotNone(result)
        self.assertEqual(result['pattern'], 'FIAT_ONRAMP')
        
    def test_p4_brc20_transfer_inscription(self):
        # Scenario: Blockchain tx with BRC-20 transfer inscription in witness
        # JSON: {"p":"brc-20", "op":"transfer", "tick":"ordi", "amt":"100"}
        # Hex: 7b2270223a226272632d3230222c20226f70223a227472616e73666572227d (simplified)
        brc20_hex = b'{"p":"brc-20", "op":"transfer"}'.hex()
        
        tx_group = [
            UnifiedTransaction(
                timestamp=self.ts,
                asset='BTC',
                amount=-0.00000546,
                fee=0.0001,
                tx_id='brc20_tx',
                tx_type='Withdrawal',
                source='BLOCKCHAIN',
                metadata={'asset_type': 'BTC'},
                witness_data=[brc20_hex]
            )
        ]
        result = detect_brc20_transfer_pattern(tx_group)
        self.assertIsNotNone(result)
        self.assertEqual(result['pattern'], 'BRC20_TRANSFER_INSCRIBE')

    def test_p3_psbt_heuristic(self):
        # Scenario: Many witness items implying multi-party
        witness_data = ["sig"] * 10
        tx_group = [
            UnifiedTransaction(
                timestamp=self.ts,
                asset='BTC',
                amount=0,
                fee=0,
                tx_id='psbt_tx',
                tx_type='Internal',
                source='BLOCKCHAIN',
                witness_data=witness_data
            )
        ]
        result = detect_psbt_pattern(tx_group)
        self.assertIsNotNone(result)
        self.assertEqual(result['pattern'], 'POTENTIAL_MARKETPLACE_SWAP')

if __name__ == '__main__':
    unittest.main()
