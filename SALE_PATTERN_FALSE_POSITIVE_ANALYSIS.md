# SALE Pattern False Positive Analysis

**Date:** 2026-02-02  
**Transaction:** 2025-06-17 11:19:00, Deposit, +0.00400935 BTC

---

## Issue Summary

A transaction is being classified as SALE pattern, but:
- ❌ No Ordinal/Rune preview displays
- ❌ Asset tag shows "BTC" instead of "ORDINAL/RUNE"
- ❌ Shows generic "USER_INPUT_REQUIRED" message
- ⚠️ Console shows Rune API calls failing for `RUNE_f13e8aa1`

---

## Root Cause Analysis

### Evidence from Console Logs:

```
www.oklink.com/api/v5/explorer/btc/runes-transaction-list?txId=f13e8aa1...
api.hiro.so/runes/v1/etchings/RUNE_f13e8aa1
[API] All Rune APIs failed, using metadata fallback
```

**This means:**
1. Frontend IS trying to fetch Rune info
2. Transaction ID: `f13e8aa1924f7bc875ab121fd97782d2e6d2aaab16a688c4165b9272d56bd434`
3. Using placeholder Rune name: `RUNE_f13e8aa1`
4. APIs are failing (404/400 errors)

### Possible Scenarios:

#### Scenario A: This IS a Sale (BTC payment received)
**Expected:**
- Deposit = BTC payment from buyer
- Withdrawal = Ordinal/Rune sent to buyer (in different tx group)
- My fix should find the withdrawal within 48 hours

**Why it's failing:**
- Withdrawal might be >48 hours away
- Withdrawal might not have metadata populated
- Withdrawal might be in CEX data, not blockchain data

#### Scenario B: This is NOT a Sale (Rune/Ordinal received)
**Reality:**
- Deposit = Receiving a Rune/Ordinal (airdrop, gift, transfer)
- NOT a sale at all
- Should be classified differently

**Why it's being misclassified:**
- Amount is not dust (0.004 BTC)
- No matching withdrawal in same group
- Meets SALE pattern criteria

#### Scenario C: Metadata Not Populated
**Reality:**
- This IS a Rune/Ordinal deposit
- But blockchain client didn't populate metadata
- So it looks like plain BTC

**Why metadata might be missing:**
- Rune detection failed in `_extract_rune_name`
- Transaction structure is different
- OP_RETURN data not in expected format

---

## Investigation Steps

### 1. Check Transaction Metadata

Need to verify if the deposit transaction has metadata:

```python
# In backend, check what metadata exists for this transaction
tx_id = "f13e8aa1924f7bc875ab121fd97782d2e6d2aaab16a688c4165b9272d56bd434"
# Does it have metadata.asset_type?
# Does it have metadata.rune_name?
```

### 2. Check Blockchain Data

Need to see the raw blockchain transaction:
- Is it a Rune transaction?
- Does it have OP_RETURN data?
- What does the scriptpubkey look like?

### 3. Check Pattern Classification

Questions:
- Is this really a SALE?
- Or is it a RECEIVE of a Rune?
- Should we have a separate pattern for "Rune/Ordinal Received"?

---

## Hypothesis

**Most Likely:** This is a **Rune RECEIVE** (not a sale), but:

1. **Backend Detection Failed:**
   - `_extract_rune_name` didn't find the Rune
   - Metadata not populated with `asset_type: 'RUNE'`
   - Transaction looks like plain BTC

2. **Pattern Misclassification:**
   - Deposit only, not dust → Classified as SALE
   - But it's actually a Rune receive
   - Should be classified as "RUNE_RECEIVE" or similar

3. **Frontend Confusion:**
   - Trying to fetch Rune info using placeholder name
   - APIs failing because `RUNE_f13e8aa1` is not a real Rune name
   - No preview displays because metadata is missing

---

## Recommended Fixes

### Fix 1: Improve Rune Detection (Backend)

**File:** `src/reconciliation/blockchain.py`

Check if `_extract_rune_name` is working correctly:
- Is it finding OP_RETURN data?
- Is it parsing the Rune protocol correctly?
- Should we use APIs to get Rune name instead of parsing?

### Fix 2: Add "RECEIVE" Pattern

**New Pattern:** Detect when someone receives a Rune/Ordinal (not a sale)

```python
def detect_rune_receive_pattern(tx_group):
    """
    Pattern: Deposit with Rune/Ordinal metadata, not a sale
    """
    deposits = [t for t in tx_group if t.tx_type == 'Deposit']
    
    if len(deposits) == 1:
        deposit = deposits[0]
        if hasattr(deposit, 'metadata') and deposit.metadata:
            if deposit.metadata.get('asset_type') in ['ORDINAL', 'RUNE']:
                # This is receiving a Rune/Ordinal, not a sale
                return {
                    "pattern": "RUNE_RECEIVE",
                    "action": "NO_ACTION_NEEDED",
                    "reason": "Received Rune/Ordinal - not taxable until sold"
                }
```

### Fix 3: Check SALE Pattern Logic

**Current Logic:**
```python
if deposits and not withdrawals:
    if not is_dust(deposits[0].amount):
        # Classify as SALE
```

**Problem:** This assumes all non-dust deposits are sales!

**Better Logic:**
```python
if deposits and not withdrawals:
    deposit = deposits[0]
    
    # Check if deposit itself is a Rune/Ordinal
    if hasattr(deposit, 'metadata') and deposit.metadata:
        if deposit.metadata.get('asset_type') in ['ORDINAL', 'RUNE']:
            # This is receiving a Rune/Ordinal, NOT a sale
            return None  # Let other patterns handle it
    
    # Only classify as SALE if it's BTC (payment)
    if not is_dust(deposit.amount):
        # Now search for Ordinal withdrawal...
```

---

## Immediate Action Required

### Step 1: Verify Transaction Type

Check the actual blockchain transaction:
```
https://mempool.space/tx/f13e8aa1924f7bc875ab121fd97782d2e6d2aaab16a688c4165b9272d56bd434
```

Look for:
- Is this a Rune transaction?
- Does it have OP_RETURN data?
- What is the actual Rune name?

### Step 2: Check Backend Logs

Look at backend terminal for:
- Did `_extract_rune_name` find anything?
- What metadata was set for this transaction?
- Any errors during blockchain data fetch?

### Step 3: Test Metadata

Add debug logging to see what metadata exists:
```python
# In detect_sale_pattern
print(f"Deposit metadata: {deposit_tx.metadata}")
```

---

## Questions for User

1. **Is this transaction a SALE or a RECEIVE?**
   - Did you sell a Rune and receive BTC?
   - Or did you receive a Rune?

2. **What does the blockchain explorer show?**
   - Check mempool.space or ordinals.com
   - Is this a Rune transaction?
   - What is the actual Rune name?

3. **Should RECEIVE be a separate pattern?**
   - Should we distinguish between:
     - SALE (sold Rune, received BTC)
     - RECEIVE (received Rune, no payment)

---

## Next Steps

Based on your answer:

**If it's a SALE:**
- Fix the 48-hour search (might need wider window)
- Improve withdrawal matching logic

**If it's a RECEIVE:**
- Fix Rune detection in blockchain.py
- Add RUNE_RECEIVE pattern
- Update SALE pattern to exclude Rune deposits

**If metadata is missing:**
- Debug `_extract_rune_name`
- Consider using APIs for Rune detection
- Fix OP_RETURN parsing
