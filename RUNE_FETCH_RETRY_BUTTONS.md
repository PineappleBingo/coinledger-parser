# Rune Fetch Retry Buttons - Implementation Complete

**Date:** 2026-02-02  
**Status:** ✅ COMPLETE

---

## Summary

Implemented on-demand Rune information fetching with retry buttons, allowing users to manually fetch Rune data from multiple API sources (OKLink and UniSat) when automatic fetching fails.

---

## Features Implemented

### 1. **Backend API Endpoint**
- New endpoint: `POST /api/fetch-rune-info`
- Supports two API sources: OKLink and UniSat
- Returns Rune name and amount
- Proper error handling and timeouts

### 2. **Frontend Retry Buttons**
- Two buttons: "Fetch from OKLink" and "Fetch from UniSat"
- Only shown when Rune name is placeholder (e.g., `RUNE_f13e8aa1`)
- Loading states with spinner animation
- Success/error feedback
- Updates UI immediately after successful fetch

### 3. **Fallback Strategy**
- Primary: OKLink API
- Fallback: UniSat API
- User can manually choose which API to use
- Retry as many times as needed

---

## User Flow

### Step 1: Analysis Detects Placeholder

When analysis runs, if Rune name couldn't be fetched:
- Shows: `RUNE_f13e8aa1` (placeholder)
- Displays: Orange Rune preview box
- Shows: Two retry buttons

### Step 2: User Clicks Retry Button

User can click either:
- **"Fetch from OKLink"** (blue button)
- **"Fetch from UniSat"** (orange button)

### Step 3: Fetching State

Button shows:
- Spinner animation
- Text: "Fetching..."
- Other button disabled

### Step 4: Success

If fetch succeeds:
- Rune name updates immediately
- Shows success message: "✅ Successfully fetched: UNCOMMON•GOODS"
- Buttons disappear
- Rune amount updates

### Step 5: Error

If fetch fails:
- Shows error message
- Buttons remain visible
- User can try other API source

---

## Files Modified

### Backend

**1. `src/api/server.py`**

Added new endpoint:
```python
@app.post("/api/fetch-rune-info")
async def fetch_rune_info(request: FetchRuneRequest):
    """
    Fetch Rune information for a specific transaction using specified API source.
    Supports OKLink and UniSat APIs.
    """
    # ... implementation
```

**Features:**
- Validates transaction ID
- Supports OKLink and UniSat APIs
- 10-second timeout
- Proper error handling
- Returns Rune name and amount

### Frontend

**2. `frontend/src/components/RuneFetchButtons.tsx`** (NEW)

New component with retry buttons:
```typescript
export const RuneFetchButtons: React.FC<RuneFetchButtonsProps> = ({ txId, onRuneFetched }) => {
    // ... implementation
}
```

**Features:**
- Two API source buttons
- Loading states
- Error display
- Callback on success

**3. `frontend/src/components/CorrectionReport.tsx`**

Updated RunePreview component:
```typescript
const RunePreview = ({ runeName, txId, metadata }) => {
    const [fetchedRuneName, setFetchedRuneName] = useState<string | null>(null);
    const [fetchedRuneAmount, setFetchedRuneAmount] = useState<string | null>(null);
    
    const handleRuneFetched = (name, amount, source) => {
        setFetchedRuneName(name);
        setFetchedRuneAmount(amount);
    };
    
    // Show buttons if placeholder
    const isPlaceholder = runeName.startsWith('RUNE_');
    
    {isPlaceholder && !fetchedRuneName && (
        <RuneFetchButtons txId={txId} onRuneFetched={handleRuneFetched} />
    )}
}
```

---

## API Details

### OKLink API

**Endpoint:**
```
GET https://www.oklink.com/api/v5/explorer/btc/runes-transaction-list?txId={txId}
```

**Response:**
```json
{
  "data": [{
    "runeName": "UNCOMMON•GOODS",
    "symbol": "UNCOMMON•GOODS",
    "amount": "1000000"
  }]
}
```

### UniSat API

**Endpoint:**
```
GET https://open-api.unisat.io/v1/indexer/tx/{txId}
```

**Response:**
```json
{
  "data": {
    "vout": [{
      "runes": [{
        "runeName": "UNCOMMON•GOODS",
        "amount": "1000000"
      }]
    }]
  }
}
```

---

## UI Screenshots (Expected)

### Before Fetch (Placeholder):
```
┌─────────────────────────────────────────┐
│ 🔮 RUNE_f13e8aa1                        │
│    Amount: Unknown                      │
│                                         │
│    Ordinals.com | OKLink                │
│                                         │
│    Failed to fetch Rune name. Try:      │
│    [Fetch from OKLink] [Fetch from      │
│     UniSat]                             │
└─────────────────────────────────────────┘
```

### During Fetch:
```
┌─────────────────────────────────────────┐
│ 🔮 RUNE_f13e8aa1                        │
│    Amount: Unknown                      │
│                                         │
│    Ordinals.com | OKLink                │
│                                         │
│    Failed to fetch Rune name. Try:      │
│    [⟳ Fetching...] [Fetch from UniSat]  │
│                      (disabled)         │
└─────────────────────────────────────────┘
```

