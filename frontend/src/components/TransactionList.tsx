import React from 'react';

interface Props {
    title: string;
    transactions: any[];
    colorClass: string;
}

const TransactionList: React.FC<Props> = ({ title, transactions, colorClass }) => {
    // Get all unique column names from the data
    const columns = transactions.length > 0 ? Object.keys(transactions[0]) : [];

    const formatCellValue = (col: string, value: any) => {
        // Handle null/undefined/empty
        if (value === null || value === undefined || value === '') {
            return '-';
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
                                    const displayValue = formatCellValue(col, value);

                                    // If it's a React element (like our badge), render it directly
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
