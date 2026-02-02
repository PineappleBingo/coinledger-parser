# Manual Verification Guide: Ordinal Preview Features

**Date:** 2026-02-02  
**Purpose:** Verify all Ordinal preview features are working correctly

---

## Prerequisites

1. **Backend running**: `uvicorn src.api.server:app --reload`
2. **Frontend running**: `npm run dev`
3. **Browser**: Open http://localhost:5173

---

## Test Steps

### Step 1: Upload CSV and Fetch Blockchain Data

1. Navigate to http://localhost:5173
2. Click "Upload CSV" button
3. Select file: `import/Xverse Import transactions - Sheet1.csv`
4. Enter wallet address: `bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql`
5. Click "Fetch & Preview" button
6. Wait for blockchain data to load (should see transaction count)

### Step 2: Run Analysis

1. Click "Run Analysis" button
2. Wait for patterns to be detected
3. Look for **BULK_MINT** or **MINT_BUY** patterns in the results

### Step 3: Verify Ordinal Preview Component

Find a pattern with Ordinal transactions (look for 🎨 ORDINAL tags) and check the following:

#### ✅ Checklist: Ordinal Preview Features

**Visual Elements:**
- [ ] **Purple-tinted box** appears (bg-purple-50 with purple border)
- [ ] **Image or icon** is displayed on the left side
  - If API succeeds: Real ordinal image (16x16 rounded)
  - If API fails: Purple fallback icon (ImageIcon)
  - While loading: Gray pulsing skeleton

**Text Content:**
- [ ] **Name is displayed** as a clickable link
  - Format: Either actual name OR "Inscription #{number}"
  - Color: Purple text (text-purple-700)
  - Has external link icon next to it
- [ ] **Inscription number** shown below name
  - Format: "Inscription #12345"
  - Small gray text

**Links:**
- [ ] **Ordinals.com link** works
  - URL format: `https://ordinals.com/inscription/{inscription_id}`
  - Opens in new tab
  - Clickable from both image and name
- [ ] **UniSat link** (if implemented - check code)
  - Should appear as additional link

**Loading States:**
- [ ] Shows skeleton loader while fetching API data
- [ ] Transitions smoothly from loading to content

**Error Handling:**
- [ ] If image fails to load, shows fallback icon
- [ ] If API fails, still shows "View on Ordinals.com" link

---

## Code Verification

### OrdinalPreview Component Location
**File:** `frontend/src/components/CorrectionReport.tsx`  
**Lines:** 56-150

### Key Features in Code:

```typescript
// ✅ Uses inscription_id from metadata
const inscriptionId = transaction.metadata?.inscription_id || transaction.tx_id;

// ✅ Fetches from API
fetchOrdinalInfo(inscriptionId).then(data => {
    setInfo(data);
    setLoading(false);
});

// ✅ Displays image
{info && info.content_url ? (
    <img src={info.content_url} alt={...} />
) : (
    <ImageIcon /> // Fallback
)}

// ✅ Displays name or inscription number
{info.name || `Inscription #${info.inscription_number}`}

// ✅ Shows inscription number
<div>Inscription #{info.inscription_number}</div>

// ✅ Links to Ordinals.com
<a href={`https://ordinals.com/inscription/${inscriptionId}`}>
```

---

## Expected Results

### When API Succeeds:
```
┌─────────────────────────────────────────┐
│  [Image]  Cool Ordinal #12345          │
│           Inscription #12345            │
│           Collection: My Collection     │
│           🔗 (External link icon)       │
└─────────────────────────────────────────┘
```

### When API Fails (Fallback):
```
┌─────────────────────────────────────────┐
│  [Icon]   View on Ordinals.com         │
│           Click to verify inscription   │
│           🔗 (External link icon)       │
└─────────────────────────────────────────┘
```

### While Loading:
```
┌─────────────────────────────────────────┐
│  [Pulse]  ████████████                  │
│           ████████                      │
└─────────────────────────────────────────┘
```

---

## Browser Console Checks

Open DevTools (F12) and check:

1. **Network Tab:**
   - [ ] API calls to UniSat/Hiro/OKLink are visible
   - [ ] Check response status (200 = success, 429 = rate limit, 404 = not found)

2. **Console Tab:**
   - [ ] Look for API logs: `[API] UniSat success:` or `[API] Hiro success:`
   - [ ] Check for rate limit warnings: `[API] UniSat rate limit reached`
   - [ ] No JavaScript errors

---

## Common Issues & Solutions

### Issue: No preview appears
**Check:**
- Is `actionType === 'CHANGE_TO_TRADE'`?
- Does transaction have `metadata.inscription_id`?
- Is OrdinalPreview component being called?

### Issue: Image doesn't load
**Check:**
- Network tab: Did API call succeed?
- Console: Any CORS errors?
- Fallback icon should still appear

### Issue: "View on Ordinals.com" instead of name
**Reason:** API failed or returned no data
**Expected:** Fallback behavior is working correctly

### Issue: Links don't work
**Check:**
- URL format in browser: Should be `https://ordinals.com/inscription/{id}`
- Opens in new tab?
- Check if `inscription_id` is valid

---

## Quick Test Script

Run this in browser console to check if inscription ID exists:

```javascript
// Get first BULK_MINT pattern
const bulkMint = window.__REACT_DEVTOOLS_GLOBAL_HOOK__?.renderers?.get(1)?.
    findFiberByHostInstance(document.querySelector('[data-pattern="BULK_MINT"]'));

// Check if OrdinalPreview is rendered
const preview = document.querySelector('.bg-purple-50');
console.log('Ordinal Preview found:', !!preview);

// Check inscription ID
const inscriptionLink = document.querySelector('a[href*="ordinals.com/inscription"]');
console.log('Inscription link:', inscriptionLink?.href);
```

---

## Success Criteria

All of the following must be true:

✅ **Visual:**
- Purple-tinted preview box appears
- Image or fallback icon is visible
- Text is readable and properly formatted

✅ **Content:**
- Name or "Inscription #..." is displayed
- Inscription number is shown
- Links are clickable

✅ **Functionality:**
- API calls are made (check Network tab)
- Loading states work
- Error handling works (fallback to icon/link)
- Links open in new tab

✅ **No Errors:**
- No JavaScript errors in console
- No broken images (fallback works)
- No CORS errors

---

## Report Template

After testing, fill out:

```
Date: ___________
Tester: ___________

✅ Ordinal Preview Features:
- [ ] Image displayed: YES / NO / FALLBACK
- [ ] Name displayed: YES / NO
- [ ] Inscription number shown: YES / NO
- [ ] Ordinals.com link works: YES / NO
- [ ] UniSat link works: YES / NO / NOT FOUND
- [ ] Loading state works: YES / NO
- [ ] Error handling works: YES / NO

Issues found:
_______________________________________
_______________________________________

Screenshots attached: YES / NO
```

---

## Next Steps

If all features work:
- ✅ Mark verification complete in task.md
- ✅ Update walkthrough.md with confirmed features

If issues found:
- 🔧 Document specific errors
- 🔧 Check browser console for details
- 🔧 Report to developer with screenshots