### After Successful Fetch:
```
┌─────────────────────────────────────────┐
│ 🔮 UNCOMMON•GOODS                       │
│    Amount: 1,000,000                    │
│                                         │
│    Ordinals.com | OKLink                │
│                                         │
│    ✅ Successfully fetched:              │
│       UNCOMMON•GOODS                    │
└─────────────────────────────────────────┘
```

### After Fetch Error:
```
┌─────────────────────────────────────────┐
│ 🔮 RUNE_f13e8aa1                        │
│    Amount: Unknown                      │
│                                         │
│    Ordinals.com | OKLink                │
│                                         │
│    Failed to fetch Rune name. Try:      │
│    [Fetch from OKLink] [Fetch from      │
│     UniSat]                             │
│                                         │
│    ⚠️ Rune data not found on OKLink     │
└─────────────────────────────────────────┘
```

---

## Testing Instructions

### 1. Start Services

Both backend and frontend should auto-reload:
```bash
# Backend (already running)
uvicorn src.api.server:app --reload

# Frontend (already running)
npm run dev
```

### 2. Test Scenario

1. Upload CSV
2. Enter wallets
3. Click "Fetch & Preview"
4. Click "Run Analysis"
5. Find RUNE_RECEIVE pattern with placeholder name

### 3. Verify Retry Buttons

**Check buttons appear:**
- [ ] Two buttons visible
- [ ] "Fetch from OKLink" (blue)
- [ ] "Fetch from UniSat" (orange)
- [ ] Text: "Failed to fetch Rune name. Try fetching from:"

### 4. Test OKLink Fetch

1. Click "Fetch from OKLink"
2. **Verify loading state:**
   - [ ] Button shows spinner
   - [ ] Text changes to "Fetching..."
   - [ ] Other button disabled
3. **Verify success:**
   - [ ] Rune name updates (e.g., "UNCOMMON•GOODS")
   - [ ] Amount updates
   - [ ] Success message appears
   - [ ] Buttons disappear

### 5. Test UniSat Fetch (if OKLink fails)

1. If OKLink fails, click "Fetch from UniSat"
2. Same verification as above

### 6. Test Error Handling

If both APIs fail:
- [ ] Error message displays
- [ ] Buttons remain visible
- [ ] Can retry

---

## Browser Console Test

```javascript
// Find Rune preview with placeholder
const runePreview = Array.from(document.querySelectorAll('div')).find(
  div => div.textContent?.includes('RUNE_') && div.textContent?.includes('fetch')
);

if (runePreview) {
  console.log('✅ Rune preview with placeholder found');
  
  // Check buttons
  const oklinkBtn = Array.from(runePreview.querySelectorAll('button')).find(
    btn => btn.textContent?.includes('OKLink')
  );
  const unisatBtn = Array.from(runePreview.querySelectorAll('button')).find(
    btn => btn.textContent?.includes('UniSat')
  );
  
  console.log('OKLink button:', oklinkBtn ? '✅ FOUND' : '❌ MISSING');
  console.log('UniSat button:', unisatBtn ? '✅ FOUND' : '❌ MISSING');
  
  // Click OKLink button
  if (oklinkBtn) {
    console.log('Clicking OKLink button...');
    oklinkBtn.click();
  }
} else {
  console.log('❌ Rune preview with placeholder NOT found');
}
```

---

## Error Handling

### Backend Errors

**Invalid Transaction ID:**
```json
{
  "detail": "Invalid transaction ID"
}
```
**Status:** 400

**API Timeout:**
```json
{
  "detail": "OKLINK API timeout"
}
```
**Status:** 504

**API Error:**
```json
{
  "detail": "OKLINK API error: [error message]"
}
```
**Status:** 502

**Rune Not Found:**
```json
{
  "detail": "Rune data not found on OKLink"
}
```
**Status:** 404

### Frontend Error Display

All errors shown in red box:
```
⚠️ [Error message]
```

---

## Success Criteria

All of the following must be true:

✅ **Backend:**
- `/api/fetch-rune-info` endpoint exists
- Supports OKLink and UniSat
- Returns Rune name and amount
- Proper error handling

✅ **Frontend:**
- Retry buttons appear for placeholders
- Buttons work correctly
- Loading states display
- Success updates UI immediately
- Errors display clearly

✅ **User Experience:**
- Can retry failed fetches
- Can choose API source
- Immediate feedback
- No page reload needed

---

## Advantages Over Previous Approach

### Before:
- ❌ Had to re-fetch ALL blockchain data
- ❌ No way to retry individual transactions
- ❌ No API source choice
- ❌ Time-consuming

### After:
- ✅ Retry individual transactions
- ✅ Choose API source (OKLink or UniSat)
- ✅ Instant feedback
- ✅ No need to re-fetch everything
- ✅ Better UX

---

## Future Enhancements

1. **Auto-retry with fallback:**
   - Try OKLink first
   - Auto-fallback to UniSat if fails
   - Show which API was used

2. **Batch retry:**
   - "Retry All Failed" button
   - Fetches all placeholders at once

3. **Cache fetched data:**
   - Store in localStorage
   - Persist across sessions

4. **More API sources:**
   - Add Hiro API
   - Add Ordinals.com API

---

## Status

**Implementation:** ✅ COMPLETE  
**Testing:** ⏳ AWAITING USER VERIFICATION  
**Expected Outcome:** Users can manually retry fetching Rune info from OKLink or UniSat when automatic fetch fails.

**This provides a much better UX than requiring a full re-fetch of all blockchain data!**
