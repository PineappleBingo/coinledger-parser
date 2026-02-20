# UI Design Blueprint — Crypto Tax Bridge

**Purpose:** Network-agnostic UI design specification for building a crypto tax reporting tool.  
**Reference Implementation:** Solana Tax Bridge (Next.js / React / TailwindCSS)  
**Target Project:** Bitcoin Tax Bridge (or any blockchain network)  
**Version:** 1.0 — February 18, 2026

---

## 🎨 Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| **Framework** | Next.js 14+ (App Router) | `'use client'` components for interactivity |
| **Language** | TypeScript | Strict mode for type safety |
| **Styling** | TailwindCSS | Dark theme via custom CSS variables |
| **Font** | Inter (Google Fonts) | `font-family: 'Inter', -apple-system, sans-serif` |
| **State** | React `useState` + `useMemo` | No external state library needed |
| **File I/O** | Browser Blob API | JSON download/upload for data caching |

---

## 🎨 Design System

### Color Tokens (CSS Variables)

```css
:root {
  --background: #0a0a0a;      /* Near-black background */
  --foreground: #ededed;       /* Light text */
  --primary: #8b5cf6;          /* Purple accent */
  --primary-dark: #7c3aed;     /* Purple hover */
  --secondary: #10b981;        /* Green accent */
  --danger: #ef4444;           /* Red accent */
  --warning: #f59e0b;          /* Yellow accent */
}
```

### Glassmorphism Effect

```css
.glass {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
```

**Usage:** All card containers, form panels, and modals.

### Scrollbar Styling

```css
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: rgba(255, 255, 255, 0.05); }
::-webkit-scrollbar-thumb { background: rgba(139, 92, 246, 0.5); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(139, 92, 246, 0.7); }
```

### Loading Animation

```css
@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}
.animate-shimmer {
  animation: shimmer 2s infinite linear;
  background: linear-gradient(to right,
    rgba(255,255,255,0.05) 0%,
    rgba(255,255,255,0.1) 50%,
    rgba(255,255,255,0.05) 100%);
  background-size: 1000px 100%;
}
```

---

## 📊 Core Data Model

The universal transaction interface that works across any blockchain:

```typescript
type CoinLedgerType =
  | 'Trade'
  | 'Deposit'
  | 'Withdrawal'
  | 'Income'
  | 'Staking'
  | 'Airdrop'
  | 'Gift Received'
  | 'Gift Sent'
  | 'Casualty Loss'
  | 'Theft Loss'
  | 'Investment Loss'
  | 'Ignored';           // For spam/dust

interface NormalizedTransaction {
  id: string;
  timestamp: Date;
  txHash: string;
  platform: string;       // e.g., "Bitcoin", "Solana"

  // Trade fields
  assetSent?: string;
  amountSent?: number;
  assetReceived?: string;
  amountReceived?: number;

  // Fee fields
  feeCurrency?: string;
  feeAmount?: number;

  // Classification
  type: CoinLedgerType;
  description: string;

  // Metadata
  priceUSD?: number;
  tokenImageUrl?: string;
  tokenAddress?: string;

  // Spam detection
  isSpam: boolean;
  spamConfidence: number;
  spamReasons: string[];

  // Cost analysis
  costBasisUSD?: number;
  proceedsUSD?: number;
  gainLossUSD?: number;
}
```

### CoinLedger CSV Row (Export Format)

```typescript
interface CoinLedgerRow {
  'Date (UTC)': string;
  'Platform': string;
  'Asset Sent': string;
  'Amount Sent': string;
  'Asset Received': string;
  'Amount Received': string;
  'Fee Currency': string;
  'Fee Amount': string;
  'Type': CoinLedgerType;
  'Description': string;
  'TxHash': string;
}
```

---

## 🧩 UI Components

### 1. Main Page Layout (`page.tsx`)

