# Analysis Logic Documentation

**Document Created:** 2026-01-27  
**Last Updated:** 2026-02-03 (Updated to reflect actual v2 implementation)

---

## Objective

The reconciliation system compares two transaction data sources to identify matches, conflicts, and specialized Bitcoin patterns (Ordinals/Runes):
- **Source A (CEX Export):** Transaction data from CoinLedger export (CSV).
- **Source B (Blockchain):** On-chain transaction data fetched from Bitcoin blockchain/UniSat.

**Goal:** Accurately reconcile CEX records with On-Chain reality, specifically correctly classifying complex events like Ordinal Mints, Rune Transfers, and self-transfers that CEXs often misreport.

---

## System Flow

```mermaid
graph TD
    A[User Uploads CEX Export] --> B[Parse Source A]
    C[User Enters Wallet Addresses] --> D[Fetch Source B (Blockchain/UniSat)]
    B & D --> E[ReconciliationEngine.reconcile_with_corrections]
    E --> F[Group by Timestamp (±2 min)]
    F --> G[Detect Patterns (Ordinals/Runes)]
    G --> H[Detect Anomalies]
    H --> I[Generate Correction Report]
```

---

## Reconciliation Logic

The core logic resides in `src/reconciliation/engine.py` and `src/reconciliation/ordinals_detector.py`.

### Phase 1: Grouping Strategy
Instead of complex fuzzy matching, the system uses a **Time-Based Bucket Strategy** to group related transactions.

1.  **CEX Grouping:** Source A transactions are grouped by minute-level timestamp.
2.  **Blockchain Matching:** For each CEX group, the system searches Source B for transactions within a **±2 minute window**.
3.  **Blockchain-Only Groups:** Any remaining blockchain transactions (unmatched) are grouped by their TxID.

This results in "Transaction Groups" that likely represent single logical events (e.g., a withdrawal on CEX corresponding to a deposit on-chain).

### Phase 2: Pattern Detection (Ordinals & Runes)
Each transaction group is analyzed against 6 specific patterns defined in `ordinals_detector.py`. These patterns identify where CoinLedger's default classification fails.

| Priority | Pattern Name | Scenario | CoinLedger Error | System Correction |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **BULK MINT** | 1 Withdrawal + Multiple Dust Deposits | Taxed as multiple income events | Merge into single Trade (Mint) |
| 2 | **MINT / BUY** | 1 Withdrawal + 1 Dust Deposit | Taxed as separate Income + Withdrawal | Merge into single Trade |
| 3 | **SELF TRANSFER** | Withdrawal + Deposit (Same Amount) | Taxed as Disposed + Indcome | Merge as Self-Transfer (Non-taxable) |
| 4 | **GAS FEE** | Small Withdrawal (<50k sats) | Taxed as taxable Withdrawal | Reclassify as Fee (Deductible) |
| 5 | **RUNE RECEIVE** | Deposit with Rune Metadata | Taxed as Income | Mark as Non-Taxable Receive |
| 6 | **SALE** | Large Deposit (No Withdrawal) | Taxed as simple Deposit (Cost Basis lost) | Reclassify as Trade (Sale of Asset) ms |

*   **Dust Threshold:** Transactions <= 10,000 sats (0.0001 BTC) are flagged as potential "Dust" (wrappers for artifacts).
*   **Verification:** Links to Ordiscan, OKLink, and Ordinals.com are generated for verification.

### Phase 3: Anomaly Detection
The `AnomalyDetector` (`src/reconciliation/anomaly.py`) runs a final pass to catch data quality issues:

1.  **High Fee:** Transaction Fee > 10% of the transaction Amount.
2.  **Duplicate TxID:** Multiple transactions sharing the same Hash (critical data error).
3.  **Out of Range:** Transactions outside the target Tax Year (e.g., 2025).

---

## Output Format

The analysis produces a **Correction Report** JSON structure:

```json
{
  "correction_suggestions": [
    {
      "pattern": "MINT_BUY",
      "confidence": 0.9,
      "severity": "HIGH",
      "affected_transactions": [ ... ],
      "corrections": [
        {
          "action": "IGNORE",
          "reason": "Dust wrapper..."
        },
        {
          "action": "CHANGE_TO_TRADE",
          "received_asset": "ORDINAL/RUNE"
        }
      ]
    }
  ],
  "summary": {
    "total_issues": 12,
    "by_pattern": { "MINT_BUY": 5, "GAS_FEE": 7 }
  }
}
```

---

## Data Sources

1.  **Blockstream / Mempool.space**: For standard Bitcoin transaction data.
2.  **UniSat API**: specifically used to fetch **Rune** and **Ordinal** metadata (`rune_name`, `inscription_id`).
    *   *Endpoint:* `/v1/indexer/runes/events` (for transfers) and `/v1/indexer/tx/{txid}`.

---

## Limitations

1.  **Time Window Sensitivity:** The ±2 minute window is hardcoded. Clock drift > 2 mins between CEX and Blockchain will cause missed matches.
2.  **Exchange Support:** Heuristics are tuned for how CoinLedger imports data; other tax tools may format exports differently.
