import unittest
import pandas as pd
from src.ingest.mhtml_parser import extract_transactions_from_mhtml, normalize_mhtml_data
from src.models import UnifiedTransaction
import os

class TestMHTMLParser(unittest.TestCase):
    def setUp(self):
        # Create a dummy MHTML file
        self.test_file = "test_export.mhtml"
        content = """
        MIME-Version: 1.0
        Content-Type: multipart/related; boundary="----=_NextPart_000_0000"

        ------=_NextPart_000_0000
        Content-Type: text/html; charset="utf-8"

        <html>
        <body>
            <table class="transaction-history">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Asset</th>
                        <th>Amount</th>
                        <th>Fee</th>
                        <th>TxHash</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>2025-01-01 10:00:00</td>
                        <td>Buy</td>
                        <td>BTC</td>
                        <td>0.5</td>
                        <td>0.001</td>
                        <td>0x123abc</td>
                    </tr>
                </tbody>
            </table>
        </body>
        </html>
        ------=_NextPart_000_0000--
        """
        with open(self.test_file, "wb") as f:
            f.write(content.encode('utf-8'))

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_extract_and_normalize(self):
        df = extract_transactions_from_mhtml(self.test_file)
        self.assertFalse(df.empty)
        self.assertEqual(len(df), 1)
        
        transactions = normalize_mhtml_data(df)
        self.assertEqual(len(transactions), 1)
        tx = transactions[0]
        
        self.assertIsInstance(tx, UnifiedTransaction)
        self.assertEqual(tx.asset, "BTC")
        self.assertEqual(tx.amount, 0.5)
        self.assertEqual(tx.fee, 0.001)
        self.assertEqual(tx.tx_id, "0x123abc")
        self.assertEqual(tx.source, "CEX")

if __name__ == '__main__':
    unittest.main()
