import React, { useState, useEffect, useCallback, useMemo } from 'react';
import axios from 'axios';
import { Upload, RefreshCw, FileText, Activity, Download, ChevronDown, ChevronRight, UploadCloud, FileJson, Search } from 'lucide-react';
import CorrectionReport from './components/CorrectionReport';
import TransactionList from './components/TransactionList';
import ReviewPanelA from './components/ReviewPanelA';
import ReviewPanelB from './components/ReviewPanelB';

function App() {
  // Theme
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    return saved === 'dark';
  });

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [darkMode]);

  // Form States
  const [file, setFile] = useState<File | null>(null);
  const [wallet, setWallet] = useState('');
  const [fromDate, setFromDate] = useState('2025-01-01');
  const [toDate, setToDate] = useState(new Date().toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);

  // Data States
  const [sourceA, setSourceA] = useState<any[]>([]);
  const [sourceB, setSourceB] = useState<any[]>([]);
  const [sourceC, setSourceC] = useState<any[]>([]);
  const [results, setResults] = useState<any>(null);

  // Status States
  const [uploadStatus, setUploadStatus] = useState('');
  const [fetchStatus, setFetchStatus] = useState('');
  const [analyzeStatus, setAnalyzeStatus] = useState('');

  // Feature States
  const [showUSD, setShowUSD] = useState(false);
  const [btcPrice, setBtcPrice] = useState<number | null>(null);
  const [progress, setProgress] = useState(0);

  // UI States
  const [exportOption, setExportOption] = useState<'report' | 'sheets' | 'blockchain-only'>('report');
  const [sheetUrl, setSheetUrl] = useState('https://docs.google.com/spreadsheets/d/1caXWkAvAqfKRmmc3suVVfP2NH8sAW5gKx2AuqkZO14E/edit?usp=sharing');
  const [exportStatus, setExportStatus] = useState('');
  const [selectedTxId, setSelectedTxId] = useState<string | null>(null);
  const [sourceACollapsed, setSourceACollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [analysisSummary, setAnalysisSummary] = useState<any>(null);
  const [runeOverrides, setRuneOverrides] = useState<Record<string, any>>({});

  // Callback when Panel A fetches rune info — propagates to Panel B
  const handleRuneFetched = useCallback((txId: string, runeData: any) => {
    setRuneOverrides(prev => ({ ...prev, [txId]: runeData }));
  }, []);

  // Auto-collapse Source A when empty
  useEffect(() => {
    if (sourceA.length === 0) setSourceACollapsed(true);
    else setSourceACollapsed(false);
  }, [sourceA]);

  // Fetch BTC price
  useEffect(() => {
    const fetchPrice = async () => {
      try {
        const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd');
        const data = await response.json();
        if (data.bitcoin?.usd) {
          setBtcPrice(data.bitcoin.usd);
        }
      } catch (err) {
        console.error('Failed to fetch BTC price:', err);
      }
    };
    fetchPrice();
  }, []);

  // Compute missing tx IDs (present in B but not in C, or vice versa)
  const missingInC = useMemo(() => {
    if (sourceC.length === 0 || sourceB.length === 0) return new Set<string>();
    const cIds = new Set(sourceC.map(tx => tx.tx_id));
    return new Set(sourceB.filter(tx => tx.tx_id && !cIds.has(tx.tx_id)).map(tx => tx.tx_id));
  }, [sourceB, sourceC]);

  // ====== Handlers ======

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setSourceA([]);
      setResults(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      setLoading(true);
      const res = await axios.post('http://localhost:8000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (res.data.data && Array.isArray(res.data.data)) {
        setSourceA(res.data.data);
        setUploadStatus(`✓ Uploaded ${res.data.count} transactions`);
      } else {
        setUploadStatus('Upload succeeded but data format is invalid');
      }
    } catch (error: any) {
      setUploadStatus(`✗ Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchBlockchain = async () => {
    const addresses = wallet.split(/[,\n]+/).map(addr => addr.trim()).filter(addr => addr.length > 0);
    if (addresses.length === 0) {
      alert("Please enter at least one wallet address");
      return;
    }
    try {
      setLoading(true);
      setFetchStatus('Initializing connection...');
      setProgress(0);
      let allTransactions: any[] = [];
      const walletEmojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];

      for (let i = 0; i < addresses.length; i++) {
        const address = addresses[i];
        const walletId = walletEmojis[i] || `${i + 1}️⃣`;
        setFetchStatus(`Fetching wallet ${i + 1}/${addresses.length}: ${address.slice(0, 8)}...`);
        const res = await axios.post('http://localhost:8000/api/fetch-blockchain', {
          wallet_address: address, chain: 'bitcoin', from_date: fromDate, to_date: toDate,
          append: i > 0  // First wallet replaces, subsequent wallets append
        });
        const txsWithWallet = res.data.data.map((tx: any) => {
          const date = new Date(tx.timestamp);
          return { ...tx, Wallet: walletId, Date: date.toISOString().split('T')[0], Time: date.toTimeString().split(' ')[0], WalletAddress: address };
        });
        allTransactions = [...allTransactions, ...txsWithWallet];
        setProgress(Math.round(((i + 1) / addresses.length) * 100));
      }

      allTransactions.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      setSourceB(allTransactions);
      setFetchStatus(`✓ Fetched ${allTransactions.length} transactions from ${addresses.length} address(es)`);
    } catch (error) {
      console.error(error);
      setFetchStatus('✗ Fetch failed. Check backend logs.');
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  const handleAnalyze = async () => {
    try {
      setLoading(true);
      const res = await axios.post('http://localhost:8000/api/analyze');
      setResults(res.data);
      if (res.data.enriched_source_a) setSourceA(res.data.enriched_source_a);
      if (res.data.enriched_source_b) setSourceB(res.data.enriched_source_b);
    } catch (error: any) {
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeBlockchainOnly = async () => {
    try {
      setLoading(true);
      setAnalyzeStatus('Analyzing blockchain transactions...');
      const walletAddresses = wallet.split(/[,\n]+/).map(addr => addr.trim()).filter(addr => addr.length > 0);
      const res = await axios.post('http://localhost:8000/api/analyze-blockchain-only', {
        wallet_addresses: walletAddresses
      });
      setSourceC(res.data.source_c || []);
      setAnalysisSummary(res.data.summary || null);
      setAnalyzeStatus(`✓ Analysis complete: ${res.data.summary?.patterns_detected || 0} patterns detected`);
    } catch (error: any) {
      setAnalyzeStatus(`✗ Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExportToSheets = async () => {
    if (!sheetUrl) { alert('Please enter a Google Sheets URL'); return; }
    try {
      setLoading(true);
      setExportStatus('Analyzing and exporting...');
      const res = await axios.post('http://localhost:8000/api/export-to-sheets', {
        sheet_url: sheetUrl,
        wallet_addresses: wallet.split(/[,\n]+/).map(addr => addr.trim()).filter(addr => addr.length > 0)
      });
      setExportStatus(`✓ Exported ${res.data.row_count} transactions. ${res.data.review_count} for review.`);
    } catch (error: any) {
      setExportStatus(`✗ Export failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // JSON Export/Upload
  const handleExportJSON = async () => {
    try {
      const res = await axios.post('http://localhost:8000/api/export-blockchain-json');
      const txCount = res.data.transaction_count || sourceB.length;
      const dateStr = new Date().toISOString().split('T')[0];
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Bitcoin_blockchain_${txCount}_${dateStr}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(`Export failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleUploadJSON = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      try {
        const data = JSON.parse(ev.target?.result as string);
        const transactions = data.transactions || data;
        const res = await axios.post('http://localhost:8000/api/upload-blockchain-json', { transactions });
        // Restore frontend state with same fields as fetch handler
        const walletEmojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];
        const txsWithDate = transactions.map((tx: any) => {
          const date = new Date(tx.timestamp);
          return {
            ...tx,
            Wallet: tx.Wallet || walletEmojis[0],
            WalletAddress: tx.WalletAddress || '',
            Date: date.toISOString().split('T')[0],
            Time: date.toTimeString().split(' ')[0],
          };
        });
        setSourceB(txsWithDate);
        setFetchStatus(`✓ Restored ${res.data.count} transactions from JSON`);
      } catch (err: any) {
        alert(`Upload failed: ${err.message}`);
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  const handleExportCSV = () => {
    if (!sourceB || sourceB.length === 0) return;
    const headers = Object.keys(sourceB[0]);
    const csvRows = [headers.join(',')];
    sourceB.forEach((tx) => {
      const escape = (val: any) => {
        if (val === null || val === undefined) return '';
        const str = String(val);
        if (str.includes(',') || str.includes('\n') || str.includes('"')) return `"${str.replace(/"/g, '""')}"`;
        return str;
      };
      const row = headers.map(col => {
        let val = tx[col];
        if (col === 'Wallet' && typeof val === 'string') {
          const match = val.match(/(\d+)/);
          if (match) val = match[1];
        }
        if (typeof val === 'object') return escape(JSON.stringify(val));
        return escape(val);
      });
      csvRows.push(row.join(','));
    });
    const blob = new Blob([csvRows.join('\n')], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `blockchain_export_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleRowClick = useCallback((txId: string) => {
    setSelectedTxId(prev => prev === txId ? null : txId);
  }, []);

  // Determine grid layout based on available sources
  const previewGridClass = useMemo(() => {
    const hasA = sourceA.length > 0 && !sourceACollapsed;
    const hasC = sourceC.length > 0;
    if (hasA && hasC) return 'grid-cols-1 xl:grid-cols-3';
    if (hasA || hasC) return 'grid-cols-1 lg:grid-cols-2';
    return 'grid-cols-1';
  }, [sourceA, sourceC, sourceACollapsed]);

  return (
    <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-[#0a0a0a] text-gray-100' : 'bg-gray-100 text-gray-900'}`}>
      <div className="max-w-[1800px] mx-auto p-6">

        {/* Header with Theme Toggle */}
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <FileText className={`w-8 h-8 ${darkMode ? 'text-purple-400' : 'text-blue-600'}`} />
              BitMatch Reconciliation
            </h1>
            <p className={`mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Dual-Ledger Audit & Reconciliation Agent</p>
          </div>
          <div className="flex items-center gap-4">

            {/* Theme Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`theme-toggle ${darkMode ? 'theme-toggle-dark' : 'theme-toggle-light'}`}
              title={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              <div className={`theme-toggle-knob ${darkMode ? 'theme-toggle-knob-dark' : 'theme-toggle-knob-light'}`}>
                {darkMode ? '🌙' : '☀️'}
              </div>
            </button>
          </div>
        </header>

        {/* ====== Workflow Steps (3 Cards) ====== */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">

          {/* Step 1: Upload CEX Export */}
          <div className={`glass p-6 ${darkMode ? 'border-t-2 border-blue-500/50' : 'border-t-4 border-blue-500'}`}>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${darkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-100 text-blue-700'}`}>1</span>
              Upload CEX Export
              <span className="text-xs text-gray-400 font-normal">(Optional)</span>
            </h2>
            <div className="space-y-3">
              <input
                type="file"
                onChange={handleFileChange}
                className={`block w-full text-sm ${darkMode ? 'text-gray-400 file:bg-gray-700 file:text-gray-200' : 'text-gray-500 file:bg-blue-50 file:text-blue-700'} file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold hover:file:opacity-80`}
              />
              <button
                onClick={handleUpload}
                disabled={!file || loading}
                className="w-full px-4 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-40 flex items-center justify-center gap-2 font-medium transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <Upload className="w-4 h-4" /> Upload & Preview
              </button>
              {uploadStatus && <p className={`text-sm text-center ${uploadStatus.includes('✗') ? 'text-red-400' : 'text-green-400'}`}>{uploadStatus}</p>}
            </div>
          </div>

          {/* Step 2: Fetch Blockchain Data */}
          <div className={`glass p-6 ${darkMode ? 'border-t-2 border-indigo-500/50' : 'border-t-4 border-indigo-500'}`}>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${darkMode ? 'bg-indigo-500/20 text-indigo-400' : 'bg-indigo-100 text-indigo-700'}`}>2</span>
              Fetch Blockchain Data
            </h2>
            <div className="space-y-3">
              <div>
                <label className={`block text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Bitcoin Wallet Address(es)
                  <span className="text-gray-500 ml-1">(comma or line break)</span>
                </label>
                <textarea
                  placeholder="bc1p... or bc1q... or 3..."
                  value={wallet}
                  onChange={(e) => setWallet(e.target.value)}
                  rows={3}
                  className={`w-full px-3 py-2 rounded-lg outline-none resize-none font-mono text-sm transition-colors
                    ${darkMode
                      ? 'bg-gray-800/50 border border-gray-700 text-gray-200 focus:ring-2 focus:ring-indigo-500/50 placeholder-gray-600'
                      : 'border border-gray-300 text-gray-900 focus:ring-2 focus:ring-indigo-500 placeholder-gray-400'}`}
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={`block text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>From Date</label>
                  <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
                    className={`w-full px-3 py-2 rounded-lg outline-none text-sm ${darkMode ? 'bg-gray-800/50 border border-gray-700 text-gray-200' : 'border border-gray-300'}`} />
                </div>
                <div>
                  <label className={`block text-xs mb-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>To Date</label>
                  <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
                    className={`w-full px-3 py-2 rounded-lg outline-none text-sm ${darkMode ? 'bg-gray-800/50 border border-gray-700 text-gray-200' : 'border border-gray-300'}`} />
                </div>
              </div>

              {/* Fetch Button */}
              <button onClick={handleFetchBlockchain} disabled={loading}
                className="w-full px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-40 flex items-center justify-center gap-2 font-medium transition-all hover:scale-[1.02] active:scale-[0.98]">
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                {loading ? 'Fetching...' : 'Fetch & Preview'}
              </button>

              {/* Progress Bar */}
              {loading && progress > 0 && (
                <div className="w-full bg-gray-700/30 rounded-full h-2 overflow-hidden">
                  <div className="bg-indigo-500 h-2 rounded-full transition-all duration-500" style={{ width: `${progress}%` }}></div>
                </div>
              )}

              {/* JSON Export/Upload/CSV Buttons */}
              {sourceB.length > 0 && (
                <div className="flex gap-2">
                  <button onClick={handleExportJSON}
                    className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02]
                      ${darkMode ? 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 border border-amber-500/30' : 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'}`}>
                    <FileJson className="w-3.5 h-3.5" /> JSON
                  </button>
                  <label className={`flex-1 cursor-pointer px-3 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02]
                    ${darkMode ? 'bg-orange-500/20 text-orange-300 hover:bg-orange-500/30 border border-orange-500/30' : 'bg-orange-50 text-orange-700 hover:bg-orange-100 border border-orange-200'}`}>
                    <UploadCloud className="w-3.5 h-3.5" /> Upload
                    <input type="file" accept=".json" onChange={handleUploadJSON} className="hidden" />
                  </label>
                  <button onClick={handleExportCSV}
                    className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-1.5 transition-all hover:scale-[1.02]
                      ${darkMode ? 'bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30' : 'bg-green-50 text-green-700 hover:bg-green-100 border border-green-200'}`}>
                    <Download className="w-3.5 h-3.5" /> CSV
                  </button>
                </div>
              )}

              {/* Upload JSON when no data yet */}
              {sourceB.length === 0 && (
                <label className={`w-full cursor-pointer px-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-all hover:scale-[1.02]
                  ${darkMode ? 'bg-orange-500/20 text-orange-300 hover:bg-orange-500/30 border border-orange-500/30' : 'bg-orange-50 text-orange-700 hover:bg-orange-100 border border-orange-200'}`}>
                  <UploadCloud className="w-4 h-4" /> Upload Cached JSON
                  <input type="file" accept=".json" onChange={handleUploadJSON} className="hidden" />
                </label>
              )}

              {fetchStatus && (
                <p className={`text-sm text-center ${fetchStatus.includes('✗') ? 'text-red-400' : 'text-green-400'}`}>{fetchStatus}</p>
              )}
            </div>
          </div>

          {/* Step 3: Analyze & Export */}
          <div className={`glass p-6 ${darkMode ? 'border-t-2 border-purple-500/50' : 'border-t-4 border-purple-500'}`}>
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${darkMode ? 'bg-purple-500/20 text-purple-400' : 'bg-purple-100 text-purple-700'}`}>3</span>
              Analyze & Export
            </h2>
            <div className="space-y-3">

              {/* Option A: CEX vs Blockchain */}
              <div className={`rounded-lg p-3 border transition-colors ${exportOption === 'report' ? (darkMode ? 'border-purple-500/50 bg-purple-500/10' : 'border-purple-300 bg-purple-50') : (darkMode ? 'border-gray-700' : 'border-gray-200')}`}>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="export-option" checked={exportOption === 'report'} onChange={() => setExportOption('report')} className="accent-purple-500" />
                  <span className="font-semibold text-sm">Option A: CEX vs Blockchain Report</span>
                </label>
                <p className={`text-xs ml-6 mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Compare CEX data vs Blockchain (Step 1 + 2)</p>
                {exportOption === 'report' && (
                  <div className="ml-6 mt-2">
                    <button onClick={handleAnalyze}
                      disabled={sourceA.length === 0 || sourceB.length === 0 || loading}
                      className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-40 flex items-center gap-2 text-sm font-medium transition-all">
                      <Activity className="w-4 h-4" /> Run Analysis
                    </button>
                    {sourceA.length === 0 && <p className="text-xs text-amber-400 mt-1">⚠️ Requires CEX data from Step 1</p>}
                  </div>
                )}
              </div>

              {/* Option B: Google Sheets */}
              <div className={`rounded-lg p-3 border transition-colors ${exportOption === 'sheets' ? (darkMode ? 'border-green-500/50 bg-green-500/10' : 'border-green-300 bg-green-50') : (darkMode ? 'border-gray-700' : 'border-gray-200')}`}>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="export-option" checked={exportOption === 'sheets'} onChange={() => setExportOption('sheets')} className="accent-green-500" />
                  <span className="font-semibold text-sm">Option B: Universal Import Template</span>
                </label>
                <p className={`text-xs ml-6 mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Export to Google Sheets (Step 2 only)</p>
                {exportOption === 'sheets' && (
                  <div className="ml-6 mt-2 space-y-2">
                    <input type="text" placeholder="Google Sheets URL" value={sheetUrl} onChange={(e) => setSheetUrl(e.target.value)}
                      className={`w-full px-3 py-2 rounded-lg outline-none text-sm ${darkMode ? 'bg-gray-800/50 border border-gray-700 text-gray-200' : 'border border-gray-300'}`} />
                    <button onClick={handleExportToSheets}
                      disabled={sourceB.length === 0 || loading || !sheetUrl}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-40 flex items-center gap-2 text-sm font-medium transition-all">
                      <Download className="w-4 h-4" /> Export to Sheets
                    </button>
                  </div>
                )}
                {exportStatus && exportOption === 'sheets' && (
                  <p className={`text-sm ml-6 mt-1 ${exportStatus.includes('✓') ? 'text-green-400' : 'text-red-400'}`}>{exportStatus}</p>
                )}
              </div>

              {/* Option C: Blockchain-Only Analysis */}
              <div className={`rounded-lg p-3 border transition-colors ${exportOption === 'blockchain-only' ? (darkMode ? 'border-cyan-500/50 bg-cyan-500/10' : 'border-cyan-300 bg-cyan-50') : (darkMode ? 'border-gray-700' : 'border-gray-200')}`}>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="radio" name="export-option" checked={exportOption === 'blockchain-only'} onChange={() => setExportOption('blockchain-only')} className="accent-cyan-500" />
                  <span className="font-semibold text-sm">Option C: Blockchain-Only Analysis</span>
                </label>
                <p className={`text-xs ml-6 mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Analyze Bitcoin transactions without CEX import (Step 2 only)</p>
                {exportOption === 'blockchain-only' && (
                  <div className="ml-6 mt-2">
                    <button onClick={handleAnalyzeBlockchainOnly}
                      disabled={sourceB.length === 0 || loading}
                      className="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 disabled:opacity-40 flex items-center gap-2 text-sm font-medium transition-all">
                      <Activity className="w-4 h-4" /> Analyze Blockchain
                    </button>
                    {sourceB.length === 0 && <p className="text-xs text-amber-400 mt-1">⚠️ Fetch blockchain data first (Step 2)</p>}
                  </div>
                )}
                {analyzeStatus && exportOption === 'blockchain-only' && (
                  <p className={`text-sm ml-6 mt-1 ${analyzeStatus.includes('✗') ? 'text-red-400' : 'text-green-400'}`}>{analyzeStatus}</p>
                )}
              </div>

            </div>
          </div>
        </div>

        {/* ====== Data Preview Area ====== */}
        {(sourceA.length > 0 || sourceB.length > 0) && !results && (
          <div className="mb-8 animate-fade-in">

            {/* Pattern Summary (shows after Option C analysis) */}
            {analysisSummary && sourceC.length > 0 && (
              <div className={`glass p-5 mb-6 ${darkMode ? 'bg-gray-900/50' : 'bg-white/90'}`}>
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-bold flex items-center gap-2">
                    📊 Analysis Summary
                  </h3>
                  <button
                    onClick={() => { setSourceC([]); setAnalysisSummary(null); setSearchQuery(''); }}
                    className={`text-sm underline ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    Back to Raw Preview
                  </button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-400">{analysisSummary.total_transactions || 0}</div>
                    <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Total Fetched</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-400">{analysisSummary.patterns_detected || 0}</div>
                    <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Patterns Detected</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-400">
                      {sourceC.filter(tx => tx.pattern && (tx.pattern === 'MINT_BUY' || tx.pattern === 'BULK_MINT' || tx.pattern === 'RUNE_RECEIVE') && !(tx.metadata?.rune_name)).length}
                    </div>
                    <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Needs Review</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-cyan-400">
                      {sourceC.filter(tx => tx.coinledger_type && tx.coinledger_type !== 'Ignored').length}
                    </div>
                    <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>Import Ready</div>
                  </div>
                </div>
                {/* Pattern breakdown */}
                {analysisSummary.by_pattern && Object.keys(analysisSummary.by_pattern).length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(analysisSummary.by_pattern).map(([pattern, count]: [string, any]) => {
                      const emojiMap: Record<string, string> = {
                        'MINT_BUY': '🎨', 'BULK_MINT': '🎨✨', 'GAS_FEE': '⛽', 'SALE': '💰',
                        'SELF_TRANSFER': '🔄', 'FIAT_ONRAMP': '💵', 'RUNE_RECEIVE': '🔮',
                        'MAGIC_EDEN_BUY': '🪄', 'MAGIC_EDEN_BUY_ISOLATED': '🪄', 'MAGIC_EDEN_SALE': '🪄💰', 'NFT_TRADE': '🏪',
                      };
                      return (
                        <span key={pattern} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold
                          ${darkMode ? 'bg-gray-800 border border-gray-700 text-gray-300' : 'bg-gray-100 border border-gray-200 text-gray-700'}`}>
                          <span>{emojiMap[pattern] || '🏷️'}</span>
                          <span>{pattern.replace(/_/g, ' ')}</span>
                          <span className="ml-1 px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-400 text-xs font-bold">{count}</span>
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* USD Toggle + Search Bar */}
            <div className="flex items-center justify-between mb-3 gap-4">
              {/* Search Bar */}
              <div className="flex-1 max-w-lg relative">
                <Search className={`absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`} />
                <input
                  type="text"
                  placeholder="Search by transaction hash, asset, pattern..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className={`w-full pl-10 pr-4 py-2 rounded-lg outline-none text-sm transition-colors
                    ${darkMode
                      ? 'bg-gray-800/50 border border-gray-700 text-gray-200 focus:ring-2 focus:ring-purple-500/50 placeholder-gray-600'
                      : 'bg-white border border-gray-300 text-gray-900 focus:ring-2 focus:ring-purple-500 placeholder-gray-400'}`}
                />
              </div>
              {/* USD Toggle */}
              <label className="inline-flex items-center cursor-pointer shrink-0">
                <span className={`mr-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Display USD Value</span>
                <input type="checkbox" checked={showUSD} onChange={() => setShowUSD(!showUSD)} className="sr-only peer" />
                <div className="relative w-10 h-5 bg-gray-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600 dark:bg-gray-600"></div>
              </label>
            </div>

            {/* ====== Review Panel A/B (after Option C analysis) ====== */}
            {sourceC.length > 0 ? (
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <ReviewPanelA
                  transactions={sourceC}
                  searchQuery={searchQuery}
                  selectedTxId={selectedTxId}
                  onRowClick={handleRowClick}
                  onRuneFetched={handleRuneFetched}
                  showUSD={showUSD}
                  btcPrice={btcPrice}
                />
                <ReviewPanelB
                  transactions={sourceC}
                  searchQuery={searchQuery}
                  selectedTxId={selectedTxId}
                  onRowClick={handleRowClick}
                  runeOverrides={runeOverrides}
                  showUSD={showUSD}
                  btcPrice={btcPrice}
                />
              </div>
            ) : (
              /* ====== Raw Source Preview (before analysis) ====== */
              <>
                {/* Source A Collapse Toggle */}
                {sourceA.length > 0 && (
                  <button
                    onClick={() => setSourceACollapsed(!sourceACollapsed)}
                    className={`mb-3 flex items-center gap-1 text-sm font-medium ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'} transition-colors`}
                  >
                    {sourceACollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    {sourceACollapsed ? 'Show Source A (CEX Export)' : 'Hide Source A (CEX Export)'}
                  </button>
                )}

                <div className={`grid ${previewGridClass} gap-6`}>
                  {/* Source A */}
                  {sourceA.length > 0 && !sourceACollapsed && (
                    <TransactionList
                      title="Source A: CEX Export"
                      transactions={sourceA}
                      colorClass={darkMode ? 'text-blue-400' : 'text-blue-700'}
                      showUSD={showUSD}
                      btcPrice={btcPrice}
                      selectedTxId={selectedTxId}
                      onRowClick={handleRowClick}
                    />
                  )}

                  {/* Source B */}
                  <TransactionList
                    title="Source B: Blockchain"
                    transactions={sourceB}
                    colorClass={darkMode ? 'text-indigo-400' : 'text-indigo-700'}
                    showUSD={showUSD}
                    btcPrice={btcPrice}
                    selectedTxId={selectedTxId}
                    onRowClick={handleRowClick}
                    missingTxIds={missingInC}
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* ====== Results Area (Option A Report) ====== */}
        {results && (
          <div className="animate-fade-in">
            <div className={`glass p-4 mb-4`}>
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold">Tax Correction Report</h2>
                <button onClick={() => setResults(null)}
                  className={`text-sm underline ${darkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
                  Back to Preview
                </button>
              </div>
            </div>
            <CorrectionReport
              suggestions={results.correction_suggestions || []}
              summary={results.summary || { total_issues: 0, by_severity: { HIGH: 0, MEDIUM: 0, LOW: 0 }, by_pattern: {} }}
              showUSD={showUSD}
              btcPrice={btcPrice}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
