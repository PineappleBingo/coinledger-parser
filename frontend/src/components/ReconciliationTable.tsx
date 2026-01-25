import React from 'react';
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

interface Transaction {
    timestamp: string;
    asset: string;
    amount: number;
    tx_id: string;
}

interface MatchResult {
    source_a: Transaction;
    source_b: Transaction | null;
    confidence: number;
    match_type: string;
    issue?: string;
}

interface Props {
    matched: MatchResult[];
    conflicts: MatchResult[];
    missing: MatchResult[];
}

const ReconciliationTable: React.FC<Props> = ({ matched, conflicts, missing }) => {
    return (
        <div className="flex flex-col gap-8">
            {/* Matched Section */}
            <section>
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2 text-green-700">
                    <CheckCircle className="w-6 h-6" /> Matched Transactions ({matched.length})
                </h3>
                <div className="overflow-x-auto border rounded-lg shadow-sm">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TxID</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {matched.map((row, idx) => (
                                <tr key={idx} className="hover:bg-green-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.source_a.timestamp}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.source_a.asset}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.source_a.amount}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">{row.source_a.tx_id.slice(0, 10)}...</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">{(row.confidence * 100).toFixed(1)}%</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* Conflicts Section */}
            <section>
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2 text-red-700">
                    <XCircle className="w-6 h-6" /> Conflicts ({conflicts.length})
                </h3>
                <div className="overflow-x-auto border rounded-lg shadow-sm">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CEX Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CEX Amount</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Chain Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Chain Amount</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Issue</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {conflicts.map((row, idx) => (
                                <tr key={idx} className="hover:bg-red-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.source_a.timestamp}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.source_a.amount} {row.source_a.asset}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.source_b?.timestamp || '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row.source_b ? `${row.source_b.amount} ${row.source_b.asset}` : '-'}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600 font-medium">{row.issue}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>

            {/* Missing Section */}
            <section>
                <h3 className="text-xl font-bold mb-4 flex items-center gap-2 text-yellow-700">
                    <AlertTriangle className="w-6 h-6" /> Missing in CEX ({missing.length})
                </h3>
                <div className="overflow-x-auto border rounded-lg shadow-sm">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TxID</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {missing.map((row: any, idx) => (
                                <tr key={idx} className="hover:bg-yellow-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.timestamp}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.asset}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{row.amount}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono">{row.tx_id}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    );
};

export default ReconciliationTable;
