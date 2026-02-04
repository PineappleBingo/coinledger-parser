import React from 'react';
import { ExternalLink } from 'lucide-react';

interface Props {
    title: string;
    transactions: any[];
    colorClass: string;
    showUSD?: boolean;
    btcPrice?: number | null;
}

const TransactionList: React.FC<Props> = ({ title, transactions, colorClass, showUSD, btcPrice }) => {
    // Get all unique column names from the data
    const columns = transactions.length > 0 ? Object.keys(transactions[0]) : [];

    const getPatternBadge = (pattern: string) => {
        const patternConfig: Record<string, { label: string; color: string; emoji: string }> = {
            'MINT_BUY': { label: 'Mint/Buy', color: 'bg-purple-100 text-purple-700 border-purple-300', emoji: '🎨' },
            'BULK_MINT': { label: 'Bulk Mint', color: 'bg-purple-100 text-purple-700 border-purple-300', emoji: '🎨✨' },
            'GAS_FEE': { label: 'Gas Fee', color: 'bg-gray-100 text-gray-700 border-gray-300', emoji: '⛽' },
            'SALE': { label: 'Sale', color: 'bg-green-100 text-green-700 border-green-300', emoji: '💰' },
            'SELF_TRANSFER': { label: 'Self Transfer', color: 'bg-blue-100 text-blue-700 border-blue-300', emoji: '🔄' },
            'FIAT_ONRAMP': { label: 'Fiat On-Ramp', color: 'bg-yellow-100 text-yellow-700 border-yellow-300', emoji: '💵' },
            'RUNE_RECEIVE': { label: 'Rune Receive', color: 'bg-orange-100 text-orange-700 border-orange-300', emoji: '🔮' },
            'POTENTIAL_MARKETPLACE_SWAP': { label: 'Marketplace', color: 'bg-indigo-100 text-indigo-700 border-indigo-300', emoji: '🏪' },
        };

        const config = patternConfig[pattern] || { label: pattern, color: 'bg-gray-100 text-gray-600 border-gray-300', emoji: '🏷️' };

        return (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${config.color}`}>
                <span>{config.emoji}</span>
                <span>{config.label}</span>
            </span>
        );
    };

    const formatCellValue = (col: string, value: any, tx: any) => {
        // Handle null/undefined/empty
        if (value === null || value === undefined || value === '') {
            return '-';
        }

        // Handle tx_id column - make it clickable ONLY for blockchain transactions
        if (col === 'tx_id' && value && typeof value === 'string' && value.length > 10) {
            // Check if this is a blockchain transaction (not CEX-only)
            const isBlockchainTx = tx.source && (
                tx.source.toLowerCase().includes('blockchain') ||
                tx.source.toLowerCase().includes('source b') ||
                tx.source === 'BLOCKCHAIN'
            );

            // Only show verification links for actual blockchain transactions
            if (isBlockchainTx) {
                const mempoolLink = `https://mempool.space/tx/${value}`;
                const ordiscanLink = `https://ordiscan.com/tx/${value}`;

                return (
                    <div className="flex items-center gap-2">
                        <span className="font-mono text-xs" title={value}>
                            {value.slice(0, 8)}...{value.slice(-6)}
                        </span>
                        <div className="flex gap-1">
                            <a
                                href={mempoolLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800"
                                title="View on Mempool"
                            >
                                <ExternalLink className="w-3 h-3" />
                            </a>
                            <a
                                href={ordiscanLink}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-purple-600 hover:text-purple-800"
                                title="View on Ordiscan"
                            >
                                <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>
                );
            } else {
                // CEX transaction - just show the ID without links
                return (
                    <span className="font-mono text-xs text-gray-500" title={value}>
                        {value.slice(0, 12)}... <span className="text-xs text-gray-400">(CEX)</span>
                    </span>
                );
            }
        }

        // Handle pattern column - show badge
        if (col === 'pattern' && value && typeof value === 'string') {
            return getPatternBadge(value);
        }

        // Handle USD Conversion for Amount columns
        const colLower = col.toLowerCase();
        if (showUSD && btcPrice && (colLower === 'amount' || colLower === 'volume' || colLower === 'fee' || colLower === 'cost_basis' || colLower === 'proceeds')) {
            const numVal = parseFloat(value);
            if (!isNaN(numVal)) {
                const usdVal = numVal * btcPrice;
                const formattedUsd = usdVal.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
                return (
                    <span>
                        {value} <span className="text-gray-500 text-xs ml-1">({formattedUsd})</span>
                    </span>
                );
            }
        }

        // Special handling for metadata column
        if (col === 'metadata' && typeof value === 'object') {
            const assetType = value.asset_type || 'BTC';
            const badgeColor =
                assetType === 'ORDINAL' ? 'bg-purple-100 text-purple-700 border border-purple-300' :
                    assetType === 'RUNE' ? 'bg-orange-100 text-orange-700 border border-orange-300' :
                        'bg-gray-100 text-gray-600 border border-gray-300';

            return (
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${badgeColor}`}>
                    {assetType === 'ORDINAL' && '🎨 ORDINAL'}
                    {assetType === 'RUNE' && '🔮 RUNE'}
                    {assetType === 'BTC' && 'BTC'}
                </span>
            );
        }

        // Handle other objects (convert to JSON)
        if (typeof value === 'object') {
            return JSON.stringify(value);
        }

        // Regular string conversion
        return String(value);
    };

    return (
        <div className="bg-white p-6 rounded-xl shadow-sm h-full flex flex-col">
            <h3 className={`text-xl font-bold mb-4 ${colorClass}`}>{title} ({transactions.length})</h3>
            <div className="overflow-auto flex-1 max-h-[500px] border rounded-lg">
                <table className="min-w-full divide-y divide-gray-200 relative">
                    <thead className="bg-gray-50 sticky top-0">
                        <tr>
                            {columns.map((col) => (
                                <th key={col} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap">
                                    {col}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {transactions.map((tx, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                                {columns.map((col) => {
                                    const value = tx[col];
                                    const displayValue = formatCellValue(col, value, tx);

                                    // If it's a React element (like our badge or link), render it directly
                                    if (React.isValidElement(displayValue)) {
                                        return (
                                            <td
                                                key={col}
                                                className="px-4 py-2 whitespace-nowrap text-sm text-gray-900"
                                            >
                                                {displayValue}
                                            </td>
                                        );
                                    }

                                    // Otherwise, render as string with truncation
                                    const stringValue = String(displayValue);
                                    return (
                                        <td
                                            key={col}
                                            className="px-4 py-2 whitespace-nowrap text-sm text-gray-900"
                                            title={stringValue}
                                        >
                                            {stringValue.length > 30 ? `${stringValue.slice(0, 30)}...` : stringValue}
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                        {transactions.length === 0 && (
                            <tr>
                                <td colSpan={columns.length || 1} className="px-4 py-8 text-center text-gray-500">
                                    No data available
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TransactionList;
