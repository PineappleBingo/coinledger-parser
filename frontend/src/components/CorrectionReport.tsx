import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Info, ExternalLink, AlertCircle, Image as ImageIcon, RefreshCw } from 'lucide-react';
import { fetchOrdinalInfo, fetchRuneInfo, formatRuneAmount, type OrdinalInfo, type RuneInfo } from '../utils/apiClient';
import { RuneFetchButtons } from './RuneFetchButtons';

interface Transaction {
    date: string;
    time: string;
    type: string;
    amount: number;
    asset: string;
    tx_id: string;
    source: string;
    metadata?: {
        asset_type?: string;
        inscription_id?: string;
        rune_name?: string;
        rune_amount?: string;
        rune_divisibility?: number;
        runes?: Array<{ name: string; amount: string; divisibility: number }>;
    };
}

interface RecommendedAction {
    action_type: string;
    reason: string;
    note?: string;
    warning?: string;
    sent_asset?: string;
    sent_amount?: string | number;
    received_asset?: string;
    received_quantity?: number;
    ordiscan_link?: string;
    hiro_link?: string;
    unisat_link?: string;
    ordinals_link?: string;
    requires_ordiscan?: boolean;
    transaction?: Transaction;
    transactions?: Transaction[];
}

interface CorrectionSuggestion {
    pattern: string;
    confidence: number;
    severity: string;
    tax_impact: string;
    affected_transactions: Transaction[];
    recommended_actions: RecommendedAction[];
}

interface CorrectionReportProps {
    suggestions: CorrectionSuggestion[];
    summary: {
        total_issues: number;
        by_severity: { HIGH: number; MEDIUM: number; LOW: number };
        by_pattern: Record<string, number>;
    };
    showUSD?: boolean;
    btcPrice?: number | null;
}

