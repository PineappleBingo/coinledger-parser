# SALE Pattern Display Issue - Root Cause Analysis

**Date:** 2026-02-02  
**Issue:** SALE pattern doesn't display Ordinal image, name, or inscription number

---

## Problem Analysis

### Current Behavior (from screenshot):
- **Affected Transactions:** Shows only BTC deposit (2025-01-12 06:04:18)
- **Asset Tag:** Shows "BTC" instead of "ORDINAL"
- **No Preview:** OrdinalPreview component not visible
- **Sent Asset:** Shows "USER_INPUT_REQUIRED ORDINAL/RUNE"

### Root Cause:

**The SALE pattern is fundamentally different from MINT_BUY:**

**MINT_BUY Pattern:**
- CEX Withdrawal (BTC payment) + Blockchain Deposit (Ordinal wrapper)
- Both transactions are in the SAME group
- The Ordinal metadata is on the deposit transaction

**SALE Pattern:**
- Blockchain Withdrawal (sending Ordinal to buyer) + Blockchain Deposit (receiving BTC payment)
- These transactions might be in DIFFERENT groups or different times
- The Ordinal metadata is on the WITHDRAWAL, not the deposit
- Current code only looks at the deposit (which is just BTC)

### Why It's Not Working:

1. **Transaction Grouping:**
   - The SALE detection looks for "deposits and not withdrawals" (line 207)
   - This finds the BTC deposit but MISSES the Ordinal withdrawal
   - The Ordinal withdrawal might be in a different tx_group

2. **Metadata Location:**
   - The deposit is BTC (payment received) - NO Ordinal metadata
   - The withdrawal is the Ordinal being sent - HAS Ordinal metadata
   - Current code tries to get metadata from deposit (line 210)

3. **My Fix Attempt:**
   - I added code to search tx_group for Ordinal metadata
   - BUT if the withdrawal is in a different group, it won't be found

---

## Solution Options

### Option 1: Search All Blockchain Transactions (RECOMMENDED)
Instead of only searching the current tx_group, search ALL blockchain transactions around the same time for an outgoing Ordinal.

**Pros:**
- Will find the Ordinal even if it's in a different group
- More accurate detection

**Cons:**
- Requires passing all blockchain transactions to the function
- More complex logic

### Option 2: Improve Transaction Grouping
Change the reconciliation engine to group Ordinal withdrawals with their corresponding BTC deposits.

**Pros:**
- Cleaner solution
- Fixes the root cause

**Cons:**
- Requires changes to engine.py
- More invasive change

### Option 3: Manual User Input (CURRENT STATE)
Require user to manually specify which Ordinal was sold.

**Pros:**
- Simple, no code changes needed
- User has full control

**Cons:**
- Poor user experience
- Defeats the purpose of automation

---

## Recommended Fix

**Implement Option 1** with these steps:

1. **Modify `detect_sale_pattern` signature:**
   ```python
   def detect_sale_pattern(
       tx_group: List[UnifiedTransaction], 
       my_wallets: List[str],
       all_blockchain_txs: List[UnifiedTransaction]  # NEW
   ) -> Optional[Dict]:
   ```

2. **Search for outgoing Ordinal:**
   ```python
   # Find Ordinal withdrawal around the same time as the BTC deposit
   deposit_time = deposits[0].timestamp
   time_window = timedelta(hours=24)  # Search within 24 hours
   
   ordinal_tx = None
   for tx in all_blockchain_txs:
       # Look for withdrawals with Ordinal metadata
       if tx.tx_type in ['Withdrawal', 'Send']:
           if hasattr(tx, 'metadata') and tx.metadata:
               if tx.metadata.get('asset_type') in ['ORDINAL', 'RUNE']:
                   # Check if it's within the time window
                   time_diff = abs((tx.timestamp - deposit_time).total_seconds())
                   if time_diff < time_window.total_seconds():
                       ordinal_tx = tx
                       break
   ```

3. **Use the found transaction:**
   ```python
   "transaction": ordinal_tx if ordinal_tx else deposits[0]
   ```

---

## Alternative: Quick Fix

If we can't change the function signature, we can:

1. **Check if deposit has Ordinal metadata** (unlikely but possible)
2. **Check all transactions in tx_group** (my current fix)
3. **Fall back to generic message** if not found

This is what I've already implemented, but it won't work if the Ordinal withdrawal is in a different group.

---

## Testing Needed

To verify the fix works, we need to:

1. **Check the actual transaction data:**
   - Is there an Ordinal withdrawal transaction?
   - What timestamp does it have?
   - Is it in the same tx_group as the BTC deposit?

2. **Verify metadata:**
   - Does the withdrawal have `asset_type: 'ORDINAL'`?
   - Does it have `inscription_id`?

3. **Test the fix:**
   - Run analysis again
   - Check if SALE pattern now shows Ordinal preview
   - Verify asset tag shows "ORDINAL" instead of "BTC"

---

## Next Steps

**Immediate:**
1. Test current fix (searches tx_group for Ordinal metadata)
2. If it doesn't work, check if withdrawal is in a different group

**If withdrawal is in different group:**
1. Modify function signature to accept all blockchain transactions
2. Implement time-based search for matching Ordinal withdrawal
3. Update all callers of `detect_sale_pattern`

**Alternative:**
1. Improve transaction grouping in `engine.py`
2. Ensure Ordinal withdrawals are grouped with their BTC deposits
