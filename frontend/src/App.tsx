import React, { useState } from 'react';
import axios from 'axios';
import { Upload, RefreshCw, FileText, Activity, Download } from 'lucide-react';
import CorrectionReport from './components/CorrectionReport';
import TransactionList from './components/TransactionList';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [wallet, setWallet] = useState('');
  const [fromDate, setFromDate] = useState('2025-01-01');
  const [toDate, setToDate] = useState(new Date().toISOString().split('T')[0]); // Today
  const [loading, setLoading] = useState(false);

  // Data States
  const [sourceA, setSourceA] = useState<any[]>([]);
  const [sourceB, setSourceB] = useState<any[]>([]);
  const [results, setResults] = useState<any>(null);

  const [uploadStatus, setUploadStatus] = useState('');
  const [fetchStatus, setFetchStatus] = useState('');

  // Feature States
  const [showUSD, setShowUSD] = useState(false);
  const [btcPrice, setBtcPrice] = useState<number | null>(null);

  React.useEffect(() => {
    // Fetch current BTC price
    const fetchPrice = async () => {
      try {
        const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd');
        const data = await response.json();
        if (data.bitcoin && data.bitcoin.usd) {
          setBtcPrice(data.bitcoin.usd);
          console.log('Fetched BTC Price:', data.bitcoin.usd);
        }
      } catch (err) {
        console.error('Failed to fetch BTC price:', err);
      }
    };
    fetchPrice();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      console.log('File selected:', selectedFile.name);
      setFile(selectedFile);
      setSourceA([]); // Reset on new file
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

      console.log('Upload response:', res.data);
      console.log('Data field:', res.data.data);

      // Set source A with the data from response
      if (res.data.data && Array.isArray(res.data.data)) {
        setSourceA(res.data.data);
        setUploadStatus(`Uploaded ${res.data.count} transactions successfully!`);
      } else {
        console.error('Invalid data format:', res.data);
        setUploadStatus('Upload succeeded but data format is invalid');
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      setUploadStatus(`Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchBlockchain = async () => {
    // Parse wallet addresses (comma or line break separated)
    const addresses = wallet
      .split(/[,\n]+/)
      .map(addr => addr.trim())
      .filter(addr => addr.length > 0);

    if (addresses.length === 0) {
      alert("Please enter at least one wallet address");
      return;
    }

    try {
      setLoading(true);
      setFetchStatus('');

      // Fetch transactions for all addresses
      let allTransactions: any[] = [];

      // Number emojis for wallet identification
      const walletEmojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟'];

      for (let i = 0; i < addresses.length; i++) {
        const address = addresses[i];
        const walletId = walletEmojis[i] || `${i + 1}️⃣`;

        console.log(`Fetching transactions for wallet ${walletId}: ${address}`);
        const res = await axios.post('http://localhost:8000/api/fetch-blockchain', {
          wallet_address: address,
          chain: 'bitcoin',
          from_date: fromDate,
          to_date: toDate
        });

        // Add wallet identifier and split date/time for each transaction
        const txsWithWallet = res.data.data.map((tx: any) => {
          const date = new Date(tx.timestamp);
          return {
            ...tx,
            Wallet: walletId,
            Date: date.toISOString().split('T')[0], // YYYY-MM-DD
            Time: date.toTimeString().split(' ')[0], // HH:MM:SS
            WalletAddress: address
          };
        });

        allTransactions = [...allTransactions, ...txsWithWallet];
      }

      // Sort all transactions by timestamp descending
      allTransactions.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

      setSourceB(allTransactions);
      setFetchStatus(`Fetched ${allTransactions.length} transactions from ${addresses.length} address(es) successfully!`);
    } catch (error) {
      console.error(error);
      setFetchStatus('Fetch failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    try {
      setLoading(true);
      const res = await axios.post('http://localhost:8000/api/analyze');
      console.log('Analysis results:', res.data);
      setResults(res.data);
    } catch (error: any) {
      console.error('Analysis error:', error);
      alert(`Analysis failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!sourceB || sourceB.length === 0) return;

    // Headers
    const headers = ['Date', 'Time', 'Wallet', 'Address', 'Tx Hash', 'Asset Type', 'Amount', 'Fee', 'Description'];
    const csvRows = [headers.join(',')];

    // Data Rows
    sourceB.forEach((tx) => {
      // Escape CSV values
      const escape = (val: any) => {
        if (val === null || val === undefined) return '';
        const str = String(val);
        if (str.includes(',') || str.includes('\n') || str.includes('"')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      };

      const description = tx.metadata ?
        (tx.metadata.rune_name || tx.metadata.inscription_id || JSON.stringify(tx.metadata).replace(/"/g, "'")) : '';

      // Determine Asset Type
      let assetType = 'BTC';
      if (tx.metadata) {
        if (tx.metadata.runes) assetType = 'RUNE';
        else if (tx.metadata.rune_name) assetType = 'RUNE';
        else if (tx.metadata.inscription_id) assetType = 'ORDINAL';
      }

      const row = [
        escape(tx.Date),
        escape(tx.Time),
        escape(tx.Wallet),
        escape(tx.WalletAddress || ''),
        escape(tx.tx_id),
        escape(assetType),
        escape(tx.amount),
        escape(tx.fee),
        escape(description)
      ];
      csvRows.push(row.join(','));
    });

    const csvString = csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `blockchain_export_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="w-8 h-8 text-blue-600" />
            BitMatch Reconciliation
          </h1>
          <p className="text-gray-600 mt-2">Dual-Ledger Audit & Reconciliation Agent</p>
        </header>

        {/* Workflow Steps */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">

          {/* Step 1: Upload */}
          <div className="bg-white p-6 rounded-xl shadow-sm border-t-4 border-blue-500">
            <h2 className="text-lg font-semibold mb-4">1. Upload CEX Export</h2>
            <div className="space-y-4">
              <input
                type="file"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500
                  file:mr-4 file:py-2 file:px-4
                  file:rounded-full file:border-0
                  file:text-sm file:font-semibold
                  file:bg-blue-50 file:text-blue-700
                  hover:file:bg-blue-100"
              />
              <button
                onClick={handleUpload}
                disabled={!file || loading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Upload className="w-4 h-4" /> Upload & Preview
              </button>
              {uploadStatus && <p className="text-sm text-green-600 text-center">{uploadStatus}</p>}
            </div>
          </div>

          {/* Step 2: Fetch Blockchain */}
          <div className={`bg-white p-6 rounded-xl shadow-sm border-t-4 ${sourceA.length > 0 ? 'border-indigo-500' : 'border-gray-300 opacity-75'}`}>
            <h2 className="text-lg font-semibold mb-4">2. Fetch Blockchain Data</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">
                  Bitcoin Wallet Address(es)
                  <span className="text-gray-400 ml-1">(separate with comma or line break)</span>
                </label>
                <textarea
                  placeholder="bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql&#10;bc1qeezvh8psmu32tylqxlkpwjf3854n8cp6vv5lk8&#10;383pcVpTUPdTcj4pPnYhhqQds6JLh25rpy"
                  value={wallet}
                  onChange={(e) => setWallet(e.target.value)}
                  disabled={sourceA.length === 0}
                  rows={3}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none resize-none font-mono text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-600 mb-1">From Date</label>
                  <input
                    type="date"
                    value={fromDate}
                    onChange={(e) => setFromDate(e.target.value)}
                    disabled={sourceA.length === 0}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-600 mb-1">To Date</label>
                  <input
                    type="date"
                    value={toDate}
                    onChange={(e) => setToDate(e.target.value)}
                    disabled={sourceA.length === 0}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                  />
                </div>
              </div>
              <button
                onClick={handleFetchBlockchain}
                disabled={sourceA.length === 0 || loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Fetch & Preview
              </button>

              {sourceB.length > 0 && (
                <button
                  onClick={handleExportCSV}
                  className="w-full px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" /> Export Results to CSV
                </button>
              )}

              {fetchStatus && <p className="text-sm text-green-600 text-center">{fetchStatus}</p>}
            </div>
          </div>

          {/* Step 3: Analyze */}
          <div className={`bg-white p-6 rounded-xl shadow-sm border-t-4 ${sourceA.length > 0 && sourceB.length > 0 ? 'border-purple-500' : 'border-gray-300 opacity-75'}`}>
            <h2 className="text-lg font-semibold mb-4">3. Analyze & Reconcile</h2>
            <div className="space-y-4">
              <div className="text-sm text-gray-500 mb-4">
                Ready to compare {sourceA.length} CEX txs vs {sourceB.length} Chain txs.
              </div>
              <button
                onClick={handleAnalyze}
                disabled={sourceA.length === 0 || sourceB.length === 0 || loading}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Activity className="w-4 h-4" /> Run Analysis
              </button>
            </div>
          </div>
        </div>

        {/* Data Preview Area */}
        {(sourceA.length > 0 || sourceB.length > 0) && !results && (
          <div className="mb-8 animate-fade-in">
            <div className="flex justify-end mb-2">
              <label className="inline-flex items-center cursor-pointer">
                <span className="mr-2 text-sm text-gray-700">Display USD Value</span>
                <input
                  type="checkbox"
                  checked={showUSD}
                  onChange={() => setShowUSD(!showUSD)}
                  className="sr-only peer"
                />
                <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
              </label>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <TransactionList
                title="Source A: CEX Export"
                transactions={sourceA}
                colorClass="text-blue-700"
                showUSD={showUSD}
                btcPrice={btcPrice}
              />
              <TransactionList
                title="Source B: Blockchain"
                transactions={sourceB}
                colorClass="text-indigo-700"
                showUSD={showUSD}
                btcPrice={btcPrice}
              />
            </div>
          </div>
        )}

        {/* Results Area */}
        {results && (
          <div className="animate-fade-in">
            <div className="bg-white p-4 rounded-xl shadow-sm mb-4">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-bold text-gray-800">Tax Correction Report</h2>
                <button
                  onClick={() => setResults(null)}
                  className="text-sm text-gray-500 hover:text-gray-700 underline"
                >
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
