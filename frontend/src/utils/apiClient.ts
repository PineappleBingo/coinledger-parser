// API utility for fetching Ordinals and Runes metadata
// Implements automatic fallback: UniSat (primary) → Hiro (fallback)
// ⚠️ Hiro sunsetting March 2026 — Rate limit: 900 requests/minute

export interface OrdinalInfo {
    inscription_id: string;
    inscription_number: number;
    content_type: string;
    content_url: string;
    name?: string;
    collection?: string;
}

export interface RuneInfo {
    rune_name: string;
    ticker: string;
    amount: string;
    divisibility: number;
    content_url?: string;
    content_type?: string;
    collection?: string;
}

// Track which APIs are currently rate-limited
const rateLimitedAPIs = new Set<string>();

// Reset rate limit tracking after 1 minute
const resetRateLimit = (apiName: string) => {
    setTimeout(() => {
        rateLimitedAPIs.delete(apiName);
        console.log(`[API] ${apiName} rate limit reset`);
    }, 60000);
};

/**
 * Fetch Ordinal inscription metadata with automatic API fallback
 * Tries: UniSat → Hiro
 */
export const fetchOrdinalInfo = async (inscriptionId: string): Promise<OrdinalInfo | null> => {
    // Try UniSat API first (primary)
    if (!rateLimitedAPIs.has('unisat')) {
        try {
            const response = await fetch(
                `https://open-api.unisat.io/v1/indexer/inscription/info/${inscriptionId}`
            );

            if (response.status === 429) {
                console.warn('[API] UniSat rate limit reached, switching to Hiro');
                rateLimitedAPIs.add('unisat');
                resetRateLimit('unisat');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] UniSat success:', inscriptionId);

                return {
                    inscription_id: data.data.inscriptionId || inscriptionId,
                    inscription_number: data.data.inscriptionNumber || 0,
                    content_type: data.data.contentType || 'unknown',
                    content_url: data.data.contentUrl || `https://ordinals.com/content/${inscriptionId}`,
                    name: data.data.meta?.name,
                    collection: data.data.meta?.collection
                };
            }
        } catch (error) {
            console.error('[API] UniSat error:', error);
        }
    }

    // Try Hiro API as fallback (sunsetting March 2026, 900 req/min)
    if (!rateLimitedAPIs.has('hiro')) {
        try {
            const response = await fetch(
                `https://api.hiro.so/ordinals/v1/inscriptions/${inscriptionId}`
            );

            if (response.status === 429) {
                console.warn('[API] Hiro rate limit reached');
                rateLimitedAPIs.add('hiro');
                resetRateLimit('hiro');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] Hiro success:', inscriptionId);

                return {
                    inscription_id: data.id || inscriptionId,
                    inscription_number: data.number || 0,
                    content_type: data.content_type || 'unknown',
                    content_url: data.content_url || `https://ordinals.com/content/${inscriptionId}`,
                    name: data.meta?.name,
                    collection: data.meta?.collection_name
                };
            }
        } catch (error) {
            console.error('[API] Hiro error:', error);
        }
    }

    console.error('[API] All APIs failed or rate-limited for inscription:', inscriptionId);
    return null;
};

/**
 * Fetch Rune metadata with automatic API fallback
 * Tries: UniSat → Hiro
 */
export const fetchRuneInfo = async (txId: string, runeName?: string): Promise<RuneInfo[]> => {
    // Try UniSat API first (primary)
    if (!rateLimitedAPIs.has('unisat-runes')) {
        try {
            const response = await fetch(
                `https://open-api.unisat.io/v1/indexer/tx/${txId}`
            );

            if (response.status === 429) {
                console.warn('[API] UniSat Runes rate limit reached, switching to Hiro');
                rateLimitedAPIs.add('unisat-runes');
                resetRateLimit('unisat-runes');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] UniSat Runes success:', txId);

                if (data.code === 0 && data.data) {
                    const tx_data = data.data;
                    const runes: RuneInfo[] = [];
                    const foundNames = new Set<string>();

                    if (tx_data.vout) {
                        for (const vout of tx_data.vout) {
                            if (vout.runes) {
                                for (const r of vout.runes) {
                                    const name = r.runeName || r.name || r.symbol || runeName || 'Unknown Rune';
                                    if (!foundNames.has(name)) {
                                        foundNames.add(name);
                                        runes.push({
                                            rune_name: name,
                                            ticker: r.symbol || name || 'RUNE',
                                            amount: r.amount || '0',
                                            divisibility: parseInt(r.divisibility) || 0
                                        });
                                    }
                                }
                            }
                        }
                    }
                    if (runes.length > 0) return runes;
                }
            }
        } catch (error) {
            console.error('[API] UniSat Runes error:', error);
        }
    }

    // Try Hiro API as fallback (sunsetting March 2026, 900 req/min)
    if (!rateLimitedAPIs.has('hiro-runes')) {
        try {
            // Hiro Runes activity endpoint by tx
            const response = await fetch(
                `https://api.hiro.so/runes/v1/transactions/${txId}/activity`
            );

            if (response.status === 429) {
                console.warn('[API] Hiro Runes rate limit reached');
                rateLimitedAPIs.add('hiro-runes');
                resetRateLimit('hiro-runes');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] Hiro Runes success:', txId);

                const results = data.results || [];
                if (results.length > 0) {
                    const runes: RuneInfo[] = [];
                    const foundRunes = new Set<string>();

                    for (const item of results) {
                        const name = item.rune?.spaced_name || item.rune?.name || runeName || 'Unknown Rune';
                        if (!foundRunes.has(name)) {
                            foundRunes.add(name);
                            runes.push({
                                rune_name: name,
                                ticker: item.rune?.symbol || name || 'RUNE',
                                amount: item.amount || '0',
                                divisibility: item.rune?.divisibility || 0
                            });
                        }
                    }
                    if (runes.length > 0) return runes;
                }
            }
        } catch (error) {
            console.error('[API] Hiro Runes error:', error);
        }
    }

    // Fallback to metadata if all APIs fail
    if (runeName) {
        console.warn('[API] All Rune APIs failed, using metadata fallback');
        return [{
            rune_name: runeName,
            ticker: runeName,
            amount: 'Unknown',
            divisibility: 0
        }];
    }

    console.error('[API] All Rune APIs failed for tx:', txId);
    return [];
};

/**
 * Format Rune amount with proper decimals
 */
export const formatRuneAmount = (amount: string, divisibility: number): string => {
    try {
        const amountNum = BigInt(amount);
        const divisor = BigInt(10 ** divisibility);
        const integerPart = amountNum / divisor;
        const fractionalPart = amountNum % divisor;

        if (fractionalPart === BigInt(0)) {
            return integerPart.toString();
        }

        const fractionalStr = fractionalPart.toString().padStart(divisibility, '0');
        return `${integerPart}.${fractionalStr}`;
    } catch (error) {
        return amount;
    }
};
