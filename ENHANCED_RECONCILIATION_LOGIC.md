# Enhanced Reconciliation Logic for Bitcoin Ordinals/Runes Tax Correction

**Document Created:** 2026-01-27  
**Version:** 2.0 (Enhanced for Ordinals/Runes)  
**Last Updated:** 2026-01-27 22:53 EST  
**Primary Reference:** `correction scenario.md`

---

## Objective

**Primary Goal:** Identify CoinLedger misclassifications of Bitcoin Ordinals/Runes transactions and provide actionable correction suggestions for accurate 2025 tax reporting.

**Problem:** CoinLedger doesn't understand the special nature of Ordinals/Runes transactions (Dust transfers as "wrappers"), leading to:
- Split transactions that should be unified
- Deposits/Withdrawals that should be Trades
- Missing cost basis for NFT/Rune acquisitions
- Incorrect taxable events

---

## 5 Core Correction Scenarios

### Scenario 1: Mint/Buy (구매/민팅)
**Pattern:** `[Withdrawal (large) + Deposit (546 sats)]` in same TxID/timeframe

**CoinLedger Error:**
- Records as separate Withdrawal + Deposit
- Deposit (dust) appears as income

**Blockchain Reality:**
- Withdrawal = Gas fee + purchase cost
- Deposit (546 sats) = Dust "wrapper" for Ordinal/Rune

**Correction Actions:**
1. **Deposit (546 sats)** → `IGNORE` (not taxable income)
2. **Withdrawal** → `TRADE`
   - Sent: BTC (withdrawal amount)
   - Received: [Asset Name from Ordiscan]

**Detection Logic:**
```python
if (withdrawal_exists and 
    all(deposit.amount <= 0.00001 for deposit in deposits) and
    same_txid_or_within_5_minutes):
    return "MINT_BUY_PATTERN"
```

---

### Scenario 2: Gas Fees (가스비)
**Pattern:** `[Withdrawal (small)]` with no matching Deposit

**CoinLedger Error:**
- Records as Withdrawal (potential taxable event)

**Blockchain Reality:**
- Network fee for failed transaction or inscription

**Correction Actions:**
1. **Withdrawal** → `FEE` (tax deductible expense)

**Detection Logic:**
```python
if (withdrawal_exists and 
    not deposits and 
    withdrawal.amount < 0.0005):
    return "GAS_FEE_PATTERN"
```

---

### Scenario 3: Sales (판매)
**Pattern:** `[Deposit (large)]` with no matching Withdrawal

**CoinLedger Error:**
- Records as simple Deposit (not taxable)

**Blockchain Reality:**
- Proceeds from selling Ordinal/Rune

**Correction Actions:**
1. **Deposit** → `TRADE`
   - Sent: [Asset Name - user must specify]
   - Received: BTC (deposit amount)

**Detection Logic:**
```python
if (deposit_exists and 
    not withdrawals and
    is_external_sender(txid)):
    return "SALE_PATTERN"
```

---

### Scenario 4: Self Transfer (단순 이동)
**Pattern:** `[Withdrawal A + Deposit B]` between own wallets, similar amounts

**CoinLedger Error:**
- Records as two separate taxable events

**Blockchain Reality:**
- Moving funds between own wallets (non-taxable)

**Correction Actions:**
1. **Merge both** → `TRANSFER` (no tax event)

**Detection Logic:**
```python
if (len(withdrawals) == 1 and len(deposits) == 1 and
    withdrawal.to_address in my_wallets and
    abs(withdrawal.amount - deposit.amount) < 0.0001):
    return "SELF_TRANSFER_PATTERN"
```

---

### Scenario 5: Bulk Mint (대량 민팅)
**Pattern:** `[Withdrawal 1x + Deposit Nx]` - one withdrawal, multiple dust deposits

**CoinLedger Error:**
- Multiple deposits appear as separate income

**Blockchain Reality:**
- Minting multiple Ordinals/Runes in one transaction

