import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, ExternalLink, Search, Download, HelpCircle } from 'lucide-react';
import axios from 'axios';

interface Props {
    transactions: any[];
    searchQuery: string;
    selectedTxId?: string | null;
    onRowClick?: (txId: string) => void;
    onRuneFetched?: (txId: string, runeData: any) => void;
    showUSD?: boolean;
    btcPrice?: number | null;
    walletAddresses?: string[];
    runeOverrides?: Record<string, any>;
    classificationOverrides?: Record<string, string>;
    onClassificationOverride?: (txId: string, type: string) => void;
}

const ReviewPanelA: React.FC<Props> = ({ transactions, searchQuery, selectedTxId, onRowClick, onRuneFetched, showUSD, btcPrice, walletAddresses = [], runeOverrides = {}, classificationOverrides = {}, onClassificationOverride }) => {
    const formatUSD = (btcAmount: number) => {
        if (!showUSD || !btcPrice) return '';
        const usd = Math.abs(btcAmount) * btcPrice;
        return ` ($${usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })})`;
    };
    const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
    const [runeInfo, setRuneInfo] = useState<Record<string, any>>({});
    const [loadingRune, setLoadingRune] = useState<Record<string, boolean>>({});

    const toggleExpand = (idx: number) => {
        setExpandedIds(prev => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else next.add(idx);
            return next;
        });
    };

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

    const fetchRuneOrOrdinalInfo = async (txId: string) => {
        if (!txId || runeInfo[txId]) return;
        setLoadingRune(prev => ({ ...prev, [txId]: true }));
        try {
            const res = await axios.post('http://localhost:8000/api/fetch-rune-info', {
                tx_id: txId,
                wallet_addresses: walletAddresses
            });
            if (res.data.success === false) {
                // Not found on any API — show info message, not error
                setRuneInfo(prev => ({ ...prev, [txId]: { not_found: true, message: res.data.message || 'No data found' } }));
            } else {
                setRuneInfo(prev => ({ ...prev, [txId]: res.data }));
                if (onRuneFetched && res.data && !res.data.error) {
                    onRuneFetched(txId, res.data);
                }
            }
        } catch (err: any) {
            const detail = err.response?.data?.detail;
            // detail could be a string OR an array of Pydantic validation errors
            const errorMsg = typeof detail === 'string' ? detail
                : Array.isArray(detail) ? detail.map((d: any) => d.msg || JSON.stringify(d)).join('; ')
                    : 'Failed to fetch';
            setRuneInfo(prev => ({ ...prev, [txId]: { error: errorMsg } }));
        } finally {
            setLoadingRune(prev => ({ ...prev, [txId]: false }));
        }
    };

    // Filter transactions
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

    const getTypeBadge = (tx: any) => {
        let type = classificationOverrides[tx.tx_id || ''] || tx.coinledger_type || tx.tx_type || 'Unknown';

        // Bug 11 Fix: Visually label all components of a MINT as 'Mint' in Panel A, 
        // even if they are fundamentally 'Ignored' dust deposits for tax purposes.
        if (!classificationOverrides[tx.tx_id || ''] && (tx.pattern === 'MINT_BUY' || tx.pattern === 'BULK_MINT')) {
            type = 'Mint';
        }

        const config: Record<string, { bg: string; text: string }> = {
            'Trade': { bg: 'bg-blue-500/20', text: 'text-blue-400' },
            'Deposit': { bg: 'bg-green-500/20', text: 'text-green-400' },
            'Withdrawal': { bg: 'bg-red-500/20', text: 'text-red-400' },
            'Ignored': { bg: 'bg-gray-500/20', text: 'text-gray-400' },
            'Income': { bg: 'bg-emerald-500/20', text: 'text-emerald-400' },
            'Investment Loss': { bg: 'bg-orange-500/20', text: 'text-orange-400' },
            'Airdrop': { bg: 'bg-cyan-500/20', text: 'text-cyan-400' },
            'Mint': { bg: 'bg-purple-500/20', text: 'text-purple-400' },
        };
        const c = config[type] || { bg: 'bg-gray-500/20', text: 'text-gray-400' };
        return <span className={`px-2 py-0.5 rounded text-xs font-bold ${c.bg} ${c.text}`}>{type}</span>;
    };

    const getPatternEmoji = (pattern: string | null) => {
        if (!pattern) return '';
        const map: Record<string, string> = {
            'MINT_BUY': '🎨', 'BULK_MINT': '🎨✨', 'GAS_FEE': '⛽', 'SALE': '💰',
            'SELF_TRANSFER': '🔄', 'FIAT_ONRAMP': '💵', 'RUNE_RECEIVE': '🔮',
            'MAGIC_EDEN_BUY': '🪄', 'MAGIC_EDEN_BUY_ISOLATED': '🪄', 'MAGIC_EDEN_SALE': '🪄💰', 'NFT_TRADE': '🏪',
        };
        return map[pattern] || '🏷️';
    };

    // Expanded detection: any tx that could be an Ordinal/Rune (buy, sell, receive, trade)
    const isOrdinalOrRune = (tx: any) => {
        const meta = tx.metadata;
        const assetType = meta && typeof meta === 'object' ? (meta.asset_type || '') : '';
        if (assetType === 'ORDINAL' || assetType === 'RUNE') return true;
        // Any pattern that involves NFT/Rune trading
        const nftPatterns = ['MINT_BUY', 'BULK_MINT', 'RUNE_RECEIVE', 'SALE', 'MAGIC_EDEN_BUY', 'MAGIC_EDEN_BUY_ISOLATED', 'MAGIC_EDEN_SALE', 'NFT_TRADE'];
        if (tx.pattern && nftPatterns.includes(tx.pattern)) return true;
        // Description-based detection
        if (tx.description && /nft|rune|ordinal|sale|mint/i.test(tx.description)) return true;
        return false;
    };

    // Check if rune name is a raw placeholder like RUNE_a4b40e86
    const hasRawRuneName = (tx: any) => {
        const meta = tx.metadata;
        if (!meta || typeof meta !== 'object') return false;
        const name = meta.rune_name || '';
        return /^RUNE_[a-f0-9]+$/i.test(name);
    };

    const getDisplayRuneName = (tx: any) => {
        const txId = tx.tx_id || '';
        const info = runeOverrides[txId] || runeInfo[txId];
        // If we fetched real info, use that
        if (info && !info.error && info.runes?.length > 0) {
            return info.runes[0].name;
        }
        // Otherwise check metadata
        const meta = tx.metadata;
        if (meta && typeof meta === 'object' && meta.rune_name && !hasRawRuneName(tx)) {
            return meta.rune_name;
        }
        return null;
    };

    const formatDate = (ts: string) => {
        try {
            const d = new Date(ts);
            const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
            const dd = String(d.getUTCDate()).padStart(2, '0');
            const yyyy = d.getUTCFullYear();
            const hh = String(d.getUTCHours()).padStart(2, '0');
            const min = String(d.getUTCMinutes()).padStart(2, '0');
            const ss = String(d.getUTCSeconds()).padStart(2, '0');
            return `${mm}/${dd}/${yyyy} ${hh}:${min}:${ss} UTC`;
        } catch { return ts; }
    };

    const formatBTC = (amount: number) => {
        if (amount === 0) return '0';
        return amount < 0 ? `${amount.toFixed(8)}` : `+${amount.toFixed(8)}`;
    };

    const getAmountsData = (tx: any) => {
        const type = classificationOverrides[tx.tx_id || ''] || tx.coinledger_type || tx.tx_type || 'Unknown';
        const amount = Math.abs(tx.amount || 0);
        const asset = tx.asset || 'BTC';
        const runeName = getDisplayRuneName(tx);

        let sentAmount = '';
        let sentAsset = '';
        let receivedAmount = '';
        let receivedAsset = '';
        let isSentUsd = false;
        let isReceivedUsd = false;

        const isBuyingNFT = tx.amount < 0 || tx.pattern === 'MINT_BUY' || tx.pattern === 'BULK_MINT' || tx.pattern === 'MAGIC_EDEN_BUY' || tx.pattern === 'MAGIC_EDEN_BUY_ISOLATED';

        if (type === 'Trade' || type === 'Mint') {
            if (isBuyingNFT) {
                sentAsset = 'BTC';
                isSentUsd = true;

                // For marketplace/mint buys where deposit is primary, use total input value as purchase price
                const meta = tx.metadata && typeof tx.metadata === 'object' ? tx.metadata : {};
                if ((tx.pattern === 'MAGIC_EDEN_BUY_ISOLATED' || tx.pattern === 'MINT_BUY' || tx.pattern === 'BULK_MINT') && meta.total_input_value_btc) {
                    sentAmount = Number(meta.total_input_value_btc).toFixed(8);
                } else {
                    sentAmount = amount.toFixed(8);
                }

                if (runeName) {
                    receivedAsset = runeName;
                    const meta2 = tx.metadata && typeof tx.metadata === 'object' ? tx.metadata : {};
                    receivedAmount = meta2.rune_amount ? String(meta2.rune_amount) : '1';
                } else {
                    if (meta.asset_type === 'ORDINAL' || tx.pattern === 'MINT_BUY' || tx.pattern === 'BULK_MINT' || tx.pattern === 'MAGIC_EDEN_BUY' || tx.pattern === 'MAGIC_EDEN_BUY_ISOLATED') {
                        // Pattern indicates ordinal/NFT purchase
                        receivedAsset = 'Ordinal #';
                        receivedAmount = '1';
                    } else {
                        receivedAsset = 'BTC';
                        receivedAmount = amount.toFixed(8);
                        isReceivedUsd = true;
                    }
                }
            } else {
                if (runeName) {
                    sentAsset = runeName;
                    const meta = tx.metadata && typeof tx.metadata === 'object' ? tx.metadata : {};
                    sentAmount = meta.rune_amount ? String(meta.rune_amount) : '1';
                } else {
                    sentAsset = asset;
                    sentAmount = amount.toFixed(8);
                    isSentUsd = true;
                }
                receivedAsset = 'BTC';
                receivedAmount = amount.toFixed(8);
                isReceivedUsd = true;
            }
        } else if (type === 'Deposit' || type === 'Income' || type === 'Airdrop') {
            receivedAsset = asset;
            receivedAmount = amount.toFixed(8);
            isReceivedUsd = true;
        } else if (type === 'Withdrawal') {
            sentAsset = asset;
            sentAmount = amount.toFixed(8);
            isSentUsd = true;
        } else {
            if (tx.amount < 0) {
                sentAsset = asset;
                sentAmount = amount.toFixed(8);
                isSentUsd = true;
            } else {
                receivedAsset = asset;
                receivedAmount = amount.toFixed(8);
                isReceivedUsd = true;
            }
        }

        return { sentAmount, sentAsset, receivedAmount, receivedAsset, isSentUsd, isReceivedUsd, amountBTC: amount, rawAmount: tx.amount };
    };

    return (
        <div className="h-full flex flex-col">
            <h3 className="text-lg font-bold text-purple-400 mb-3 flex items-center gap-2">
                📋 Review Panel A — Transaction Details
                <span className="text-sm font-normal text-gray-500">({filtered.length})</span>
            </h3>
            <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[700px]">
                {filtered.map((tx, idx) => {
                    const isExpanded = expandedIds.has(idx);
                    const txId = tx.tx_id || '';
                    const isBlockchain = txId.length > 10;
                    const hasOrdRune = isOrdinalOrRune(tx);
                    const isSelected = selectedTxId && txId === selectedTxId;
                    // Unclassified: no pattern detected, blockchain tx, looks like a transfer
                    const isUnclassified = isBlockchain && !tx.pattern && tx.source === 'BLOCKCHAIN'
                        && tx.coinledger_type !== 'Ignored';

                    return (
                        <div key={idx}
                            className={`rounded-xl border overflow-hidden transition-all
                                ${isSelected
                                    ? 'border-purple-500 bg-purple-500/10 ring-1 ring-purple-500/30'
                                    : 'border-gray-700/50 bg-gray-900/50'}`}
                        >
                            {/* Card Header — always visible */}
                            <button
                                onClick={() => {
                                    toggleExpand(idx);
                                    if (onRowClick && txId) onRowClick(txId);
                                }}
                                className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-800/50 transition-colors text-left"
                            >
                                <div className="flex items-center gap-3">
                                    <span className="text-lg">{getPatternEmoji(tx.pattern)}</span>
                                    {getTypeBadge(tx)}
                                    {tx.pattern && (
                                        <span className="text-xs text-gray-500 font-mono">{tx.pattern}</span>
                                    )}
                                    {/* Show decoded rune name inline if available */}
                                    {getDisplayRuneName(tx) && (
                                        <span className="text-xs font-bold text-orange-400">🔮 {getDisplayRuneName(tx)}</span>
                                    )}
                                    {/* Unclassified transaction indicator */}
                                    {isUnclassified && (
                                        <span className="relative group">
                                            <HelpCircle className="w-4 h-4 text-yellow-500 cursor-help" />
                                            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs bg-gray-800 border border-yellow-500/30 text-yellow-300 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-50 pointer-events-none shadow-lg">
                                                ❓ Unclassified — the sending/receiving address may not be in your tracked wallets
                                            </span>
                                        </span>
                                    )}
                                </div>
                                <div className="flex items-center gap-4">
                                    <span className="text-xs text-gray-500">{formatDate(tx.timestamp)}</span>
                                    {isExpanded ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronRight className="w-4 h-4 text-gray-400" />}
                                </div>
                            </button>

                            {/* Collapsed preview line */}
                            {!isExpanded && (
                                <div className="px-4 pb-3 flex flex-wrap items-center gap-4 text-sm">
                                    {(() => {
                                        const { sentAmount, sentAsset, receivedAmount, receivedAsset, isSentUsd, isReceivedUsd, amountBTC } = getAmountsData(tx);
                                        return (
                                            <>
                                                {sentAmount && (
                                                    <span className="text-red-400">Sent: {sentAmount} {sentAsset}{isSentUsd ? formatUSD(-amountBTC) : ''}</span>
                                                )}
                                                {receivedAmount && (
                                                    <span className="text-green-400">Received: {receivedAmount} {receivedAsset}{isReceivedUsd ? formatUSD(amountBTC) : ''}</span>
                                                )}
                                            </>
                                        );
                                    })()}
                                    {tx.fee > 0 && <span className="text-gray-500 text-xs">Fee: {tx.fee.toFixed(8)} BTC{formatUSD(tx.fee)}</span>}
                                    {isBlockchain && (
                                        <span className="text-gray-600 font-mono text-xs ml-auto">{txId.slice(0, 8)}…{txId.slice(-6)}</span>
                                    )}
                                </div>
                            )}

                            {/* Expanded Details */}
                            {isExpanded && (
                                <div className="px-4 pb-4 space-y-3 border-t border-gray-800/50">
                                    {/* Amounts */}
                                    <div className="grid grid-cols-3 gap-4 pt-3 mb-3">
                                        {(() => {
                                            const { sentAmount, sentAsset, receivedAmount, receivedAsset, isSentUsd, isReceivedUsd, amountBTC } = getAmountsData(tx);
                                            return (
                                                <>
                                                    <div>
                                                        <span className="text-xs text-gray-500 block">Sent</span>
                                                        <span className={`font-semibold flex flex-col ${sentAmount ? 'text-red-400' : 'text-gray-500'}`}>
                                                            <span>{sentAmount ? `${sentAmount} ${sentAsset}` : '—'}</span>
                                                            {sentAmount && isSentUsd && <span className="text-gray-500 text-xs font-normal">{formatUSD(-amountBTC)}</span>}
                                                        </span>
                                                    </div>
                                                    <div>
                                                        <span className="text-xs text-gray-500 block">Received</span>
                                                        <span className={`font-semibold flex flex-col ${receivedAmount ? 'text-green-400' : 'text-gray-500'}`}>
                                                            <span>{receivedAmount ? `${receivedAmount} ${receivedAsset}` : '—'}</span>
                                                            {receivedAmount && isReceivedUsd && <span className="text-gray-500 text-xs font-normal">{formatUSD(amountBTC)}</span>}
                                                        </span>
                                                    </div>
                                                </>
                                            );
                                        })()}
                                        <div className="text-right">
                                            <span className="text-xs text-gray-500 block">Fee</span>
                                            <span className={`font-semibold flex flex-col items-end ${tx.fee > 0 ? 'text-yellow-400' : 'text-gray-500'}`}>
                                                <span>{tx.fee > 0 ? `${tx.fee.toFixed(8)} BTC` : '—'}</span>
                                                {tx.fee > 0 && <span className="text-gray-500 text-xs font-normal">{formatUSD(tx.fee)}</span>}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Description */}
                                    {tx.description && (
                                        <div className="text-sm text-gray-400">
                                            <span className="text-gray-600">Description: </span>{tx.description}
                                        </div>
                                    )}

                                    {/* Classification Override */}
                                    <div className="flex items-center justify-between text-sm py-2 px-3 bg-gray-800/20 rounded-lg border border-gray-700/30">
                                        <span className="text-gray-400 font-medium tracking-wide">Classification</span>
                                        <select
                                            value={classificationOverrides[tx.tx_id || ''] || tx.coinledger_type || tx.tx_type}
                                            onChange={(e) => onClassificationOverride && onClassificationOverride(tx.tx_id || '', e.target.value)}
                                            className="bg-gray-800 border border-gray-700 text-gray-200 text-xs rounded px-2 py-1.5 outline-none focus:ring-1 focus:ring-purple-500 cursor-pointer"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <option value="Deposit">Deposit</option>
                                            <option value="Withdrawal">Withdrawal</option>
                                            <option value="Trade">Trade</option>
                                            <option value="Income">Income</option>
                                            <option value="Airdrop">Airdrop</option>
                                            <option value="Mint">Mint</option>
                                            <option value="Ignored">Ignored</option>
                                            <option value="Investment Loss">Investment Loss</option>
                                        </select>
                                    </div>

                                    {/* Metadata — Asset Type Badge */}
                                    {tx.metadata && typeof tx.metadata === 'object' && tx.metadata.asset_type && tx.metadata.asset_type !== 'BTC' && (
                                        <div className="bg-gray-800/30 rounded-lg px-3 py-2 space-y-1">
                                            <div className="flex items-center gap-2">
                                                <span className="text-xs text-gray-500">Asset Type: </span>
                                                <span className={`text-sm font-bold ${tx.metadata.asset_type === 'ORDINAL' ? 'text-purple-400' : 'text-orange-400'}`}>
                                                    {tx.metadata.asset_type === 'ORDINAL' ? '🎨 ORDINAL' : '🔮 RUNE'}
                                                </span>
                                                {getDisplayRuneName(tx) && (
                                                    <span className="text-sm text-orange-300 font-semibold">{getDisplayRuneName(tx)}</span>
                                                )}
                                                {hasRawRuneName(tx) && !runeInfo[txId] && (
                                                    <span className="text-xs text-yellow-500">(undecoded — click fetch below)</span>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* TxHash + Verify Links */}
                                    {isBlockchain && (
                                        <div className="space-y-2">
                                            <div className="flex items-center gap-2 text-xs">
                                                <span className="text-gray-500">TxHash:</span>
                                                <span className="font-mono text-gray-300">{txId.slice(0, 16)}…{txId.slice(-8)}</span>
                                                <button onClick={(e) => { e.stopPropagation(); copyToClipboard(txId); }} className="text-gray-500 hover:text-gray-300" title="Copy">
                                                    <Copy className="w-3 h-3" />
                                                </button>
                                            </div>
                                            <div className="flex gap-2 flex-wrap">
                                                <a href={`https://mempool.space/tx/${txId}`} target="_blank" rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 border border-blue-500/20">
                                                    <ExternalLink className="w-3 h-3" /> Mempool
                                                </a>
                                                <a href={`https://www.blockchain.com/btc/tx/${txId}`} target="_blank" rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-green-500/10 text-green-400 hover:bg-green-500/20 border border-green-500/20">
                                                    <ExternalLink className="w-3 h-3" /> Blockchain.com
                                                </a>
                                                <a href={`https://ordiscan.com/tx/${txId}`} target="_blank" rel="noopener noreferrer"
                                                    className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 border border-purple-500/20">
                                                    <ExternalLink className="w-3 h-3" /> Ordiscan
                                                </a>
                                                {/* Ordinals.com link for NFT/Rune transactions */}
                                                {hasOrdRune && (
                                                    <a href={`https://ordinals.com/tx/${txId}`} target="_blank" rel="noopener noreferrer"
                                                        className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20">
                                                        <ExternalLink className="w-3 h-3" /> Ordinals.com
                                                    </a>
                                                )}
                                            </div>
                                        </div>
                                    )}

                                    {/* On-demand Ordinal/Rune fetch — shown for ALL NFT/Rune related txs */}
                                    {hasOrdRune && isBlockchain && (() => {
                                        const info = runeOverrides[txId] || runeInfo[txId];
                                        return (
                                            <div className="border-t border-gray-800/50 pt-3">
                                                {info ? (
                                                    info.not_found ? (
                                                        <div className="space-y-2">
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); fetchRuneOrOrdinalInfo(txId); }}
                                                                disabled={loadingRune[txId]}
                                                                className="w-full px-3 py-2 rounded-lg text-sm font-medium bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 border border-purple-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
                                                            >
                                                                {loadingRune[txId] ? (
                                                                    <><Search className="w-3.5 h-3.5 animate-spin" /> Fetching…</>
                                                                ) : (
                                                                    <><Download className="w-3.5 h-3.5" /> Fetch Ordinal / Rune Info</>
                                                                )}
                                                            </button>
                                                            <div className="bg-gray-500/10 border border-gray-500/20 rounded-lg p-3 text-sm text-gray-400">
                                                                ℹ️ {info.message || 'No data found'}
                                                            </div>
                                                        </div>
                                                    ) : info.error ? (
                                                        <div className="space-y-2">
                                                            <button
                                                                onClick={(e) => { e.stopPropagation(); fetchRuneOrOrdinalInfo(txId); }}
                                                                disabled={loadingRune[txId]}
                                                                className="w-full px-3 py-2 rounded-lg text-sm font-medium bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 border border-purple-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
                                                            >
                                                                {loadingRune[txId] ? (
                                                                    <><Search className="w-3.5 h-3.5 animate-spin" /> Fetching…</>
                                                                ) : (
                                                                    <><Download className="w-3.5 h-3.5" /> Fetch Ordinal / Rune Info</>
                                                                )}
                                                            </button>
                                                            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
                                                                <span className="text-red-400 text-sm">{info.error}</span>
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 space-y-1">
                                                            <div className="text-xs text-gray-500">Fetched from {info.source}</div>
                                                            {info.runes?.map((r: any, i: number) => (
                                                                <div key={i} className="flex items-center gap-2">
                                                                    {r.content_url && r.content_type?.includes('image') && (
                                                                        <img src={r.content_url} alt="ordinal" className="w-6 h-6 rounded object-cover bg-black/20" />
                                                                    )}
                                                                    <div className="flex flex-col flex-1 pl-1">
                                                                        <span className="text-orange-400 font-bold">{r.name}</span>
                                                                        {r.inscription_number && !r.name.includes(String(r.inscription_number)) && (
                                                                            <span className="text-xs text-gray-400">Inscription #{r.inscription_number}</span>
                                                                        )}
                                                                        {r.collection && <span className="text-xs text-gray-500 leading-tight">Collection: {r.collection}</span>}
                                                                        {r.inscription_number && (
                                                                            <a href={`https://ordiscan.com/inscription/${r.inscription_number}`} target="_blank" rel="noopener noreferrer"
                                                                                className="mt-1 inline-flex items-center gap-1 w-fit px-2 py-0.5 rounded text-[10px] bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 border border-purple-500/20">
                                                                                <ExternalLink className="w-2.5 h-2.5" /> Ordiscan Verify
                                                                            </a>
                                                                        )}
                                                                    </div>
                                                                    <span className="text-gray-300 ml-auto whitespace-nowrap text-sm">qty: {r.amount}</span>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    )
                                                ) : (
                                                    <button
                                                        onClick={(e) => { e.stopPropagation(); fetchRuneOrOrdinalInfo(txId); }}
                                                        disabled={loadingRune[txId]}
                                                        className="w-full px-3 py-2 rounded-lg text-sm font-medium bg-purple-500/10 text-purple-300 hover:bg-purple-500/20 border border-purple-500/20 flex items-center justify-center gap-2 disabled:opacity-50"
                                                    >
                                                        {loadingRune[txId] ? (
                                                            <><Search className="w-3.5 h-3.5 animate-spin" /> Fetching…</>
                                                        ) : (
                                                            <><Download className="w-3.5 h-3.5" /> Fetch Ordinal / Rune Info</>
                                                        )}
                                                    </button>
                                                )}
                                            </div>
                                        );
                                    })()}

                                    {/* Wallet info */}
                                    {tx.Wallet && (
                                        <div className="text-xs text-gray-600">
                                            Wallet: {tx.Wallet}
                                            {tx.WalletAddress && <span className="ml-2 font-mono">{tx.WalletAddress.slice(0, 12)}…</span>}
                                        </div>
                                    )}
                                </div>
                            )
                            }
                        </div>
                    );
                })}
                {filtered.length === 0 && (
                    <div className="text-center text-gray-500 py-12">No transactions match your search.</div>
                )}
            </div>
        </div >
    );
};

export default ReviewPanelA;
