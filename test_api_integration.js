#!/usr/bin/env node

/**
 * Test script for API integration
 * Tests UniSat, OKLink, and Hiro APIs for Ordinals and Runes metadata
 */

// Test Ordinal inscription
const testInscriptionId = 'e2514b92a9734e800555febf81e815b057214d489079bce35151cbbf0d11c9bbi0';

// Test Rune transaction
const testRuneTxId = '66c9b1a69e1c2fc09c865c106ef2151c8a1e7e4f9b8a7d6c5e4f3a2b1c0d9e8f';
const testRuneName = 'UNCOMMON•GOODS';

console.log('🧪 Testing API Integration\n');
console.log('='.repeat(80));

// Test 1: UniSat Ordinals API
console.log('\n📍 Test 1: UniSat Ordinals API');
console.log(`Fetching inscription: ${testInscriptionId.substring(0, 20)}...`);

fetch(`https://open-api.unisat.io/v1/indexer/inscription/info/${testInscriptionId}`)
    .then(res => {
        console.log(`Status: ${res.status} ${res.statusText}`);
        if (res.status === 429) {
            console.log('⚠️  Rate limit reached - this is expected for free tier');
            return null;
        }
        return res.json();
    })
    .then(data => {
        if (data) {
            console.log('✅ UniSat API Response:');
            console.log(JSON.stringify(data, null, 2).substring(0, 500));
        }
    })
    .catch(err => console.error('❌ UniSat Error:', err.message));

// Test 2: Hiro Ordinals API
setTimeout(() => {
    console.log('\n📍 Test 2: Hiro Ordinals API');
    console.log(`Fetching inscription: ${testInscriptionId.substring(0, 20)}...`);

    fetch(`https://api.hiro.so/ordinals/v1/inscriptions/${testInscriptionId}`)
        .then(res => {
            console.log(`Status: ${res.status} ${res.statusText}`);
            if (res.status === 429) {
                console.log('⚠️  Rate limit reached - this is expected for free tier');
                return null;
            }
            return res.json();
        })
        .then(data => {
            if (data) {
                console.log('✅ Hiro API Response:');
                console.log(JSON.stringify(data, null, 2).substring(0, 500));
            }
        })
        .catch(err => console.error('❌ Hiro Error:', err.message));
}, 1000);

// Test 3: OKLink Runes API
setTimeout(() => {
    console.log('\n📍 Test 3: OKLink Runes API');
    console.log(`Fetching rune tx: ${testRuneTxId.substring(0, 20)}...`);

    fetch(`https://www.oklink.com/api/v5/explorer/btc/runes-transaction-list?txId=${testRuneTxId}`)
        .then(res => {
            console.log(`Status: ${res.status} ${res.statusText}`);
            if (res.status === 429) {
                console.log('⚠️  Rate limit reached - this is expected for free tier');
                return null;
            }
            return res.json();
        })
        .then(data => {
            if (data) {
                console.log('✅ OKLink API Response:');
                console.log(JSON.stringify(data, null, 2).substring(0, 500));
            }
        })
        .catch(err => console.error('❌ OKLink Error:', err.message));
}, 2000);

// Test 4: Hiro Runes API
setTimeout(() => {
    console.log('\n📍 Test 4: Hiro Runes API');
    console.log(`Fetching rune: ${testRuneName}`);

    fetch(`https://api.hiro.so/runes/v1/etchings/${testRuneName}`)
        .then(res => {
            console.log(`Status: ${res.status} ${res.statusText}`);
            if (res.status === 429) {
                console.log('⚠️  Rate limit reached - this is expected for free tier');
                return null;
            }
            return res.json();
        })
        .then(data => {
            if (data) {
                console.log('✅ Hiro Runes API Response:');
                console.log(JSON.stringify(data, null, 2).substring(0, 500));
            }
        })
        .catch(err => console.error('❌ Hiro Runes Error:', err.message));

    setTimeout(() => {
        console.log('\n' + '='.repeat(80));
        console.log('\n✅ API Integration Test Complete');
        console.log('\n📝 Summary:');
        console.log('- UniSat: Ordinals metadata (image, name, inscription #)');
        console.log('- Hiro: Ordinals + Runes metadata (fallback)');
        console.log('- OKLink: Runes transaction data (ticker, amount)');
        console.log('\n💡 The frontend will automatically fallback between APIs when rate limits are hit.');
    }, 1000);
}, 3000);
