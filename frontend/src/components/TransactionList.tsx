import React from 'react';
import { ExternalLink } from 'lucide-react';

interface Props {
    title: string;
    transactions: any[];
    colorClass: string;
    showUSD?: boolean;
    btcPrice?: number | null;
    selectedTxId?: string | null;
    onRowClick?: (txId: string) => void;
    missingTxIds?: Set<string>;
}

const TransactionList: React.FC<Props> = ({
    title,
    transactions,
    colorClass,
    showUSD,
    btcPrice,
    selectedTxId,
    onRowClick,
    missingTxIds,
}) => {
    // Get all unique column names from the data, exclude internal verify_* fields
    const columns = transactions.length > 0
        ? Object.keys(transactions[0]).filter(col => !col.startsWith('verify_'))
        : [];

    const getPatternBadge = (pattern: string) => {
        const patternConfig: Record<string, { label: string; color: string; emoji: string }> = {
            'MINT_BUY': { label: 'Mint/Buy', color: 'bg-purple-500/20 text-purple-400 dark:text-purple-300 border-purple-500/30', emoji: '🎨' },
            'BULK_MINT': { label: 'Bulk Mint', color: 'bg-purple-500/20 text-purple-400 dark:text-purple-300 border-purple-500/30', emoji: '🎨✨' },
            'GAS_FEE': { label: 'Gas Fee', color: 'bg-gray-500/20 text-gray-400 dark:text-gray-300 border-gray-500/30', emoji: '⛽' },
            'SALE': { label: 'Sale', color: 'bg-green-500/20 text-green-400 dark:text-green-300 border-green-500/30', emoji: '💰' },
            'SELF_TRANSFER': { label: 'Self Transfer', color: 'bg-blue-500/20 text-blue-400 dark:text-blue-300 border-blue-500/30', emoji: '🔄' },
            'FIAT_ONRAMP': { label: 'Fiat On-Ramp', color: 'bg-yellow-500/20 text-yellow-400 dark:text-yellow-300 border-yellow-500/30', emoji: '💵' },
            'RUNE_RECEIVE': { label: 'Rune Receive', color: 'bg-orange-500/20 text-orange-400 dark:text-orange-300 border-orange-500/30', emoji: '🔮' },
            'NFT_TRADE': { label: 'NFT Trade', color: 'bg-indigo-500/20 text-indigo-400 dark:text-indigo-300 border-indigo-500/30', emoji: '🏪' },
            'MAGIC_EDEN_BUY': { label: 'ME Buy', color: 'bg-pink-500/20 text-pink-400 dark:text-pink-300 border-pink-500/30', emoji: '🪄' },
            'MAGIC_EDEN_BUY_ISOLATED': { label: 'ME Buy (Isolated)', color: 'bg-pink-500/20 text-pink-400 dark:text-pink-300 border-pink-500/30', emoji: '🪄' },
            'MAGIC_EDEN_SALE': { label: 'ME Sale', color: 'bg-pink-500/20 text-pink-400 dark:text-pink-300 border-pink-500/30', emoji: '🪄💰' },
            'POTENTIAL_MARKETPLACE_SWAP': { label: 'Marketplace', color: 'bg-indigo-500/20 text-indigo-400 dark:text-indigo-300 border-indigo-500/30', emoji: '🏪' },
        };

        const config = patternConfig[pattern] || { label: pattern, color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', emoji: '🏷️' };

        return (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${config.color}`}>
                <span>{config.emoji}</span>
                <span>{config.label}</span>
            </span>
        );
    };

    const getCoinLedgerTypeBadge = (type: string) => {
        const typeConfig: Record<string, { color: string; icon: string }> = {
            'Trade': { color: 'bg-blue-500/20 text-blue-400 border-blue-500/30', icon: '🔄' },
            'Deposit': { color: 'bg-green-500/20 text-green-400 border-green-500/30', icon: '📥' },
            'Withdrawal': { color: 'bg-red-500/20 text-red-400 border-red-500/30', icon: '📤' },
            'Income': { color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: '💰' },
            'Ignored': { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30 line-through', icon: '🚫' },
            'Investment Loss': { color: 'bg-orange-500/20 text-orange-400 border-orange-500/30', icon: '📉' },
            'Airdrop': { color: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30', icon: '🎁' },
        };
        const config = typeConfig[type] || { color: 'bg-gray-500/20 text-gray-400 border-gray-500/30', icon: '❔' };
        return (
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold border ${config.color}`}>
                <span>{config.icon}</span>
                <span>{type}</span>
            </span>
        );
    };

    const formatCellValue = (col: string, value: any, tx: any) => {
        if (value === null || value === undefined || value === '') {
            return '-';
        }

        // Handle tx_id column - make it clickable ONLY for blockchain transactions
        if (col === 'tx_id' && value && typeof value === 'string' && value.length > 10) {
            const isBlockchainTx = tx.source && (
                tx.source.toLowerCase().includes('blockchain') ||
                tx.source.toLowerCase().includes('source b') ||
                tx.source === 'BLOCKCHAIN'
            );

            if (isBlockchainTx) {
                const mempoolLink = `https://mempool.space/tx/${value}`;
                const blockchainLink = `https://www.blockchain.com/btc/tx/${value}`;
                const ordiscanLink = `https://ordiscan.com/tx/${value}`;

                return (
                    <div className="flex items-center gap-2">
                        <span className="font-mono text-xs" title={value}>
                            {value.slice(0, 8)}...{value.slice(-6)}
                        </span>
                        <div className="flex gap-1">
                            <a href={mempoolLink} target="_blank" rel="noopener noreferrer"
                                className="text-blue-500 hover:text-blue-300" title="Mempool">
                                <ExternalLink className="w-3 h-3" />
                            </a>
                            <a href={blockchainLink} target="_blank" rel="noopener noreferrer"
                                className="text-green-500 hover:text-green-300" title="Blockchain.com">
                                <ExternalLink className="w-3 h-3" />
                            </a>
                            <a href={ordiscanLink} target="_blank" rel="noopener noreferrer"
                                className="text-purple-500 hover:text-purple-300" title="Ordiscan">
                                <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>
                );
            } else {
                return (
                    <span className="font-mono text-xs text-gray-500 dark:text-gray-400" title={value}>
                        {value.slice(0, 12)}... <span className="text-xs opacity-60">(CEX)</span>
                    </span>
                );
            }
        }

        // Handle pattern column - show badge
        if (col === 'pattern' && value && typeof value === 'string') {
            return getPatternBadge(value);
        }

        // Handle coinledger_type column
        if (col === 'coinledger_type' && value && typeof value === 'string') {
            return getCoinLedgerTypeBadge(value);
        }

        // Handle tx_type column
        if (col === 'tx_type' && value && typeof value === 'string') {
            return getCoinLedgerTypeBadge(value);
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
                        {value} <span className="text-gray-400 dark:text-gray-500 text-xs ml-1">({formattedUsd})</span>
                    </span>
                );
            }
        }

        // Special handling for metadata column
        if (col === 'metadata' && typeof value === 'object') {
            const assetType = value.asset_type || 'BTC';
            const badgeColor =
                assetType === 'ORDINAL' ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' :
                    assetType === 'RUNE' ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
                        'bg-gray-500/20 text-gray-400 border border-gray-500/30';

            return (
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${badgeColor}`}>
                    {assetType === 'ORDINAL' && '🎨 ORDINAL'}
                    {assetType === 'RUNE' && '🔮 RUNE'}
                    {assetType === 'BTC' && 'BTC'}
                </span>
            );
        }

        if (typeof value === 'object') {
            return JSON.stringify(value);
        }

        return String(value);
    };

    const getRowClasses = (tx: any) => {
        const txId = tx.tx_id || '';
        let classes = 'cursor-pointer transition-all duration-200 ';

        // Selected row highlight
        if (selectedTxId && txId === selectedTxId) {
            classes += 'tx-selected ';
        }

        // Missing transaction highlight
        if (missingTxIds && missingTxIds.has(txId)) {
            classes += 'tx-warning ';
        }

        // Default hover
        classes += 'hover:bg-gray-50 dark:hover:bg-white/5 ';

        return classes;
    };

    return (
        <div className="glass p-4 h-full flex flex-col bg-white/90 dark:bg-transparent">
            <h3 className={`text-lg font-bold mb-3 ${colorClass}`}>{title} ({transactions.length})</h3>
            <div className="overflow-auto flex-1 max-h-[500px] rounded-lg border border-gray-200 dark:border-gray-700/50 bg-white dark:bg-transparent">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700/50 relative">
                    <thead className="bg-gray-50 dark:bg-gray-800/50 sticky top-0 z-10">
                        <tr>
                            {columns.map((col) => (
                                <th key={col} className="px-3 py-2.5 text-left text-xs font-medium text-gray-600 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                                    {col.replace(/_/g, ' ')}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800/50 bg-white dark:bg-transparent">
                        {transactions.map((tx, idx) => (
                            <tr
                                key={idx}
                                className={getRowClasses(tx)}
                                onClick={() => onRowClick && onRowClick(tx.tx_id || '')}
                            >
                                {columns.map((col) => {
                                    const value = tx[col];
                                    const displayValue = formatCellValue(col, value, tx);

                                    if (React.isValidElement(displayValue)) {
                                        return (
                                            <td key={col} className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">
                                                {displayValue}
                                            </td>
                                        );
                                    }

                                    const stringValue = String(displayValue);
                                    return (
                                        <td
                                            key={col}
                                            className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200"
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
                                <td colSpan={columns.length || 1} className="px-4 py-8 text-center text-gray-400 dark:text-gray-500">
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