```
┌──────────────────────────────────────────────┐
│  🪙 [Network] Tax Bridge                     │
│  Subtitle / version                          │
├──────────────────────────────────────────────┤
│  📝 FETCH CONFIG PANEL (.glass)              │
│  ┌──────────────────────────────────────┐    │
│  │ Address Input (full width)           │    │
│  ├──────────┬──────────┬────────────────┤    │
│  │ Start    │ End Date │ Limit          │    │
│  ├──────────┴──────────┴────────────────┤    │
│  │ [x] Use AI Classification checkbox   │    │
│  │    subtitle: AI mode / Heuristic     │    │
│  ├──────────────────────────────────────┤    │
│  │ [Fetch & Preview]  [One-Click Sync]  │    │
│  ├──────────────────────────────────────┤    │
│  │ [📥 Download]  [📤 Upload]  [🗑 Clear]│   │
│  │ ✅ Cache status indicator            │    │
│  └──────────────────────────────────────┘    │
│                                              │
│  ⏳ Progress Bar (during fetch)              │
├──────────────────────────────────────────────┤
│  📊 SUMMARY PANEL (.glass)                   │
│  ┌────────┬────────┬────────┬────────┐       │
│  │ Total  │  Spam  │Missing │Visible │       │
│  │Fetched │Detected│Prices  │  Txns  │       │
│  └────────┴────────┴────────┴────────┘       │
├──────────────────────────────────────────────┤
│  Transaction Previews                        │
│  [Spam Toggle] [UTC|Local] [USD|SOL]         │
│  ┌───────────────────┬───────────────────┐   │
│  │   Preview A       │    Preview B      │   │
│  │   (Cards)         │    (CSV Table)    │   │
│  └───────────────────┴───────────────────┘   │
└──────────────────────────────────────────────┘
```

### State Variables

```typescript
// Form state
const [walletAddress, setWalletAddress] = useState('');
const [startDate, setStartDate] = useState('');
const [endDate, setEndDate] = useState('');
const [includeSpam, setIncludeSpam] = useState(false);
const [useAI, setUseAI] = useState(true);
const [limit, setLimit] = useState(10);

// Data state
const [loading, setLoading] = useState(false);
const [transactions, setTransactions] = useState<NormalizedTransaction[]>([]);
const [summary, setSummary] = useState<any>(null);
const [error, setError] = useState<string | null>(null);

// UI state
const [displayCurrency, setDisplayCurrency] = useState<'USD' | 'BTC'>('USD');
const [timezone, setTimezone] = useState<'UTC' | 'Local'>('UTC');
const [selectedTxIndex, setSelectedTxIndex] = useState<number | null>(null);
const [expandedTxIndex, setExpandedTxIndex] = useState<number | null>(null);
const [searchQuery, setSearchQuery] = useState('');

// Derived state
const filteredSpamCount = useMemo(
  () => transactions.filter(tx => tx.isSpam === true).length,
  [transactions]
);
const visibleTransactions = useMemo(
  () => includeSpam ? transactions : transactions.filter(tx => !tx.isSpam),
  [transactions, includeSpam]
);
```

---

### 2. Preview A — Interactive Transaction Cards

**Component Props:**
```typescript
interface PreviewAProps {
  transactions: NormalizedTransaction[];
  selectedTxIndex: number | null;
  setSelectedTxIndex: (index: number | null) => void;
  expandedTxIndex: number | null;
  setExpandedTxIndex: (index: number | null) => void;
  formatDate: (date: Date | string) => string;
  displayCurrency: 'USD' | 'BTC';  // Adapt to network
  searchQuery: string;
}
```

**Card Layout:**
```
┌──────────────────────────────────────────┐
│  [Token Image] [Type Badge] [ℹ️ Tooltip] │
│               Date / Time                 │
│  Sent: 0.5 BTC        Received: 10 ETH  │
│  Fee: 0.0001 BTC                         │
│  ────── Description ──────               │
│  TxHash: abc123... [📋 Copy] [🔗 Link]  │
│                              [▼ Expand]  │
└──────────────────────────────────────────┘
```

