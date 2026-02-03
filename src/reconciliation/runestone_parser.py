
from typing import List, Optional, Dict
from src.models import UnifiedTransaction

class RunestoneParser:
    """
    Parser for Bitcoin Runes Protocol (Runestones).
    Decodes OP_RETURN data to identify valid Runes transactions and Cenotaphs (burns).
    """
    
    OP_RETURN = 0x6a
    OP_13 = 0x5d  # 'R'
    
    @staticmethod
    def decode_leb128(data: bytes) -> List[int]:
        """
        Decodes a byte string of concatenated LEB128 integers.
        Returns a list of decoded integers.
        """
        result = []
        current = 0
        shift = 0
        
        # Pointer to current byte index
        i = 0
        while i < len(data):
            byte = data[i]
            
            # Extract lower 7 bits
            value = byte & 0x7f
            current |= value << shift
            
            # Check high bit
            if (byte & 0x80) == 0:
                # End of integer
                result.append(current)
                current = 0
                shift = 0
            else:
                # More bytes follow
                shift += 7
            
            i += 1
            
        return result

    def detect_cenotaph(self, payload: bytes) -> bool:
        """
        Detects if a Runestone payload is a Cenotaph (malformed).
        A Cenotaph happens if:
        - The LEB128 sequence is incomplete.
        - Contains unrecognized tags (odd tags are critical).
        """
        # Basic LEB128 validity check
        # If the last byte has the high bit set, it's an incomplete sequence -> Cenotaph
        if payload and (payload[-1] & 0x80) != 0:
            return True
            
        return False

    def parse_transaction(self, tx: UnifiedTransaction) -> Optional[Dict]:
        """
        Parses a transaction to check for Runestone data.
        Returns a dict with Runestone details if found, or None.
        """
        # Check source is blockchain
        if tx.source != 'BLOCKCHAIN':
            return None
            
        # Iterate through witness data or outputs to find OP_RETURN + OP_13
        # In this simplified version for V2, we focus on outputs as stored in metadata
        # or if we had raw output scripts.
        # Since UnifiedTransaction doesn't store raw output scripts by default (unless in metadata),
        # we might need to rely on what `blockchain.py` extracted or infer from `witness_data` if relevant
        # (though Runes are in OP_RETURN outputs, not witness).
        
        # However, `blockchain.py` DOES extract metadata['runes'] via UniSat checks, 
        # but here we want to validate the "Cenotaph" status which UniSat might hide.
        
        # Limitation: We need the raw scriptpubkey of the OP_RETURN output to decode properly.
        # Currently `blockchain.py` checks `scriptpubkey.startswith('6a5d')`.
        # We need `blockchain.py` to actually store that payload if we want to parse it here.
        # For Phase 1, we didn't explicitly add `raw_payload` to `UnifiedTransaction`.
        
        # Workaround for now: We will simulate the logic assuming we can access the payload 
        # via a hypothetical `tx.metadata.get('rune_payload')` or similar, 
        # which we might need to add to `blockchain.py` later.
        
        # For the purpose of this implementation task:
        # I'll enable the parser to take a hex string directly, 
        # so it can be used when we do have the data.
        pass

    @staticmethod
    def parse_payload(payload_hex: str) -> Dict:
        """
        Parses a specific Runestone payload hex string.
        Payload should be the data AFTER '6a5d' (OP_RETURN OP_13).
        """
        try:
            data = bytes.fromhex(payload_hex)
            
            parser = RunestoneParser()
            is_cenotaph = parser.detect_cenotaph(data)
            
            integers = parser.decode_leb128(data)
            
            return {
                "is_cenotaph": is_cenotaph,
                "integers": integers,
                "valid": not is_cenotaph
            }
        except Exception as e:
            return {
                "is_cenotaph": True, 
                "error": str(e),
                "valid": False
            }
