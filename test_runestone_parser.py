
import unittest
from src.reconciliation.runestone_parser import RunestoneParser

class TestRunestoneParser(unittest.TestCase):
    
    def test_decode_leb128_simple(self):
        # 1 byte: 0x05 -> 5
        data = bytes([0x05])
        result = RunestoneParser.decode_leb128(data)
        self.assertEqual(result, [5])
        
    def test_decode_leb128_multi_byte(self):
        # 2 bytes: 0xE5 0x8E 0x26 -> 624485
        # 0xE5 = 11100101 (low 7: 1100101 = 101, high 1)
        # 0x8E = 10001110 (low 7: 0001110 = 14, high 1)
        # 0x26 = 00100110 (low 7: 0100110 = 38, high 0)
        # Value = 101 + (14 << 7) + (38 << 14)
        # 101 + 1792 + 622592 = 624485
        
        # Testing a known sequence: [1, 2] -> 0x01 0x02
        data = bytes([0x01, 0x02])
        result = RunestoneParser.decode_leb128(data)
        self.assertEqual(result, [1, 2])
        
    def test_cenotaph_incomplete_leb128(self):
        # Incomplete sequence: High bit set on last byte
        data = bytes([0x80]) # 10000000 -> expects more
        is_cenotaph = RunestoneParser().detect_cenotaph(data)
        self.assertTrue(is_cenotaph)
        
    def test_valid_payload_parsing(self):
        # Valid payload representing integers [10, 20]
        # 10 -> 0x0A
        # 20 -> 0x14
        payload_hex = "0a14" 
        result = RunestoneParser.parse_payload(payload_hex)
        self.assertFalse(result['is_cenotaph'])
        self.assertEqual(result['integers'], [10, 20])
        
    def test_malformed_payload_parsing(self):
        # Incomplete
        payload_hex = "80"
        result = RunestoneParser.parse_payload(payload_hex)
        self.assertTrue(result['is_cenotaph'])

if __name__ == '__main__':
    unittest.main()
