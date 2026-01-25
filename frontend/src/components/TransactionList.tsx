import React from 'react';

interface Transaction {
    timestamp: string;
    asset: string;
    amount: number;
    tx_id: string;
}

interface Props {
    title: string;
    transactions: Transaction[];
    colorClass: string;
}

const TransactionList: React.FC<Props> = ({ title, transactions, colorClass }) => {
    return (
        <div className="bg-white p-6 rounded-xl shadow-sm h-full flex flex-col">
            <h3 className={`text-xl font-bold mb-4 ${colorClass}`}>{title} ({transactions.length})</h3>
            <div className="overflow-auto flex-1 max-h-[500px] border rounded-lg">
                <table className="min-w-full divide-y divide-gray-200 relative">
                    <thead className="bg-gray-50 sticky top-0">
                        <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">TxID</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {transactions.map((tx, idx) => (
                            <tr key={idx} className="hover:bg-gray-50">
                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{tx.timestamp}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{tx.asset}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">{tx.amount}</td>
                                <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500 font-mono" title={tx.tx_id}>
                                    {tx.tx_id ? `${tx.tx_id.slice(0, 8)}...` : '-'}
                                </td>
                            </tr>
                        ))}
                        {transactions.length === 0 && (
                            <tr>
                                <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
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
