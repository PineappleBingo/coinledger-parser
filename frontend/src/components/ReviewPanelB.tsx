import React from 'react';
import { Download } from 'lucide-react';

interface Props {
    transactions: any[];
    searchQuery: string;
    selectedTxId?: string | null;
    onRowClick?: (txId: string) => void;
    runeOverrides?: Record<string, any>;
    showUSD?: boolean;
    btcPrice?: number | null;
}

// CoinLedger Universal Import Template columns
const TEMPLATE_HEADERS = [
    'Date (UTC)',
    'Platform',
    'Asset Sent',
    'Amount Sent',
    'Asset Received',
    'Amount Received',
    'Fee Currency',
    'Fee Amount',
    'Type',
    'Description',
    'TxHash',
];

const ReviewPanelB: React.FC<Props> = ({ transactions, searchQuery, selectedTxId, onRowClick, runeOverrides = {}, showUSD, btcPrice }) => {

    const formatUSD = (amount: string, assetType: string) => {
        if (!showUSD || !btcPrice || !amount) return '';
        // Only calculate USD for BTC, prevent calculating Ordinal quantities at BTC price
        if (assetType && assetType.toUpperCase() !== 'BTC') return '';
        const val = parseFloat(amount);
        if (isNaN(val) || val === 0) return '';
        const usd = val * btcPrice;
        return ` ($${usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })})`;
    };

    // Get resolved rune name: overrides from Panel A fetch > metadata > raw
    const getResolvedRuneName = (tx: any): { name: string; amount: string } | null => {
        const txId = tx.tx_id || '';
        // Check Panel A overrides first
        const override = runeOverrides[txId];
        if (override && override.runes?.length > 0) {
            const r = override.runes[0];
            let displayName = r.collection ? `${r.collection} - ${r.name}` : r.name;
            if (r.inscription_number && !displayName.includes(String(r.inscription_number))) {
                displayName = `${displayName} (Inscription #${r.inscription_number})`;
            }
            return { name: displayName, amount: r.amount };
        }
        // Check metadata
        const meta = tx.metadata && typeof tx.metadata === 'object' ? tx.metadata : {};
        if (meta.rune_name && !/^RUNE_[a-f0-9]+$/i.test(meta.rune_name)) {
            return { name: meta.rune_name, amount: meta.rune_amount ? String(meta.rune_amount) : '1' };
        }
        return null;
    };

    // Map Source C transactions to CoinLedger template rows
    const mapToTemplates = (tx: any): any[] => {
        const type = tx.coinledger_type || tx.tx_type || '';
        const timestamp = tx.timestamp
            ? new Date(tx.timestamp).toISOString().replace('T', ' ').split('.')[0]
            : '';
        const amount = Math.abs(tx.amount || 0);
        const fee = tx.fee || 0;
        const asset = tx.asset || 'BTC';
        const resolvedRune = getResolvedRuneName(tx);

        let returnRows: any[] = [];
        let primaryRow: any = {
            'Date (UTC)': timestamp,
            'Platform': 'Bitcoin Blockchain',
            'Asset Sent': '',
            'Amount Sent': '',
            'Asset Received': '',
            'Amount Received': '',
            'Fee Currency': fee > 0 ? 'BTC' : '',
            'Fee Amount': fee > 0 ? fee.toFixed(8) : '',
            'Type': type,
            'Description': tx.description || tx.pattern || '',
            'TxHash': tx.tx_id || '',
            _needsReview: !resolvedRune && !!(tx.pattern && ['MINT_BUY', 'BULK_MINT', 'RUNE_RECEIVE', 'SALE', 'MAGIC_EDEN_BUY', 'MAGIC_EDEN_SALE'].includes(tx.pattern)),
            _isIgnored: type === 'Ignored',
            _isUnclassified: !tx.pattern && tx.source === 'BLOCKCHAIN' && (tx.tx_id || '').length > 10 && type !== 'Ignored',
        };

        if (type === 'Trade' || type === 'Mint') {
            if (tx.amount < 0 || tx.pattern === 'MINT_BUY' || tx.pattern === 'BULK_MINT' || tx.pattern === 'MAGIC_EDEN_BUY' || tx.pattern === 'MAGIC_EDEN_BUY_ISOLATED') {
                // Buying: BTC sent, NFT/Rune received
                primaryRow['Asset Sent'] = 'BTC';

                // Check for isolated buy pattern
                if (tx.pattern === 'MAGIC_EDEN_BUY_ISOLATED') {
                    primaryRow['Amount Sent'] = ''; // User Input Required
                } else {
                    primaryRow['Amount Sent'] = amount.toFixed(8);
                }

                if (resolvedRune) {
                    primaryRow['Asset Received'] = resolvedRune.name;
                    primaryRow['Amount Received'] = resolvedRune.amount;
                } else {
                    const meta = tx.metadata && typeof tx.metadata === 'object' ? tx.metadata : {};
                    if (meta.asset_type === 'ORDINAL') {
                        primaryRow['Asset Received'] = 'Ordinal #';
                        primaryRow['Amount Received'] = '1';
                    } else {
                        primaryRow['Asset Received'] = 'BTC';
                        primaryRow['Amount Received'] = amount.toFixed(8);
                    }
                }
            } else {
                // Selling: NFT/Rune sent, BTC received
                if (resolvedRune) {
                    primaryRow['Asset Sent'] = resolvedRune.name;
                    primaryRow['Amount Sent'] = resolvedRune.amount;
                } else {
                    primaryRow['Asset Sent'] = asset;
                    primaryRow['Amount Sent'] = amount.toFixed(8);
                }
                primaryRow['Asset Received'] = 'BTC';
                primaryRow['Amount Received'] = amount.toFixed(8);
            }
            returnRows.push(primaryRow);

            if (tx.pattern === 'MAGIC_EDEN_BUY_ISOLATED' && resolvedRune) {
                // Return a second row for the dust deposit, since it's isolated and we need to account for it
                returnRows.push({
                    'Date (UTC)': timestamp,
                    'Platform': 'Bitcoin Blockchain',
                    'Asset Sent': '',
                    'Amount Sent': '',
                    'Asset Received': 'BTC',
                    'Amount Received': amount.toFixed(8),
                    'Fee Currency': '', // fee already paid in row 1
                    'Fee Amount': '',
                    'Type': 'Ignored',
                    'Description': 'BTC dust received with Ordinal/Rune',
                    'TxHash': tx.tx_id || '',
                    _needsReview: false,
                    _isIgnored: true,
                    _isUnclassified: false,
                });
            }
        } else if (type === 'Deposit' || type === 'Income' || type === 'Airdrop') {
            if (resolvedRune) {
                // Return TWO rows: The Rune and the BTC dust
                primaryRow['Asset Received'] = resolvedRune.name;
                primaryRow['Amount Received'] = resolvedRune.amount;
                returnRows.push(primaryRow);

                returnRows.push({
                    'Date (UTC)': timestamp,
                    'Platform': 'Bitcoin Blockchain',
                    'Asset Sent': '',
                    'Amount Sent': '',
                    'Asset Received': 'BTC',
                    'Amount Received': amount.toFixed(8),
                    'Fee Currency': '', // fee already paid in row 1
                    'Fee Amount': '',
                    'Type': 'Ignored',
                    'Description': 'BTC dust received with Ordinal/Rune',
                    'TxHash': tx.tx_id || '',
                    _needsReview: false,
                    _isIgnored: true,
                    _isUnclassified: false,
                });
            } else {
                primaryRow['Asset Received'] = asset;
                primaryRow['Amount Received'] = amount.toFixed(8);
                returnRows.push(primaryRow);
            }
        } else if (type === 'Withdrawal') {
            primaryRow['Asset Sent'] = asset;
            primaryRow['Amount Sent'] = amount.toFixed(8);
            returnRows.push(primaryRow);
        } else {
            // Default handling
            primaryRow['Asset Received'] = asset;
            primaryRow['Amount Received'] = amount.toFixed(8);
            returnRows.push(primaryRow);
        }

        return returnRows;
    };

    // Filter
    const filtered = searchQuery
        ? transactions.filter(tx => {
            const q = searchQuery.toLowerCase();
            return (
                (tx.tx_id && tx.tx_id.toLowerCase().includes(q)) ||
                (tx.asset && tx.asset.toLowerCase().includes(q)) ||
                (tx.pattern && tx.pattern.toLowerCase().includes(q)) ||
                (tx.description && tx.description.toLowerCase().includes(q)) ||
                (tx.coinledger_type && tx.coinledger_type.toLowerCase().includes(q))
            );
        })
        : transactions;

    const rows = filtered.flatMap(mapToTemplates);

    const handleDownloadCSV = () => {
        const allRows = transactions.filter(tx => {
            const type = tx.coinledger_type || tx.tx_type || '';
            return type !== 'Ignored';
        }).flatMap(mapToTemplates);

        // Strip emojis for clean CoinLedger import
        const stripEmoji = (str: string) => str.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}\u{E0020}-\u{E007F}\u{2753}\u{2754}\u{2755}\u{FE0F}]/gu, '').trim();

        const csvHeader = TEMPLATE_HEADERS.join(',');
        const csvRows = allRows.map(row =>
            TEMPLATE_HEADERS.map(h => {
                const val = stripEmoji((row as any)[h] || '');
                if (val.includes(',') || val.includes('\n') || val.includes('"')) {
                    return `"${val.replace(/"/g, '""')}"`;
                }
                return val;
            }).join(',')
        );
        const csv = [csvHeader, ...csvRows].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `CoinLedger_Universal_Import_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const getRowClasses = (row: any) => {
        let classes = 'hover:bg-gray-800/30 transition-colors cursor-pointer ';
        if (row._isIgnored) classes += 'opacity-40 line-through ';
        if (row._needsReview) classes += 'bg-yellow-500/10 border-l-2 border-yellow-500 ';
        if (row._isUnclassified) classes += 'bg-blue-500/5 border-l-2 border-blue-400/40 ';
        // Cross-highlight: match selectedTxId
        if (selectedTxId && row['TxHash'] === selectedTxId) {
            classes += 'bg-purple-500/10 ring-1 ring-purple-500/30 ';
        }
        return classes;
    };

    return (
        <div className="h-full flex flex-col">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-lg font-bold text-cyan-400 flex items-center gap-2">
                    📄 Review Panel B — CoinLedger Import
                    <span className="text-sm font-normal text-gray-500">({rows.length})</span>
                </h3>
                <button
                    onClick={handleDownloadCSV}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-green-500/20 text-green-300 hover:bg-green-500/30 border border-green-500/30 transition-all"
                >
                    <Download className="w-3.5 h-3.5" /> Download CSV
                </button>
            </div>

            <div className="flex-1 overflow-auto max-h-[700px] rounded-lg border border-gray-700/50 bg-gray-900/30">
                <table className="min-w-full divide-y divide-gray-700/50">
                    <thead className="bg-gray-800/50 sticky top-0 z-10">
                        <tr>
                            {TEMPLATE_HEADERS.map(h => (
                                <th key={h} className="px-2 py-2 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-800/50">
                        {rows.map((row, idx) => (
                            <tr
                                key={idx}
                                className={getRowClasses(row)}
                                onClick={() => onRowClick && row['TxHash'] && onRowClick(row['TxHash'])}
                            >
                                {TEMPLATE_HEADERS.map(h => {
                                    const val = (row as any)[h] || '';
                                    return (
                                        <td key={h} className="px-2 py-2 text-sm text-gray-300 whitespace-nowrap" title={val}>
                                            {h === 'TxHash' && val.length > 10
                                                ? <span className="font-mono text-xs">{val.slice(0, 8)}…{val.slice(-6)}</span>
                                                : h === 'Type'
                                                    ? <span className="inline-flex items-center gap-1">
                                                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${val === 'Trade' ? 'bg-blue-500/20 text-blue-400' :
                                                            val === 'Deposit' ? 'bg-green-500/20 text-green-400' :
                                                                val === 'Withdrawal' ? 'bg-red-500/20 text-red-400' :
                                                                    val === 'Airdrop' ? 'bg-cyan-500/20 text-cyan-400' :
                                                                        val === 'Mint' ? 'bg-purple-500/20 text-purple-400' :
                                                                            'bg-gray-500/20 text-gray-400'
                                                            }`}>{val}</span>
                                                        {(row as any)._isUnclassified && (
                                                            <span className="relative group">
                                                                <span className="text-yellow-500 cursor-help text-sm" title="Unclassified — address may not be in your tracked wallets">❓</span>
                                                            </span>
                                                        )}
                                                    </span>
                                                    : (h === 'Amount Sent' || h === 'Amount Received' || h === 'Fee Amount') && val
                                                        ? <>{val}{formatUSD(val, h === 'Fee Amount' ? 'BTC' : (row as any)[h.replace('Amount', 'Asset')] || 'BTC')}</>
                                                        : val.length > 20 ? `${val.slice(0, 20)}…` : val
                                            }
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                        {rows.length === 0 && (
                            <tr>
                                <td colSpan={TEMPLATE_HEADERS.length} className="px-4 py-12 text-center text-gray-500">
                                    No transactions to display. Run Option C first.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
            {rows.some(r => r._needsReview) && (
                <p className="text-xs text-yellow-400 mt-2">⚠️ Yellow rows need review — click "Fetch Ordinal/Rune Info" in Panel A to resolve. Panel B updates automatically.</p>
            )}
        </div>
    );
};

export default ReviewPanelB;
