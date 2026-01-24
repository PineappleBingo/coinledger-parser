import unittest
import pandas as pd
from src.ingest.csv_parser import smart_csv_load, normalize_csv_data
from src.models import UnifiedTransaction
import os
from unittest.mock import patch

class TestCSVParser(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_export.csv"
        # CSV with standard headers
        content = "timestamp,asset,amount,fee,tx_id,tx_type\n2025-01-01 12:00:00,ETH,1.5,0.01,0xdef456,Sell"
        with open(self.test_file, "w") as f:
            f.write(content)

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_standard_csv_load(self):
        df = smart_csv_load(self.test_file)
        self.assertFalse(df.empty)
        
        transactions = normalize_csv_data(df)
        self.assertEqual(len(transactions), 1)
        tx = transactions[0]
        
        self.assertEqual(tx.asset, "ETH")
        self.assertEqual(tx.amount, 1.5)
        self.assertEqual(tx.tx_type, "Sell")

    @patch('src.ingest.csv_parser.get_gemini_model')
    def test_gemini_inference(self, mock_get_model):
        # Mock Gemini response
        mock_response = unittest.mock.Mock()
        mock_response.text = '{"Date (UTC)": "timestamp", "Coin": "asset", "Qty": "amount"}'
        mock_model = unittest.mock.Mock()
        mock_model.generate_content.return_value = mock_response
        mock_get_model.return_value = mock_model

        # Create weird CSV
        weird_file = "weird.csv"
        with open(weird_file, "w") as f:
            f.write("Date (UTC),Coin,Qty\n2025-01-02 15:00:00,SOL,100")
            
        try:
            df = smart_csv_load(weird_file)
            self.assertIn("timestamp", df.columns)
            self.assertIn("asset", df.columns)
            self.assertIn("amount", df.columns)
            
            transactions = normalize_csv_data(df)
            self.assertEqual(len(transactions), 1)
            self.assertEqual(transactions[0].asset, "SOL")
        finally:
            if os.path.exists(weird_file):
                os.remove(weird_file)

if __name__ == '__main__':
    unittest.main()