**Type Badge Styling:**
```tsx
// Determine display type and style
const displayType = tx.isSpam ? '🚫 Ignored' : tx.type;
const badgeClass = tx.isSpam ? 'bg-gray-500/20 text-gray-400 line-through' :
  tx.type === 'Trade' ? 'bg-blue-500/20 text-blue-400' :
  tx.type === 'Deposit' ? 'bg-green-500/20 text-green-400' :
  tx.type === 'Withdrawal' ? 'bg-red-500/20 text-red-400' :
  tx.type === 'Investment Loss' ? 'bg-orange-500/20 text-orange-400' :
  'bg-gray-500/20 text-gray-400';

<span className={`px-2 py-0.5 rounded text-xs font-semibold ${badgeClass}`}>
  {displayType}
</span>
```

**Tooltip Pattern (hover info icon):**
```tsx
<div className="group relative inline-flex">
  <button className="text-gray-500 hover:text-blue-400 cursor-help">
    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 ..." />
    </svg>
  </button>
  {/* Tooltip appears on hover */}
  <div className="invisible group-hover:visible opacity-0 group-hover:opacity-100
                  transition-opacity absolute left-0 top-6 z-50 w-80">
    <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 shadow-xl">
      <div className="flex items-start gap-2 mb-2">
        <span className="text-2xl">{typeIcon}</span>
        <div>
          <div className="font-semibold text-white">{typeInfo.title}</div>
          <div className="text-xs text-gray-400">
            Taxable: <span className="font-semibold text-green-400">{taxable}</span>
          </div>
        </div>
      </div>
      <p className="text-sm text-gray-300">{typeInfo.description}</p>
      <p className="text-xs text-gray-500 italic">💡 {typeInfo.learnMore}</p>
    </div>
    {/* Arrow */}
    <div className="absolute left-4 -top-2 w-0 h-0
      border-l-8 border-r-8 border-b-8
      border-transparent border-b-gray-700" />
  </div>
</div>
```

---

### 3. Preview B — CSV Table View

**Table Structure:**
```
┌────────────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────┬────────┐
│ Date (UTC) │ Plat │A.Sent│Amt   │A.Rcv │Amt   │ Fee  │ Fee  │ Type   │ TxHash │
│            │ form │      │Sent  │      │Rcvd  │ Curr │ Amt  │        │        │
├────────────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┼────────┼────────┤
│ 2025-12-25 │ BTC  │ BTC  │ 0.5  │ -    │ -    │ BTC  │0.0001│Withdraw│ abc... │
│ 2025-12-20 │ BTC  │ -    │ -    │ BTC  │ 1.0  │ BTC  │0.0001│ 🚫 Ign │ def... │
└────────────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┴────────┴────────┘
```

**Table Styling:**
```tsx
<div className="overflow-x-auto">
  <table className="w-full text-sm">
    <thead>
      <tr className="border-b border-gray-700/50 text-gray-400 text-xs uppercase">
        <th className="py-3 px-2 text-left">Date (UTC)</th>
        {/* ... */}
      </tr>
    </thead>
    <tbody>
      {transactions.map(tx => (
        <tr className="border-b border-gray-800/50 hover:bg-white/5 transition-colors">
          {/* ... */}
        </tr>
      ))}
    </tbody>
  </table>
</div>
```

---

### 4. Global Controls Bar

Located in the preview section header, next to UTC/SOL toggles:

```tsx
{/* Spam Filter Toggle — only shows when spam exists */}
{filteredSpamCount > 0 && (
  <div className="flex items-center gap-2 px-3 py-1.5
                  bg-purple-500/10 border border-purple-500/30 rounded-lg">
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" checked={includeSpam}
             onChange={(e) => setIncludeSpam(e.target.checked)}
             className="w-4 h-4 accent-purple-500" />
      <span className="text-sm font-medium text-purple-300">
        {includeSpam ? '🗑️ Spam Included' : '✨ Spam Excluded'}
      </span>
    </label>
    {!includeSpam && (
      <span className="text-xs bg-red-500/20 text-red-300 px-2 py-0.5 rounded-full">
        {filteredSpamCount} ignored
      </span>
    )}
  </div>
)}

{/* Toggle Button Pattern (UTC/Local, USD/BTC) */}
<div className="flex bg-gray-800/50 rounded-lg p-1">
  <button onClick={() => setOption('A')}
    className={`px-4 py-2 rounded-md font-semibold transition-all ${
      option === 'A'
        ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white'
        : 'text-gray-400 hover:text-white'
    }`}>
    Option A
  </button>
  <button onClick={() => setOption('B')} /* same pattern */ />
</div>
```

