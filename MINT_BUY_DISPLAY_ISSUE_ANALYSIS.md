# MINT_BUY Pattern Display Issue - Root Cause Analysis

**Date:** 2026-02-02  
**Issue:** Ordinal/Rune names and amounts not displaying in MINT_BUY pattern

---

## Investigation Summary

### Backend Code Review ✅

**1. Blockchain Client (`src/reconciliation/blockchain.py` lines 110-122)**
```python
# Build metadata with asset type and additional info
metadata = {'asset_type': asset_type}

# Extract inscription ID for Ordinals
if asset_type == 'ORDINAL':
    inscription_id = self._extract_inscription_id(tx, address)
    if inscription_id:
        metadata['inscription_id'] = inscription_id

# Extract Rune token name for Runes
if asset_type == 'RUNE':
    rune_name = self._extract_rune_name(tx)
    if rune_name:
        metadata['rune_name'] = rune_name
```
**Status:** ✅ Metadata IS being populated on blockchain deposits

**2. MINT_BUY Pattern Detection (`src/reconciliation/ordinals_detector.py` line 40)**
```python
{
    "tx": withdrawals[0],
    "action": "CHANGE_TO_TRADE",
    ...
    "transaction": deposits[0]  # Include blockchain deposit for asset tags
}
```
**Status:** ✅ Transaction object IS being passed

**3. API Serialization (`src/api/server.py` line 232)**
```python
"metadata": tx.metadata if hasattr(tx, 'metadata') and tx.metadata else {}
```
**Status:** ✅ Metadata IS being serialized to frontend

---

### Frontend Code Review ✅

**1. OrdinalPreview Display Condition (`frontend/src/components/CorrectionReport.tsx` line 423)**
```typescript
{action.transaction && action.transaction.metadata?.asset_type === 'ORDINAL' && (
    <OrdinalPreview
        transaction={action.transaction}
        actionType={action.action_type}
    />
)}
```
**Condition:** Requires `action.transaction.metadata.asset_type === 'ORDINAL'`

**2. RunePreview Display Condition (line 431)**
```typescript
{action.transaction?.metadata?.rune_name && (
    <RunePreview
        runeName={action.transaction.metadata.rune_name}
        txId={action.transaction.tx_id}
        metadata={action.transaction.metadata}
    />
)}
```
**Condition:** Requires `action.transaction.metadata.rune_name` to exist

---

## Root Cause Analysis

### Possible Issues:

1. **Metadata Not Populated on Deposits**
   - **Likelihood:** LOW
   - **Reason:** Code shows metadata IS being set (blockchain.py lines 110-122)
   - **Test:** Need to verify actual blockchain deposits have metadata

2. **Transaction Object Not Passed in MINT_BUY**
   - **Likelihood:** LOW
   - **Reason:** Code shows `deposits[0]` IS being passed (ordinals_detector.py line 40)
   - **Test:** Need to verify API response includes transaction object

3. **API Not Serializing Metadata**
   - **Likelihood:** LOW
   - **Reason:** Code shows metadata IS being serialized (server.py line 232)
   - **Test:** Need to check actual API response JSON

4. **Frontend Condition Not Met**
   - **Likelihood:** MEDIUM
   - **Reason:** Conditions are strict - requires exact metadata fields
   - **Test:** Check browser console for actual data structure

5. **Rune Name is Placeholder Format**
   - **Likelihood:** HIGH
   - **Reason:** Backend uses `RUNE_{txid[:8]}` placeholder
   - **Impact:** RunePreview SHOULD still display with placeholder name
   - **Test:** Verify if placeholder names are being set

---

## Testing Checklist

To identify the exact issue, check:

### Browser DevTools (Frontend)
- [ ] Open http://localhost:5173
- [ ] Upload CSV and run analysis
- [ ] Find MINT_BUY pattern
- [ ] Open DevTools Console
- [ ] Check `action.transaction` object structure
- [ ] Verify `action.transaction.metadata` exists
- [ ] Check `action.transaction.metadata.asset_type` value
- [ ] Check `action.transaction.metadata.inscription_id` (for Ordinals)
- [ ] Check `action.transaction.metadata.rune_name` (for Runes)

