import React, { useState } from 'react';
import axios from 'axios';
import { Upload, RefreshCw, FileText, Activity } from 'lucide-react';
import ReconciliationTable from './components/ReconciliationTable';
import TransactionList from './components/TransactionList';

function App() {
  const [file, setFile] = useState<File | null>(null);
  const [wallet, setWallet] = useState('');
  const [loading, setLoading] = useState(false);

  // Data States
  const [sourceA, setSourceA] = useState<any[]>([]);
  const [sourceB, setSourceB] = useState<any[]>([]);
  const [results, setResults] = useState<any>(null);

  const [uploadStatus, setUploadStatus] = useState('');
  const [fetchStatus, setFetchStatus] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFile(e.target.files[0]);
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
      setSourceA(res.data.data);
      setUploadStatus(`Uploaded ${res.data.count} transactions successfully!`);
    } catch (error) {
      console.error(error);
      setUploadStatus('Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleFetchBlockchain = async () => {
    if (!wallet) {
      alert("Please enter a wallet address");
      return;
    }

    try {
      setLoading(true);
      const res = await axios.post('http://localhost:8000/api/fetch-blockchain', {
        wallet_address: wallet,
        chain: 'ethereum'
      });
      setSourceB(res.data.data);
      setFetchStatus(`Fetched ${res.data.count} transactions successfully!`);
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
      setResults(res.data);
    } catch (error) {
      console.error(error);
      alert("Analysis failed");
    } finally {
      setLoading(false);
    }
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
              <input
                type="text"
                placeholder="Wallet Address (0x...)"
                value={wallet}
                onChange={(e) => setWallet(e.target.value)}
                disabled={sourceA.length === 0}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none"
              />
              <button
                onClick={handleFetchBlockchain}
                disabled={sourceA.length === 0 || loading}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Fetch & Preview
              </button>
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
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8 animate-fade-in">
            <TransactionList
              title="Source A: CEX Export"
              transactions={sourceA}
              colorClass="text-blue-700"
            />
            <TransactionList
              title="Source B: Blockchain"
              transactions={sourceB}
              colorClass="text-indigo-700"
            />
          </div>
        )}

        {/* Results Area */}
        {results && (
          <div className="bg-white p-6 rounded-xl shadow-sm animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-800">Reconciliation Report</h2>
              <button
                onClick={() => setResults(null)}
                className="text-sm text-gray-500 hover:text-gray-700 underline"
              >
                Back to Preview
              </button>
            </div>
            <ReconciliationTable
              matched={results.matched}
              conflicts={results.conflicts}
              missing={results.missing_in_blockchain}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