---

## 💾 Data Download / Upload Functions

### Download Handler

```typescript
const handleDownloadData = () => {
  if (transactions.length === 0) {
    alert('No transactions to download.');
    return;
  }

  const data = {
    version: '1.0',
    walletAddress,
    fetchedAt: new Date().toISOString(),
    filters: { startDate, endDate, limit, useAI, includeSpam },
    transactions,     // ALL transactions (including spam)
    summary,
    stats: {
      totalTransactions: transactions.length,
      tradeCount: transactions.filter(t => t.type === 'Trade').length,
      // ... add network-specific stats
    },
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${network}-data-${walletAddress.substring(0, 8)}-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);
};
```

### Upload Handler

```typescript
const handleUploadData = (event: React.ChangeEvent<HTMLInputElement>) => {
  const file = event.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    try {
      const data = JSON.parse(e.target?.result as string);

      // Re-evaluate spam for unclassified transactions
      const reEvaluated = data.transactions.map((tx: NormalizedTransaction) => {
        if (tx.isSpam === true || tx.isSpam === false) return tx;

        const spam = isLikelySpam(tx);  // Network-specific heuristic
        return {
          ...tx,
          isSpam: spam,
          spamConfidence: spam ? 0.7 : 0,
          spamReasons: spam ? ['Heuristic: uploaded data re-evaluation'] : [],
        };
      });

      setTransactions(reEvaluated);
      setSummary(data.summary || null);
      setCachedData(data);

      const spamCount = reEvaluated.filter((tx: NormalizedTransaction) => tx.isSpam === true).length;
      alert(`Loaded ${reEvaluated.length} transactions (${spamCount} spam detected)`);
    } catch {
      alert('Invalid JSON file');
    }
  };
  reader.readAsText(file);
  event.target.value = '';  // Reset input
};
```

### Upload Button (Disabled During Fetch)

```tsx
<label className={`flex-1 ${loading ? 'pointer-events-none opacity-50' : 'cursor-pointer'}`}>
  <div className={`px-4 py-2 ${loading ? 'bg-gray-700' : 'bg-orange-600 hover:bg-orange-700'}
                   rounded-lg font-medium text-sm transition-all text-center`}>
    📤 Upload Cached Data
  </div>
  <input type="file" accept=".json" onChange={handleUploadData}
         className="hidden" disabled={loading} />
</label>
```

---

## 🔧 Transaction Type Education System

### Architecture

```typescript
interface TransactionTypeInfo {
  type: string;
  icon: string;
  title: string;
  description: string;
  taxable: 'Yes' | 'No' | 'Depends';
  learnMore: string;
}

const TRANSACTION_TYPE_INFO: Record<string, TransactionTypeInfo> = {
  'Trade': { type: 'Trade', icon: '🔄', title: 'Trade (Swap)', ... },
  'Deposit': { type: 'Deposit', icon: '📥', title: 'Deposit', ... },
  'Ignored': { type: 'Ignored', icon: '🚫', title: 'Ignored (Spam / Dust)', ... },
  // ... add all types
};

function getTransactionTypeInfo(type: string, description?: string): TransactionTypeInfo {
  if (type.toUpperCase().includes('SPAM') || type === 'Ignored') {
    return TRANSACTION_TYPE_INFO['Ignored'];
  }
  // Add network-specific overrides based on description
  return TRANSACTION_TYPE_INFO[type] || TRANSACTION_TYPE_INFO['UNKNOWN'];
}
```

