// API utility for fetching Ordinals and Runes metadata
// Implements automatic fallback between UniSat, OKLink, and Hiro APIs

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
 * Tries: UniSat → Hiro → OKLink
 */
export const fetchOrdinalInfo = async (inscriptionId: string): Promise<OrdinalInfo | null> => {
    // Try UniSat API first
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

    // Try Hiro API as fallback
    if (!rateLimitedAPIs.has('hiro')) {
        try {
            const response = await fetch(
                `https://api.hiro.so/ordinals/v1/inscriptions/${inscriptionId}`
            );

            if (response.status === 429) {
                console.warn('[API] Hiro rate limit reached, switching to OKLink');
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

    // Try OKLink API as last resort
    if (!rateLimitedAPIs.has('oklink')) {
        try {
            // OKLink uses inscription number, try to extract from ID
            const response = await fetch(
                `https://www.oklink.com/api/v5/explorer/btc/inscriptions-list?inscriptionId=${inscriptionId}`
            );

            if (response.status === 429) {
                console.warn('[API] OKLink rate limit reached');
                rateLimitedAPIs.add('oklink');
                resetRateLimit('oklink');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] OKLink success:', inscriptionId);

                if (data.data && data.data.length > 0) {
                    const inscription = data.data[0];
                    return {
                        inscription_id: inscription.inscriptionId || inscriptionId,
                        inscription_number: parseInt(inscription.inscriptionNumber) || 0,
                        content_type: inscription.contentType || 'unknown',
                        content_url: `https://ordinals.com/content/${inscriptionId}`,
                        name: inscription.name
                    };
                }
            }
        } catch (error) {
            console.error('[API] OKLink error:', error);
        }
    }

    console.error('[API] All APIs failed or rate-limited for inscription:', inscriptionId);
    return null;
};

/**
 * Fetch Rune metadata with automatic API fallback
 * Tries: OKLink → Hiro → UniSat
 */
export const fetchRuneInfo = async (txId: string, runeName?: string): Promise<RuneInfo | null> => {
    // Try OKLink API first (best for Runes)
    if (!rateLimitedAPIs.has('oklink-runes')) {
        try {
            const response = await fetch(
                `https://www.oklink.com/api/v5/explorer/btc/runes-transaction-list?txId=${txId}`
            );

            if (response.status === 429) {
                console.warn('[API] OKLink Runes rate limit reached, switching to Hiro');
                rateLimitedAPIs.add('oklink-runes');
                resetRateLimit('oklink-runes');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] OKLink Runes success:', txId);

                if (data.data && data.data.length > 0) {
                    const rune = data.data[0];
                    return {
                        rune_name: rune.runeName || runeName || 'Unknown Rune',
                        ticker: rune.runeSymbol || rune.runeName || 'RUNE',
                        amount: rune.amount || '0',
                        divisibility: parseInt(rune.divisibility) || 0
                    };
                }
            }
        } catch (error) {
            console.error('[API] OKLink Runes error:', error);
        }
    }

    // Try Hiro API as fallback
    if (!rateLimitedAPIs.has('hiro-runes')) {
        try {
            const response = await fetch(
                `https://api.hiro.so/runes/v1/etchings/${runeName || 'UNCOMMON•GOODS'}`
            );

            if (response.status === 429) {
                console.warn('[API] Hiro Runes rate limit reached');
                rateLimitedAPIs.add('hiro-runes');
                resetRateLimit('hiro-runes');
            } else if (response.ok) {
                const data = await response.json();
                console.log('[API] Hiro Runes success:', runeName);

                return {
                    rune_name: data.name || runeName || 'Unknown Rune',
                    ticker: data.symbol || data.name || 'RUNE',
                    amount: data.total_mints || '0',
                    divisibility: data.divisibility || 0
                };
            }
        } catch (error) {
            console.error('[API] Hiro Runes error:', error);
        }
    }

    // Fallback to metadata if all APIs fail
    if (runeName) {
        console.warn('[API] All Rune APIs failed, using metadata fallback');
        return {
            rune_name: runeName,
            ticker: runeName,
            amount: 'Unknown',
            divisibility: 0
        };
    }

    console.error('[API] All Rune APIs failed for tx:', txId);
    return null;
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
