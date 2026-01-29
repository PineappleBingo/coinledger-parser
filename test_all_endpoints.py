#!/usr/bin/env python3
"""
Comprehensive endpoint testing script
Tests all API endpoints to verify functionality
"""
import requests
import sys
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test if server is responding"""
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Server health check: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Server not responding: {e}")
        return False

def test_upload():
    """Test file upload endpoint"""
    print("\n📤 Testing Upload Endpoint...")
    try:
        # Create test CSV
        test_csv = """Date,Time,Type,Account,Amount,Currency
2025-01-15,10:30:00,Deposit,Wallet1,0.001,BTC
2025-01-16,14:20:00,Withdrawal,Wallet1,-0.0005,BTC
2025-01-17,09:15:00,Deposit,Wallet1,0.00000546,BTC
"""
        
        files = {'file': ('test.csv', test_csv, 'text/csv')}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Upload successful!")
            print(f"   Count: {data.get('count')}")
            print(f"   Data rows: {len(data.get('data', []))}")
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Upload error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fetch_blockchain():
    """Test blockchain data fetch endpoint"""
    print("\n🔗 Testing Fetch Blockchain Endpoint...")
    try:
        payload = {
            "wallet_address": "bc1pf3n2ka7tpwv4tc4yzflclspjgq9yjvhek6cjnd4x2lzdd7k5lqfs327cql",
            "chain": "bitcoin",
            "from_date": "2025-01-01",
            "to_date": "2025-12-31"
        }
        
        response = requests.post(f"{BASE_URL}/api/fetch-blockchain", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Fetch successful!")
            print(f"   Count: {data.get('count')}")
            return True
        else:
            print(f"❌ Fetch failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Fetch error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyze():
    """Test analysis endpoint"""
    print("\n🔍 Testing Analyze Endpoint...")
    try:
        response = requests.post(f"{BASE_URL}/api/analyze")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Analyze successful!")
            print(f"   Status: {data.get('status')}")
            print(f"   Suggestions: {len(data.get('correction_suggestions', []))}")
            print(f"   Summary: {data.get('summary')}")
            return True
        else:
            print(f"❌ Analyze failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Analyze error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("🧪 API Endpoint Testing Suite")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Health check
    results['health'] = test_health()
    
    if not results['health']:
        print("\n❌ Server not running. Cannot proceed with tests.")
        sys.exit(1)
    
    # Test 2: Upload
    results['upload'] = test_upload()
    
    # Test 3: Fetch blockchain
    results['fetch'] = test_fetch_blockchain()
    
    # Test 4: Analyze (requires upload and fetch to have run)
    if results['upload'] and results['fetch']:
        results['analyze'] = test_analyze()
    else:
        print("\n⚠️  Skipping analyze test (requires upload and fetch)")
        results['analyze'] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test.upper():20s} {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