---

## 🔌 Bitcoin Network Adaptation Notes

When adapting this blueprint for Bitcoin:

| Solana Concept | Bitcoin Equivalent |
|----------------|-------------------|
| SOL | BTC / sats |
| Token accounts (rent) | UTXOs |
| Rent recovery | UTXO consolidation |
| SPL tokens | Ordinals / Runes / BRC-20 |
| Raydium/Jupiter | Magic Eden / Unisat |
| Solscan | Mempool.space / Blockchain.com |
| Helius RPC API | Mempool API / BlockCypher / OKLink |
| Native SOL transfers | BTC UTXO transfers |
| Token metadata (DAS) | Ordinals metadata API |

### Bitcoin-Specific Transaction Types to Add:
- **Ordinals Transfer** — NFT-like transfers on Bitcoin
- **Rune Transfer** — Fungible token transfers
- **BRC-20 Transfer** — Token standard transfers
- **UTXO Consolidation** — Merging inputs (not taxable)
- **Inscription Mint** — Creating ordinals (taxable as Trade)

---

## 🤖 Transition Prompt

Use this prompt to initialize the Bitcoin Tax Bridge project:

```
Build a Bitcoin Transaction Tax Bridge web application using Next.js 14 (App Router),
TypeScript, and TailwindCSS with a dark glassmorphism theme.

DESIGN REQUIREMENTS:
- Dark theme with near-black background (#0a0a0a)
- Glassmorphism cards (rgba(255,255,255,0.05) + backdrop-filter blur)
- Purple (#8b5cf6) primary accent, green (#10b981) secondary
- Inter font from Google Fonts
- Custom purple scrollbars
- Shimmer loading animation

CORE FEATURES:
1. Wallet address input + date range + transaction limit
2. API integration to fetch Bitcoin transactions (UTXO-based)
3. Transaction classification into CoinLedger types:
   Trade, Deposit, Withdrawal, Income, Staking, Ignored (spam)
4. Dual preview system:
   - Preview A: Interactive expandable cards with token images,
     type badges (colored), info tooltips (hover for tax education),
     copy-to-clipboard TxHash, blockchain explorer links
   - Preview B: CSV table matching CoinLedger import format
5. Spam detection with Ignored label (gray strikethrough badge)
6. Spam filter toggle in preview header (purple accent, shows count)
7. Download ALL transactions as JSON (including spam)
8. Upload JSON with automatic spam re-evaluation
9. Upload button disabled during active fetch
10. Global toggles: UTC/Local timezone, USD/BTC currency display
11. Progress bar during fetch with status text
12. Summary panel: total fetched, spam detected, missing prices, visible

UI PATTERNS:
- Type badges: colored rounded pills (blue=Trade, green=Deposit,
  red=Withdrawal, gray+strikethrough=Ignored)
- Tooltips: CSS-only hover (group/group-hover), no JS tooltip library
- Toggle buttons: bg-gray-800/50 container with gradient active state
- Buttons: gradient backgrounds with hover:scale-105 active:scale-95
- Glass panels: .glass class with rounded-2xl

TYPE SYSTEM:
Use CoinLedgerType union type with:
Trade | Deposit | Withdrawal | Income | Staking | Airdrop |
Gift Received | Gift Sent | Investment Loss | Theft Loss |
Casualty Loss | Ignored

DATA MODEL:
NormalizedTransaction interface with: id, timestamp, txHash, platform,
assetSent/Received, amountSent/Received, feeCurrency/Amount, type,
description, priceUSD, isSpam, spamConfidence, spamReasons,
costBasisUSD, proceedsUSD, gainLossUSD

Adapt all Solana-specific references to Bitcoin equivalents:
SOL→BTC, SPL tokens→Ordinals/Runes/BRC-20, Solscan→Mempool.space,
Helius→Mempool API
```

---

**Last Updated:** February 18, 2026  
**Source Project:** [coinledger-parser-solana](.)  
**Target Project:** coinledger-parser-bitcoin
