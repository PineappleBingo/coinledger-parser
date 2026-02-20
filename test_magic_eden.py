from src.reconciliation.ordinals_detector import detect_patterns
from src.reconciliation.blockchain import UnifiedTransaction
from datetime import datetime
import json

# Manually create the transaction simulating what blockchain.py would parse
tx = UnifiedTransaction(
    timestamp=datetime.utcfromtimestamp(1763506189),
    asset="BTC",
    amount=0.00000546, # Deposit amount
    fee=0,
    tx_id="ffe9c95c269fb99ff6972665b7c7d57e06d47a9192849ca1396881bf81a8552d",
    tx_type="Deposit",
    source="BLOCKCHAIN",
    price_krw=0,
    metadata={
        "asset_type": "ORDINAL",
        "inscription_id": "71578892" * 4 # fake ID
    },
    witness_data=["sig1", "sig2", "multisig_script"], # PSBT signature heuristic > 2 witnesses
    raw_hex=""
)

pattern = detect_patterns([tx], [], [])
print(json.dumps(pattern, default=str, indent=2))
