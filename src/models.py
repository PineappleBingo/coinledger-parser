from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class UnifiedTransaction:
    """
    Normalized transaction data structure for BitMatch.
    """
    timestamp: datetime
    asset: str
    amount: float
    fee: float
    tx_id: str
    tx_type: str
    source: str  # 'CEX' or 'BLOCKCHAIN'
    price_krw: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)  # For asset_type, etc.
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "asset": self.asset,
            "amount": self.amount,
            "fee": self.fee,
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "source": self.source,
            "price_krw": self.price_krw,
            "metadata": self.metadata
        }