**Correction Actions:**
1. **All Deposits** → `IGNORE`
2. **Withdrawal** → `TRADE`
   - Sent: BTC (total cost)
   - Received: [Asset Name] × N quantity

**Detection Logic:**
```python
if (len(withdrawals) == 1 and 
    len(deposits) > 1 and
    all(d.amount <= 0.00001 for d in deposits)):
    return "BULK_MINT_PATTERN"
```

---

## Enhanced Reconciliation Algorithm

### Phase 1: Group Transactions by TxID/Time
```python
def group_transactions(source_a, source_b):
    """Group transactions by TxID or time window for pattern detection"""
    groups = {}
    
    # Combine both sources
    all_txs = source_a + source_b
    
    # Group by TxID (exact match - highest confidence)
    for tx in all_txs:
        if tx.tx_id:
            if tx.tx_id not in groups:
                groups[tx.tx_id] = []
            groups[tx.tx_id].append(tx)
    
    # Group remaining by time window (±5 minutes)
    ungrouped = [tx for tx in all_txs if not tx.tx_id or tx.tx_id not in groups]
    for tx in ungrouped:
        # Round to 5-minute buckets
        time_key = f"time_{int(tx.timestamp.timestamp() / 300)}"
        if time_key not in groups:
            groups[time_key] = []
        groups[time_key].append(tx)
    
    return groups
```

### Phase 2: Pattern Detection
```python
def detect_ordinals_pattern(tx_group, my_wallets):
    """Detect Ordinals/Runes transaction patterns"""
    
    # Separate by type and source
    source_a_txs = [t for t in tx_group if t.source == 'CEX']
    source_b_txs = [t for t in tx_group if t.source == 'BLOCKCHAIN']
    
    withdrawals = [t for t in source_a_txs if t.tx_type == 'Withdrawal']
    deposits = [t for t in source_a_txs if t.tx_type == 'Deposit']
    
    # SCENARIO 5: Bulk Mint (highest priority - most specific)
    if len(withdrawals) == 1 and len(deposits) > 1:
        if all(d.amount <= 0.00001 for d in deposits):
            return {
                "pattern": "BULK_MINT",
                "confidence": 0.95,
                "severity": "HIGH",
                "tax_impact": "ESTABLISHES_COST_BASIS",
                "corrections": [
                    *[{
                        "tx_id": d.tx_id,
                        "original_type": "Deposit",
                        "action": "IGNORE",
                        "reason": "Dust wrapper for Ordinal/Rune (not income)",
                        "warning": "Do NOT delete - mark as 'Ignored' in CoinLedger"
                    } for d in deposits],
                    {
                        "tx_id": withdrawals[0].tx_id,
                        "original_type": "Withdrawal",
                        "action": "CHANGE_TO_TRADE",
                        "sent_asset": "BTC",
                        "sent_amount": abs(withdrawals[0].amount),
                        "received_asset": "ORDINAL/RUNE",
                        "received_quantity": len(deposits),
                        "requires_ordiscan": True
                    }
                ]
            }
    
    # SCENARIO 1: Mint/Buy
    if withdrawals and deposits:
        if all(d.amount <= 0.00001 for d in deposits):
            return {
                "pattern": "MINT_BUY",
                "confidence": 0.9,
                "severity": "HIGH",
                "tax_impact": "ESTABLISHES_COST_BASIS",
                "corrections": [
                    *[{
                        "tx_id": d.tx_id,
                        "action": "IGNORE",
                        "reason": "Dust wrapper"
                    } for d in deposits],
                    {
                        "tx_id": withdrawals[0].tx_id,
                        "action": "CHANGE_TO_TRADE",
                        "requires_ordiscan": True
                    }
                ]
            }
    
    # SCENARIO 4: Self Transfer
    if len(withdrawals) == 1 and len(deposits) == 1:
        w, d = withdrawals[0], deposits[0]
        # Check if both addresses belong to user
        if (any(addr in str(w.tx_id) for addr in my_wallets) and
            abs(w.amount - d.amount) < 0.0001):
            return {
                "pattern": "SELF_TRANSFER",
                "confidence": 0.85,
                "severity": "MEDIUM",
                "tax_impact": "NON_TAXABLE",
                "corrections": [{
                    "tx_ids": [w.tx_id, d.tx_id],
                    "action": "MERGE_AS_TRANSFER",
                    "reason": "Moving between own wallets"
                }]
            }
    
    # SCENARIO 2: Gas Fee
    if withdrawals and not deposits:
        if withdrawals[0].amount < 0.0005:
            return {
                "pattern": "GAS_FEE",
                "confidence": 0.8,
                "severity": "LOW",
                "tax_impact": "TAX_DEDUCTIBLE",
                "corrections": [{
                    "tx_id": withdrawals[0].tx_id,
                    "action": "CHANGE_TO_FEE",
                    "reason": "Network cost"
                }]
            }
    
    # SCENARIO 3: Sale
    if deposits and not withdrawals:
        return {
            "pattern": "SALE",
            "confidence": 0.7,
            "severity": "HIGH",
            "tax_impact": "TAXABLE_INCOME",
            "corrections": [{
                "tx_id": deposits[0].tx_id,
                "action": "CHANGE_TO_TRADE",
                "requires_user_input": "asset_sold",
                "reason": "Proceeds from selling Ordinal/Rune"
            }]
        }
    
    return None  # No pattern detected
```