const CorrectionReport: React.FC<CorrectionReportProps> = ({ suggestions, summary, showUSD, btcPrice }) => {

    const formatCurrency = (amount: any, isWrapper = true) => {
        if (!amount) return '-';
        const num = parseFloat(amount);
        if (isNaN(num)) return amount;

        if (showUSD && btcPrice) {
            const usdVal = num * btcPrice;
            const formatted = usdVal.toLocaleString('en-US', { style: 'currency', currency: 'USD' });
            return isWrapper ? (
                <span>
                    {amount} <span className="text-gray-500 text-xs">({formatted})</span>
                </span>
            ) : formatted;
        }
        return amount;
    };

    const OrdinalPreview: React.FC<{ transaction: Transaction }> = ({ transaction }) => {
        const [info, setInfo] = useState<OrdinalInfo | null>(null);
        const [loading, setLoading] = useState(false);

        // Use inscription_id from metadata if available, otherwise fall back to tx_id
        const inscriptionId = transaction.metadata?.inscription_id || transaction.tx_id;

        // Auto-fetch disabled per user request
        // useEffect(() => { ... }, [inscriptionId]);

        if (!inscriptionId) return null;

        const ordinalLink = `https://ordinals.com/inscription/${inscriptionId}`;

        return (
            <div className="mt-3 p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <div className="flex items-start gap-3">
                    {/* Ordinal Image/Icon */}
                    <div className="flex-shrink-0">
                        {loading ? (
                            <div className="w-16 h-16 bg-gray-200 rounded animate-pulse flex items-center justify-center">
                                <ImageIcon className="w-6 h-6 text-gray-400" />
                            </div>
                        ) : info && info.content_url ? (
                            <a href={ordinalLink} target="_blank" rel="noopener noreferrer" className="block">
                                <img
                                    src={info.content_url}
                                    alt={info.name || `Inscription #${info.inscription_number}`}
                                    className="w-16 h-16 rounded border-2 border-purple-300 hover:border-purple-500 transition-colors object-cover cursor-pointer"
                                    onError={(e) => {
                                        // Fallback if image fails to load
                                        (e.target as HTMLImageElement).style.display = 'none';
                                        (e.target as HTMLImageElement).parentElement!.innerHTML =
                                            '<div class="w-16 h-16 bg-purple-100 rounded border-2 border-purple-300 flex items-center justify-center"><svg class="w-8 h-8 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg></div>';
                                    }}
                                />
                            </a>
                        ) : (
                            <div className="w-16 h-16 bg-purple-100 rounded border-2 border-purple-300 flex items-center justify-center">
                                <ImageIcon className="w-8 h-8 text-purple-500" />
                            </div>
                        )}
                    </div>

                    {/* Ordinal Info */}
                    <div className="flex-1 min-w-0">
                        {loading ? (
                            <div className="space-y-2">
                                <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
                                <div className="h-3 bg-gray-200 rounded w-1/2 animate-pulse"></div>
                            </div>
                        ) : info ? (
                            <>
                                <a
                                    href={ordinalLink}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="font-semibold text-purple-700 hover:text-purple-900 hover:underline flex items-center gap-1"
                                >
                                    {info.name || `Inscription #${info.inscription_number}`}
                                    <ExternalLink className="w-3 h-3" />
                                </a>
                                <div className="text-xs text-gray-600 mt-1">
                                    <div>Inscription #{info.inscription_number}</div>
                                    {info.collection && <div className="text-purple-600">Collection: {info.collection}</div>}
                                </div>
                            </>
                        ) : (
                            <div className="text-sm">
                                <button
                                    onClick={() => {
                                        setLoading(true);
                                        fetchOrdinalInfo(inscriptionId).then(data => {
                                            setInfo(data);
                                            setLoading(false);
                                        });
                                    }}
                                    className="text-purple-600 hover:text-purple-800 hover:underline flex items-center gap-1"
                                >
                                    Fetch Inscription Info
                                    <RefreshCw className="w-3 h-3 ml-1" />
                                </button>
                                <div className="text-xs text-gray-500 mt-1">
                                    Click to load inscription details from API
                                </div>
                                <a
                                    href={ordinalLink}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-xs text-gray-400 hover:text-gray-600 hover:underline flex items-center gap-1 mt-1"
                                >
                                    Or View on Ordinals.com
                                    <ExternalLink className="w-2 h-2" />
                                </a>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    };

    // Rune Preview Component
    const RunePreview: React.FC<{ runeName: string; txId: string; metadata?: Transaction['metadata'] }> = ({ runeName, txId, metadata }) => {
        // Now storing an array of RuneInfo
        const [runeInfos, setRuneInfos] = useState<RuneInfo[]>([]);
        const [loading, setLoading] = useState(false);
        const [manuallyFetchedRunes, setManuallyFetchedRunes] = useState<Array<{ name: string; amount: string; divisibility: number }>>([]);
        const [fetchSource, setFetchSource] = useState<string | null>(null);

        useEffect(() => {
            setLoading(true);
            fetchRuneInfo(txId, runeName).then(data => {
                if (data && data.length > 0) {
                    setRuneInfos(data);
                }
                setLoading(false);
            });
        }, [txId, runeName]);

        // Handle manually fetched Rune data (from buttons)
        const handleRuneFetched = (runes: Array<{ name: string; amount: string; divisibility: number }>, source: string) => {
            setManuallyFetchedRunes(runes);
            setFetchSource(source);
            console.log(`✅ Fetched ${runes.length} Rune(s) from ${source}`);
        };

        // Determine list of runes to display
        // Priority: Manually fetched > API fetched > Metadata (runes list) > Metadata (single rune)
        const runesToDisplay: Array<{ name: string; amount: string; divisibility: number }> = [];

        if (manuallyFetchedRunes.length > 0) {
            runesToDisplay.push(...manuallyFetchedRunes);
        } else if (runeInfos.length > 0) {
            runesToDisplay.push(...runeInfos.map(r => ({ name: r.rune_name, amount: r.amount, divisibility: r.divisibility })));
        } else if (metadata?.runes && metadata.runes.length > 0) {
            runesToDisplay.push(...metadata.runes);
        } else {
            // Fallback to single rune props/metadata
            runesToDisplay.push({
                name: metadata?.rune_name || runeName,
                amount: metadata?.rune_amount || 'Unknown',
                divisibility: metadata?.rune_divisibility || 0
            });
        }

        // Check if Rune name is placeholder (only relevant if single rune and it looks like a placeholder)
        const isPlaceholder = runesToDisplay.length === 1 && runesToDisplay[0].name.startsWith('RUNE_') && !manuallyFetchedRunes.length;

        return (
            <div className="mt-3 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 mt-1">
                        <div className="w-12 h-12 bg-orange-100 rounded-full border-2 border-orange-300 flex items-center justify-center">
                            <span className="text-2xl">🔮</span>
                        </div>
                    </div>
                    <div className="flex-1 w-full">
                        {loading && runesToDisplay.length === 0 ? (
                            <div className="space-y-2">
                                <div className="h-4 bg-gray-200 rounded w-3/4 animate-pulse"></div>
                                <div className="h-3 bg-gray-200 rounded w-1/2 animate-pulse"></div>
                            </div>
                        ) : (
                            <>
                                {/* Render retrieved runes list */}
                                <div className="space-y-3">
                                    {runesToDisplay.map((rune, idx) => (
                                        <div key={idx} className={idx > 0 ? "pt-2 border-t border-orange-200" : ""}>
                                            <div className="font-semibold text-orange-700 break-all">{rune.name}</div>
                                            <div className="text-sm text-gray-700 mt-0.5">
                                                Amount: <span className="font-mono bg-orange-100 px-1 rounded">{formatRuneAmount(rune.amount, rune.divisibility)}</span>
                                            </div>
                                            {/* Link for individual rune */}
                                            <div className="mt-1 text-xs">
                                                <a
                                                    href={`https://ordinals.com/rune/${rune.name}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-orange-600 hover:text-orange-800 hover:underline inline-flex items-center gap-1"
                                                >
                                                    Ordinals.com <ExternalLink className="w-2.5 h-2.5" />
                                                </a>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* Shared Links / Buttons */}
                                <div className="mt-3 pt-2 border-t border-orange-200 flex flex-wrap gap-2 text-xs items-center">
                                    <span className="text-gray-500">Transaction:</span>
                                    <a
                                        href={`https://mempool.space/tx/${txId}`}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1"
                                    >
                                        Mempool.space <ExternalLink className="w-3 h-3" />
                                    </a>
                                </div>

                                {/* Show fetch buttons if Rune needs to be fetched (placeholder or user wants to retry/verify) or if explicitly requested */}
                                {(isPlaceholder || (!loading && runesToDisplay.some(r => r.name.startsWith('RUNE_')))) && (
                                    <RuneFetchButtons
                                        txId={txId}
                                        onRuneFetched={handleRuneFetched}
                                    />
                                )}

                                {/* Show success message if fetched */}
                                {fetchSource && (
                                    <div className="mt-2 text-xs text-green-600 bg-green-50 border border-green-200 rounded px-2 py-1">
                                        ✅ Successfully fetched {manuallyFetchedRunes.length} Rune(s) from {fetchSource}
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                </div>
            </div>
        );
    };


    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'HIGH': return 'border-red-500 bg-red-50';
            case 'MEDIUM': return 'border-yellow-500 bg-yellow-50';
            case 'LOW': return 'border-blue-500 bg-blue-50';
            default: return 'border-gray-500 bg-gray-50';
        }
    };

    const getSeverityIcon = (severity: string) => {
        switch (severity) {
            case 'HIGH': return <AlertTriangle className="w-5 h-5 text-red-600" />;
            case 'MEDIUM': return <AlertCircle className="w-5 h-5 text-yellow-600" />;
            case 'LOW': return <Info className="w-5 h-5 text-blue-600" />;
            default: return <Info className="w-5 h-5 text-gray-600" />;
        }
    };

    const getPatternTitle = (pattern: string) => {
        const titles: Record<string, string> = {
            'MINT_BUY': '🎨 Mint/Buy Pattern',
            'BULK_MINT': '🎨✨ Bulk Mint Pattern',
            'GAS_FEE': '⛽ Gas Fee Pattern',
            'SALE': '💰 Sale Pattern',
            'SELF_TRANSFER': '🔄 Self Transfer Pattern',
            'NFT_MARKETPLACE_BUY': '🖼️ NFT Marketplace Buy',
            'NFT_MARKETPLACE_SALE': '💰 NFT Marketplace Sale',
            'NFT_MARKETPLACE_BUY_CROSSREF': '🪄 Magic Eden Buy (Matched)',
            'NFT_MARKETPLACE_SALE_CROSSREF': '🪄 Magic Eden Sale (Matched)',
            'FIAT_ONRAMP': '💵 Fiat On-Ramp',
            'UNMATCHED_ASSET_TRANSFER': '⚠️ Unmatched Asset Transfer'
        };
        return titles[pattern] || pattern;
    };

    const getTaxImpactBadge = (impact: string) => {
        const badges: Record<string, { text: string; color: string }> = {
            'ESTABLISHES_COST_BASIS': { text: 'Establishes Cost Basis', color: 'bg-purple-100 text-purple-800' },
            'TAX_DEDUCTIBLE': { text: 'Tax Deductible', color: 'bg-green-100 text-green-800' },
            'TAXABLE_INCOME': { text: 'Taxable Income', color: 'bg-orange-100 text-orange-800' },
            'NON_TAXABLE': { text: 'Non-Taxable', color: 'bg-gray-100 text-gray-800' }
        };
        const badge = badges[impact] || { text: impact, color: 'bg-gray-100 text-gray-800' };
        return (
            <span className={`px-2 py-1 rounded-full text-xs font-semibold ${badge.color}`}>
                {badge.text}
            </span>
        );
    };

    return (
        <div className="space-y-6">
            {/* Summary Dashboard */}
            <div className="bg-white p-6 rounded-xl shadow-sm border-t-4 border-indigo-500">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">📊 Tax Correction Summary for 2025</h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-3xl font-bold text-indigo-600">{summary.total_issues}</div>
                        <div className="text-sm text-gray-600">Total Issues Found</div>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="space-y-1">
                            <div className="flex justify-between text-sm">
                                <span className="text-red-600">🔴 HIGH</span>
                                <span className="font-semibold">{summary.by_severity.HIGH}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-yellow-600">🟡 MEDIUM</span>
                                <span className="font-semibold">{summary.by_severity.MEDIUM}</span>
                            </div>
                            <div className="flex justify-between text-sm">
                                <span className="text-blue-600">🟢 LOW</span>
                                <span className="font-semibold">{summary.by_severity.LOW}</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg">
                        <div className="text-sm text-gray-600 mb-2">By Pattern:</div>
                        <div className="space-y-1">
                            {Object.entries(summary.by_pattern).map(([pattern, count]) => (
                                <div key={pattern} className="flex justify-between text-xs">
                                    <span className="truncate">{pattern}</span>
                                    <span className="font-semibold ml-2">{count}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded">
                    <div className="flex items-start">
                        <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
                        <div className="text-sm text-yellow-800">
                            <strong>Important:</strong> When marking transactions as "Ignored", do NOT delete them from CoinLedger.
                            Deleting will cause tax issues when you sell the asset later.
                        </div>
                    </div>
                </div>
            </div>

            {/* Correction Cards */}
            {suggestions.map((suggestion, idx) => (
                <div key={idx} className={`bg-white p-6 rounded-xl shadow-sm border-t-4 ${getSeverityColor(suggestion.severity)}`}>
                    {/* Header */}
                    <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                            {getSeverityIcon(suggestion.severity)}
                            <div>
                                <h3 className="text-lg font-semibold text-gray-800">
                                    {getPatternTitle(suggestion.pattern)}
                                </h3>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="text-xs bg-gray-200 px-2 py-1 rounded-full font-mono">
                                        {(suggestion.confidence * 100).toFixed(0)}% Confidence
                                    </span>
                                    {getTaxImpactBadge(suggestion.tax_impact)}
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Affected Transactions */}
                    <div className="mb-4">
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">Affected Transactions:</h4>
                        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                            {suggestion.affected_transactions.map((tx, txIdx) => {
                                // Get asset type from metadata
                                const assetType = tx.metadata?.asset_type || 'BTC';
                                const assetTagColor =
                                    assetType === 'ORDINAL' ? 'bg-purple-100 text-purple-700 border-purple-300' :
                                        assetType === 'RUNE' ? 'bg-orange-100 text-orange-700 border-orange-300' :
                                            'bg-gray-100 text-gray-600 border-gray-300';

                                // Generate links if applicable
                                const mempoolLink = tx.source === 'BLOCKCHAIN' && tx.tx_id ? `https://mempool.space/tx/${tx.tx_id}` : null;

                                return (
                                    <div key={txIdx} className="flex items-center justify-between text-sm border-b border-gray-200 last:border-0 pb-2 last:pb-0">
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono text-xs text-gray-500">{tx.date} {tx.time}</span>
                                            <span className={`px-2 py-0.5 rounded text-xs font-semibold ${tx.type === 'Withdrawal' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                                                }`}>
                                                {tx.type}
                                            </span>
                                            {/* Asset Type Tag */}
                                            <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${assetTagColor}`}>
                                                {assetType === 'ORDINAL' && '🎨 ORDINAL'}
                                                {assetType === 'RUNE' && '🔮 RUNE'}
                                                {assetType === 'BTC' && 'BTC'}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="font-semibold">{tx.amount > 0 ? '+' : ''}{formatCurrency(tx.amount)} {tx.asset}</span>
                                            <span className="text-xs text-gray-400">({tx.source})</span>

                                            {/* Verification Icon */}
                                            {mempoolLink && (
                                                <a
                                                    href={mempoolLink}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-gray-400 hover:text-blue-600 transition-colors"
                                                    title="View on Mempool.space"
                                                >
                                                    <ExternalLink className="w-4 h-4" />
                                                </a>
                                            )}
                                            {assetType === 'RUNE' && tx.tx_id && (
                                                <a
                                                    href={`https://unisat.io/tx/${tx.tx_id}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-gray-400 hover:text-orange-600 transition-colors"
                                                    title="View on UniSat"
                                                >
                                                    <ExternalLink className="w-4 h-4" />
                                                </a>
                                            )}
                                            {assetType === 'ORDINAL' && tx.tx_id && (
                                                <a
                                                    href={`https://ordiscan.com/tx/${tx.tx_id}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-gray-400 hover:text-purple-600 transition-colors"
                                                    title="View on Ordiscan"
                                                >
                                                    <ExternalLink className="w-4 h-4" />
                                                </a>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Recommended Actions */}
                    <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-2">📋 Recommended Actions:</h4>
                        <div className="space-y-3">
                            {suggestion.recommended_actions.map((action, actionIdx) => (
                                <div key={actionIdx} className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
                                    <div className="flex items-start gap-2">
                                        <span className="font-bold text-blue-700 text-sm">{actionIdx + 1}.</span>
                                        <div className="flex-1">
                                            <div className="font-semibold text-blue-900 mb-1">
                                                {action.action_type.replace(/_/g, ' ')}
                                            </div>

                                            {action.transaction && (
                                                <div className="text-xs text-gray-600 mb-2 flex items-center gap-2 flex-wrap">
                                                    <span>Transaction: {action.transaction.date} {action.transaction.time}</span>
                                                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${action.transaction.type === 'Withdrawal' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                                                        }`}>
                                                        {action.transaction.type}
                                                    </span>
                                                    {/* Asset Type Tag */}
                                                    {action.transaction.metadata?.asset_type && (
                                                        <span className={`px-2 py-0.5 rounded text-xs font-semibold border ${action.transaction.metadata.asset_type === 'ORDINAL' ? 'bg-purple-100 text-purple-700 border-purple-300' :
                                                            action.transaction.metadata.asset_type === 'RUNE' ? 'bg-orange-100 text-orange-700 border-orange-300' :
                                                                'bg-gray-100 text-gray-600 border-gray-300'
                                                            }`}>
                                                            {action.transaction.metadata.asset_type === 'ORDINAL' && '🎨 ORDINAL'}
                                                            {action.transaction.metadata.asset_type === 'RUNE' && '🔮 RUNE'}
                                                            {action.transaction.metadata.asset_type === 'BTC' && 'BTC'}
                                                        </span>
                                                    )}
                                                    <span>({action.transaction.amount} BTC)</span>
                                                </div>
                                            )}

                                            <div className="text-sm text-gray-700">{action.reason}</div>

                                            {/* Display note if present */}
                                            {action.note && (
                                                <div className="text-xs text-gray-600 mt-1 italic">{action.note}</div>
                                            )}

                                            {action.warning && (
                                                <div className="mt-2 bg-yellow-100 border border-yellow-300 rounded p-2 text-xs text-yellow-800">
                                                    {action.warning}
                                                </div>
                                            )}

                                            {action.action_type === 'CHANGE_TO_TRADE' && (
                                                <div className="mt-2">
                                                    <div className="text-xs space-y-1 mb-2">
                                                        <div>• Sent: {action.sent_amount} {action.sent_asset}</div>
                                                        <div>• Received: {action.received_asset} {action.received_quantity && `(×${action.received_quantity})`}</div>
                                                    </div>
                                                </div>
                                            )}

                                            {/* Ordinal Preview with Image and Link - Show for ALL action types */}
                                            {action.transaction && action.transaction.metadata?.asset_type === 'ORDINAL' && (
                                                <OrdinalPreview
                                                    transaction={action.transaction}
                                                />
                                            )}

                                            {/* Rune Preview - Show for ALL action types */}
                                            {action.transaction?.metadata?.rune_name && (
                                                <RunePreview
                                                    runeName={action.transaction.metadata.rune_name}
                                                    txId={action.transaction.tx_id}
                                                    metadata={action.transaction.metadata}
                                                />
                                            )}

                                            {/* Verification Links - Show for ALL action types */}
                                            <div className="mt-2 flex flex-wrap gap-2">
                                                {action.ordiscan_link && (
                                                    <a
                                                        href={action.ordiscan_link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm"
                                                    >
                                                        <ExternalLink className="w-3 h-3" />
                                                        Verify on Ordiscan
                                                    </a>
                                                )}

                                                {action.unisat_link && (
                                                    <a
                                                        href={action.unisat_link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 text-orange-600 hover:text-orange-800 text-sm"
                                                    >
                                                        <ExternalLink className="w-3 h-3" />
                                                        Verify on UniSat
                                                    </a>
                                                )}

                                                {action.hiro_link && (
                                                    <a
                                                        href={action.hiro_link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-orange-500/10 text-orange-400 hover:bg-orange-500/20 border border-orange-500/20 transition-all"
                                                    >
                                                        <ExternalLink className="w-3 h-3" />
                                                        Verify on Hiro
                                                    </a>
                                                )}

                                                {action.ordinals_link && (
                                                    <a
                                                        href={action.ordinals_link}
                                                        target="_blank"
                                                        rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 text-orange-600 hover:text-orange-800 text-sm"
                                                    >
                                                        <ExternalLink className="w-3 h-3" />
                                                        View Rune on Ordinals.com
                                                    </a>
                                                )}
                                            </div>

                                            {action.action_type === 'MERGE_AS_TRANSFER' && action.transactions && (
                                                <div className="mt-2 text-xs">
                                                    Merging {action.transactions.length} transactions into single non-taxable transfer
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            ))}

            {suggestions.length === 0 && (
                <div className="bg-white p-8 rounded-xl shadow-sm text-center">
                    <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-gray-800 mb-2">No Issues Found!</h3>
                    <p className="text-gray-600">
                        All transactions appear to be correctly classified. No tax corrections needed.
                    </p>
                </div>
            )}
        </div>
    );
};

export default CorrectionReport;
