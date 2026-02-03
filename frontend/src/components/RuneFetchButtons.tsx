import React, { useState } from 'react';
import { RefreshCw } from 'lucide-react';

interface RuneFetchButtonsProps {
    txId: string;
    onRuneFetched: (runes: Array<{ name: string; amount: string; divisibility: number }>, source: string) => void;
}

export const RuneFetchButtons: React.FC<RuneFetchButtonsProps> = ({ txId, onRuneFetched }) => {
    const [loading, setLoading] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const fetchRuneInfo = async () => {
        const apiSource = 'unisat';
        setLoading(apiSource);
        setError(null);

        try {
            const response = await fetch('http://localhost:8000/api/fetch-rune-info', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tx_id: txId,
                    api_source: apiSource
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to fetch Rune info');
            }

            const data = await response.json();

            if (data.success) {
                // Check for detailed runes list first
                if (data.runes && Array.isArray(data.runes)) {
                    onRuneFetched(data.runes, data.source);
                } else if (data.rune_name) {
                    // Fallback for single rune response
                    onRuneFetched([{
                        name: data.rune_name,
                        amount: data.rune_amount || '0',
                        divisibility: 0
                    }], data.source);
                } else {
                    throw new Error('No Rune data found');
                }
            } else {
                throw new Error('No Rune data found');
            }
        } catch (err: any) {
            setError(err.message);
            console.error(`Error fetching from ${apiSource}:`, err);
        } finally {
            setLoading(null);
        }
    };

    return (
        <div className="mt-2 space-y-2">
            <div className="text-xs text-gray-600">
                Data missing? Fetch details:
            </div>
            <div className="flex gap-2">
                <button
                    onClick={fetchRuneInfo}
                    disabled={loading !== null}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-white bg-orange-600 hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded transition-colors"
                >
                    {loading === 'unisat' ? (
                        <>
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            Fetching...
                        </>
                    ) : (
                        <>
                            <RefreshCw className="w-3 h-3" />
                            Fetch from UniSat
                        </>
                    )}
                </button>
            </div>

            {error && (
                <div className="text-xs text-red-600 mt-1">
                    ⚠️ {error}
                </div>
            )}
        </div>
    );
};