---

## UI Report Structure

### Correction Report Card Component

```jsx
<CorrectionCard 
  pattern="MINT_BUY"
  confidence={0.95}
  severity="HIGH"
  taxImpact="ESTABLISHES_COST_BASIS"
>
  <Header>
    ⚠️ Mint/Buy Pattern Detected
    <ConfidenceBadge>95% Confidence</ConfidenceBadge>
  </Header>
  
  <AffectedTransactions>
    <Transaction>
      📅 2025-03-15 10:30
      🔻 Withdrawal: -0.00156 BTC
      TxID: abc123...
    </Transaction>
    <Transaction>
      📅 2025-03-15 10:31
      🔺 Deposit: +0.00000546 BTC (Dust)
      TxID: abc123...
    </Transaction>
  </AffectedTransactions>
  
  <RecommendedActions>
    <Action priority="critical">
      1️⃣ IGNORE Deposit (546 sats)
      ⚠️ Important: Mark as "Ignored" in CoinLedger, do NOT delete
      Reason: Dust wrapper for Ordinal/Rune (not taxable income)
    </Action>
    
    <Action priority="high">
      2️⃣ CHANGE Withdrawal to Trade
      Original: Withdrawal (-0.00156 BTC)
      New: Trade
        • Sent: 0.00156 BTC
        • Received: [Verify on Ordiscan ↗]
    </Action>
  </RecommendedActions>
  
  <TaxImpact>
    💰 Tax Impact: Establishes cost basis for asset acquisition
    Without correction: Dust appears as income + no cost basis for future sale
  </TaxImpact>
  
  <Actions>
    <Button primary onClick={viewOnOrdiscan}>
      🔍 View on Ordiscan
    </Button>
    <Button onClick={applyCorrection}>
      ✅ Apply Corrections
    </Button>
    <Button secondary onClick={skip}>
      Skip
    </Button>
  </Actions>
</CorrectionCard>
```

