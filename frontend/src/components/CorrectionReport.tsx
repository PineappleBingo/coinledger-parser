import React from 'react';
import { AlertTriangle, CheckCircle, Info, ExternalLink, AlertCircle } from 'lucide-react';

interface Transaction {
    date: string;
    time: string;
    type: string;
    amount: number;
    asset: string;
    tx_id: string;
    source: string;
}

interface RecommendedAction {
    action_type: string;
    reason: string;
    warning?: string;
    transaction?: Transaction;
    transactions?: Transaction[];
    sent_asset?: string;
    sent_amount?: string | number;
    received_asset?: string;
    received_quantity?: number;
    ordiscan_link?: string;
    requires_ordiscan?: boolean;
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
}

const CorrectionReport: React.FC<CorrectionReportProps> = ({ suggestions, summary }) => {
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
            'SELF_TRANSFER': '🔄 Self Transfer Pattern'
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
                            {suggestion.affected_transactions.map((tx, txIdx) => (
                                <div key={txIdx} className="flex items-center justify-between text-sm border-b border-gray-200 last:border-0 pb-2 last:pb-0">
                                    <div className="flex items-center gap-2">
                                        <span className="font-mono text-xs text-gray-500">{tx.date} {tx.time}</span>
                                        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${tx.type === 'Withdrawal' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                                            }`}>
                                            {tx.type}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="font-semibold">{tx.amount > 0 ? '+' : ''}{tx.amount} {tx.asset}</span>
                                        <span className="text-xs text-gray-400">({tx.source})</span>
                                    </div>
                                </div>
                            ))}
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
                                                <div className="text-xs text-gray-600 mb-2">
                                                    Transaction: {action.transaction.date} {action.transaction.time} - {action.transaction.type} ({action.transaction.amount} BTC)
                                                </div>
                                            )}

                                            <div className="text-sm text-gray-700">{action.reason}</div>

                                            {action.warning && (
                                                <div className="mt-2 bg-yellow-100 border border-yellow-300 rounded p-2 text-xs text-yellow-800">
                                                    {action.warning}
                                                </div>
                                            )}

                                            {action.action_type === 'CHANGE_TO_TRADE' && (
                                                <div className="mt-2 text-xs space-y-1">
                                                    <div>• Sent: {action.sent_amount} {action.sent_asset}</div>
                                                    <div>• Received: {action.received_asset} {action.received_quantity && `(×${action.received_quantity})`}</div>
                                                    {action.ordiscan_link && (
                                                        <a
                                                            href={action.ordiscan_link}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 mt-2"
                                                        >
                                                            <ExternalLink className="w-3 h-3" />
                                                            Verify on Ordiscan
                                                        </a>
                                                    )}
                                                </div>
                                            )}

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
