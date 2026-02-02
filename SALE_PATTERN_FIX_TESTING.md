# SALE Pattern Fix - Testing Instructions

**Date:** 2026-02-02  
**Fix Applied:** Enhanced SALE pattern to search for Ordinal/Rune metadata in tx_group

---

## What Was Changed

**File:** `src/reconciliation/ordinals_detector.py`  
**Function:** `detect_sale_pattern`  
**Lines:** 210-239

### Changes:
1. Added search through all transactions in `tx_group` for Ordinal/Rune metadata
2. If found, use that transaction's metadata instead of the deposit's metadata
3. Pass the Ordinal transaction object to frontend (line 239)

---

## Testing Steps

### 1. Restart Backend
The backend should auto-reload, but if not:
```bash
# The uvicorn server should auto-reload
# Check terminal for "Reloading..." message
```

### 2. Test in Browser
1. Open http://localhost:5173
2. Upload CSV
3. Enter wallets from SOURCE B.MD
4. Fetch blockchain data
5. Run analysis
6. Find SALE pattern

### 3. Verify Fix
Check if SALE pattern now shows:
- [ ] Asset tag shows "ORDINAL" instead of "BTC"
- [ ] OrdinalPreview component appears (purple box)
- [ ] Image or fallback icon is visible
- [ ] Inscription name/number is displayed
- [ ] Links to Ordinals.com work

---

## Expected Behavior

**If the Ordinal withdrawal IS in the same tx_group:**
✅ Fix will work
✅ Ordinal preview will display
✅ Asset tag will show "ORDINAL"

**If the Ordinal withdrawal is NOT in the same tx_group:**
❌ Fix will NOT work
❌ Will still show "BTC" and no preview
❌ Need to implement Option 1 from analysis (search all blockchain txs)

---

## Diagnostic Commands

### Check if Ordinal withdrawal exists:
Run in browser console after analysis:
```javascript
// Find SALE pattern
const salePattern = Array.from(document.querySelectorAll('div')).find(
  div => div.textContent?.includes('Sale Pattern')
);

if (salePattern) {
  // Check affected transactions
  const txList = salePattern.querySelector('[class*="affected"]');
  console.log('Affected transactions:', txList?.textContent);
  
  // Check for Ordinal preview
  const ordinalPreview = salePattern.querySelector('.bg-purple-50');
  console.log('Ordinal preview:', ordinalPreview ? 'FOUND' : 'NOT FOUND');
  
  // Check asset tag
  const assetTag = salePattern.querySelector('[class*="ORDINAL"]');
  console.log('Asset tag:', assetTag?.textContent || 'NOT FOUND');
}
```

---

## If Fix Doesn't Work

### Next Steps:
1. **Verify the Ordinal withdrawal exists in blockchain data**
2. **Check if it's in a different transaction group**
3. **Implement comprehensive fix:**
   - Modify `detect_sale_pattern` to accept all blockchain transactions
   - Search for Ordinal withdrawal within 24-hour window
   - Match by timestamp proximity

### Alternative Solution:
Improve transaction grouping in `engine.py` to ensure Ordinal withdrawals are grouped with their corresponding BTC deposits.

---

## Current Status

**Fix Applied:** ✅ Partial fix (searches tx_group)  
**Tested:** ⏳ Awaiting user testing  
**Expected Result:** May or may not work depending on transaction grouping

**If it works:** Great! Issue resolved.  
**If it doesn't work:** Need to implement more comprehensive fix (search all blockchain txs).