### Summary Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│ 📊 Tax Correction Summary for 2025                         │
├─────────────────────────────────────────────────────────────┤
│ Total Issues Found: 47                                      │
│                                                              │
│ By Severity:                                                │
│ 🔴 HIGH (32)    - Requires immediate attention              │
│ 🟡 MEDIUM (10)  - Review recommended                        │
│ 🟢 LOW (5)      - Optional optimization                     │
│                                                              │
│ By Pattern:                                                 │
│ • Mint/Buy: 18 cases                                        │
│ • Bulk Mint: 8 cases                                        │
│ • Gas Fees: 12 cases                                        │
│ • Sales: 6 cases                                            │
│ • Self Transfer: 3 cases                                    │
│                                                              │
│ Estimated Tax Impact:                                       │
│ • Cost Basis Corrections: $X,XXX                            │
│ • Deductible Fees: $XXX                                     │
│ • Avoided Phantom Income: $X,XXX                            │
│                                                              │
│ [Apply All High Confidence] [Export CSV] [Review Details]   │
└─────────────────────────────────────────────────────────────┘
```

---

## Critical Implementation Notes

### 1. Dust Detection Threshold
```python
DUST_THRESHOLDS = {
    "primary": 0.00000546,    # 546 sats (most common)
    "secondary": 0.00000330,  # 330 sats
    "max": 0.00001            # 10,000 sats (flexible upper bound)
}

def is_dust(amount):
    return abs(amount) <= DUST_THRESHOLDS["max"]
```

### 2. TxID Matching Priority
1. **Exact TxID match** (confidence: 1.0)
2. **Time window ±5 minutes + amount similarity** (confidence: 0.8-0.9)
3. **Manual user confirmation** for ambiguous cases (confidence: user-defined)

### 3. "IGNORE" vs "DELETE" Warning
**CRITICAL USER EDUCATION:**

```
⚠️ IMPORTANT: Do NOT Delete Dust Deposits!

❌ WRONG: Deleting the transaction
   Result: No cost basis → Tax bomb when selling

✅ CORRECT: Mark as "Ignored" in CoinLedger
   Result: Preserves acquisition record, prevents future tax issues
```

### 4. Ordiscan Integration
```python
def get_ordiscan_link(tx_id):
    return f"https://ordiscan.com/tx/{tx_id}"

def fetch_asset_info(tx_id):
    """
    Query Ordiscan API to get asset name
    Fallback: Prompt user to manually check
    """
    try:
        # API call to Ordiscan
        response = requests.get(f"https://ordiscan.com/api/tx/{tx_id}")
        if response.ok:
            data = response.json()
            return data.get("inscription_name") or data.get("rune_name")
    except:
        pass
    
    return "UNKNOWN_ASSET (Check Ordiscan manually)"
```

---

## Comparison with Original ANALYSIS_LOGIC.md

### What We Keep:
✅ UnifiedTransaction data model  
✅ 3-tier matching framework (Exact TxID → Fuzzy → Manual)  
✅ Anomaly detection infrastructure  
✅ Performance considerations  

### What We Enhance:
🔄 **Pattern Detection:** Generic matching → 5 specific Ordinals/Runes scenarios  
🔄 **Tax Focus:** General reconciliation → Tax correction recommendations  
🔄 **User Guidance:** Technical report → Actionable correction steps  
🔄 **External Integration:** None → Ordiscan API for asset verification  

### What We Add:
➕ Dust detection logic  
➕ Bulk transaction handling  
➕ Self-transfer identification  
➕ Tax impact calculations  
➕ "IGNORE" vs "DELETE" warnings  
➕ Confidence scoring per pattern  

---

## Next Steps for Implementation

1. **Update ReconciliationEngine** (`src/reconciliation/engine.py`)
   - Add `detect_ordinals_pattern()` method
   - Implement 5 scenario detection logic
   - Add Ordiscan API integration

2. **Create CorrectionReport Component** (`frontend/src/components/CorrectionReport.tsx`)
   - Pattern-specific card layouts
   - Ordiscan link buttons
   - Apply/Skip action handlers

3. **Update API Endpoint** (`src/api/server.py`)
   - Return correction suggestions instead of just matches/conflicts
   - Include confidence scores and tax impact

4. **Add User Education**
   - Modal explaining "IGNORE" vs "DELETE"
   - Tooltips for each correction type
   - Link to tax reporting guide

---

## Version History

### v2.0 (2026-01-27)
- Complete rewrite based on `correction scenario.md`
- Added 5 Ordinals/Runes-specific patterns
- Ordiscan integration
- Enhanced UI mockups
- Tax correction focus
- Confidence scoring system