### Network Tab (API Response)
- [ ] Open Network tab
- [ ] Run analysis
- [ ] Find `/api/analyze` request
- [ ] Check response JSON
- [ ] Look for `corrections` array
- [ ] Find `CHANGE_TO_TRADE` action
- [ ] Verify `transaction` object exists
- [ ] Verify `metadata` object exists with correct fields

---

## Expected vs Actual

### Expected Behavior:
```json
{
  "action_type": "CHANGE_TO_TRADE",
  "transaction": {
    "date": "2025-12-01",
    "time": "06:09:00",
    "type": "Deposit",
    "amount": 0.00000546,
    "tx_id": "abc123...",
    "source": "BLOCKCHAIN",
    "metadata": {
      "asset_type": "ORDINAL",
      "inscription_id": "abc123...i0"
    }
  }
}
```

### If Ordinal Preview Doesn't Show:
**Check:**
1. Does `transaction` exist? → If NO: Backend issue
2. Does `metadata` exist? → If NO: API serialization issue
3. Does `metadata.asset_type === 'ORDINAL'`? → If NO: Detection issue
4. Does `metadata.inscription_id` exist? → If NO: Extraction issue

### If Rune Preview Doesn't Show:
**Check:**
1. Does `transaction` exist? → If NO: Backend issue
2. Does `metadata` exist? → If NO: API serialization issue
3. Does `metadata.rune_name` exist? → If NO: Extraction issue
4. Is `metadata.rune_name` empty string? → If YES: Detection issue

---

## Quick Browser Console Test

Run this in browser console after loading MINT_BUY pattern:

```javascript
// Find the React component state
const suggestions = window.__REACT_STATE__?.suggestions || [];
const mintBuy = suggestions.find(s => s.pattern === 'MINT_BUY');

if (mintBuy) {
  console.log('MINT_BUY Pattern Found:', mintBuy);
  
  const changeToTrade = mintBuy.recommended_actions?.find(
    a => a.action_type === 'CHANGE_TO_TRADE'
  );
  
  if (changeToTrade) {
    console.log('CHANGE_TO_TRADE Action:', changeToTrade);
    console.log('Has transaction?', !!changeToTrade.transaction);
    console.log('Has metadata?', !!changeToTrade.transaction?.metadata);
    console.log('Metadata:', changeToTrade.transaction?.metadata);
    
    // Check display conditions
    const hasOrdinal = changeToTrade.transaction?.metadata?.asset_type === 'ORDINAL';
    const hasRune = !!changeToTrade.transaction?.metadata?.rune_name;
    
    console.log('Should show OrdinalPreview?', hasOrdinal);
    console.log('Should show RunePreview?', hasRune);
  }
}
```

---

## Next Steps

1. **Manual Browser Test** (RECOMMENDED)
   - Open app in browser
   - Use DevTools to inspect actual data
   - Check console for errors
   - Verify API response structure

2. **Add Debug Logging**
   - Add `console.log` in frontend before preview components
   - Log `action.transaction.metadata` to see actual values

3. **Fix Based on Findings**
   - If metadata missing → Fix backend
   - If transaction missing → Fix pattern detector
   - If API not serializing → Fix server.py
   - If frontend condition wrong → Fix CorrectionReport.tsx

---

## Hypothesis

**Most Likely Issue:** The metadata IS being populated, but:
- Either the `asset_type` is not being set to 'ORDINAL' for ordinal transactions
- Or the `inscription_id` / `rune_name` extraction is failing
- Or the frontend is receiving the data but the display condition is not being met

**Recommended Action:** Use browser DevTools to inspect the actual `action.transaction.metadata` object and compare it to the expected structure.
