from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import shutil
import os
import pandas as pd
from datetime import datetime

from src.ingest.mhtml_parser import extract_transactions_from_mhtml, normalize_mhtml_data
from src.ingest.csv_parser import smart_csv_load, normalize_csv_data
from src.reconciliation.blockchain import BlockchainClient
from src.reconciliation.engine import ReconciliationEngine
from src.reconciliation.anomaly import AnomalyDetector
from src.models import UnifiedTransaction

app = FastAPI(title="BitMatch API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (simple in-memory for MVP)
class AppState:
    source_a: List[UnifiedTransaction] = []
    source_b: List[UnifiedTransaction] = []
    original_csv_data: List[dict] = []  # Store original CSV rows for preview
    matched: pd.DataFrame = pd.DataFrame()
    conflicts: pd.DataFrame = pd.DataFrame()
    missing_in_b: pd.DataFrame = pd.DataFrame()
    anomalies: List[dict] = []

state = AppState()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Uploads and parses a CEX export file (CSV or MHTML).
    Returns the parsed transactions for preview.
    """
    # Extract just the filename without any directory path
    import os as os_module
    filename = os_module.path.basename(file.filename)
    temp_path = f"data/temp_{filename}"
    os.makedirs("data", exist_ok=True)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        if file.filename.endswith(".mhtml") or file.filename.endswith(".html"):
            df = extract_transactions_from_mhtml(temp_path)
            state.source_a = normalize_mhtml_data(df)
            # Store original data for preview
            state.original_csv_data = df.to_dict('records')
        elif file.filename.endswith(".csv"):
            # Read original CSV for preview
            original_df = pd.read_csv(temp_path)
            # Replace NaN with empty string for JSON serialization
            original_df = original_df.fillna('')
            state.original_csv_data = original_df.to_dict('records')
            
            # Process for reconciliation
            df = smart_csv_load(temp_path)
            state.source_a = normalize_csv_data(df)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        # Return the original data for preview
        return {
            "message": "File uploaded successfully", 
            "count": len(state.original_csv_data),
            "data": state.original_csv_data
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Upload error: {str(e)}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class FetchRequest(BaseModel):
    wallet_address: str
    chain: str = "bitcoin"  # Default to bitcoin for this project
    from_date: Optional[str] = None  # Format: YYYY-MM-DD
    to_date: Optional[str] = None    # Format: YYYY-MM-DD

@app.post("/api/fetch-blockchain")
async def fetch_blockchain(req: FetchRequest):
    """
    Fetches blockchain data and returns it for preview.
    Supports optional date range filtering.
    """
    try:
        client = BlockchainClient()
        state.source_b = client.fetch_transactions(req.wallet_address, req.chain)
        
        # Filter by date range if provided
        if req.from_date or req.to_date:
            from datetime import datetime
            import pytz
            
            filtered_txs = []
            for tx in state.source_b:
                # Parse date range
                if req.from_date:
                    from_dt = datetime.strptime(req.from_date, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
                    if tx.timestamp < from_dt:
                        continue
                
                if req.to_date:
                    # Add 1 day to include the entire to_date
                    to_dt = datetime.strptime(req.to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC)
                    if tx.timestamp > to_dt:
                        continue
                
                filtered_txs.append(tx)
            
            state.source_b = filtered_txs
            print(f"Filtered to {len(filtered_txs)} transactions between {req.from_date} and {req.to_date}")
        
        # Convert UnifiedTransaction objects to dicts for JSON serialization
        blockchain_data = [tx.to_dict() for tx in state.source_b]
        
        return {
            "message": "Blockchain data fetched successfully",
            "count": len(blockchain_data),
            "data": blockchain_data
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Fetch blockchain error: {str(e)}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Fetch failed: {str(e)}")

@app.post("/api/analyze")
async def analyze(wallet_addresses: Optional[List[str]] = None):
    """
    Runs Ordinals/Runes-aware reconciliation and returns correction suggestions.
    """
    if not state.source_a:
        raise HTTPException(status_code=400, detail="No CEX data found. Please upload a file.")
    if not state.source_b:
        raise HTTPException(status_code=400, detail="No blockchain data found. Please fetch blockchain data.")
        
    try:
        print(f"Starting Ordinals/Runes pattern detection with {len(state.source_a)} CEX transactions and {len(state.source_b)} blockchain transactions")
        
        # Get wallet addresses from request or use empty list
        my_wallets = wallet_addresses if wallet_addresses else []
        
        # Run enhanced reconciliation with pattern detection
        engine = ReconciliationEngine()
        results = engine.reconcile_with_corrections(state.source_a, state.source_b, my_wallets)
        
        # Create a mapping of transaction IDs to patterns
        tx_to_pattern = {}
        for suggestion in results["correction_suggestions"]:
            pattern = suggestion["pattern"]
            for tx in suggestion.get("affected_transactions", []):
                # Use a composite key: source + tx_id + timestamp to handle duplicates
                key = f"{tx.source}_{tx.tx_id}_{tx.timestamp.isoformat()}"
                # If a transaction is in multiple patterns, keep the first (highest priority) one
                if key not in tx_to_pattern:
                    tx_to_pattern[key] = pattern
        
        # Format correction suggestions for frontend
        formatted_suggestions = []
        for suggestion in results["correction_suggestions"]:
            formatted = {
                "pattern": suggestion["pattern"],
                "confidence": suggestion["confidence"],
                "severity": suggestion["severity"],
                "tax_impact": suggestion["tax_impact"],
                "affected_transactions": [],
                "recommended_actions": []
            }
            
            # Format affected transactions
            for tx in suggestion.get("affected_transactions", []):
                formatted["affected_transactions"].append({
                    "date": tx.timestamp.strftime("%Y-%m-%d"),
                    "time": tx.timestamp.strftime("%H:%M:%S"),
                    "type": tx.tx_type,
                    "amount": tx.amount,
                    "asset": tx.asset,
                    "tx_id": tx.tx_id,
                    "source": tx.source,
                    "metadata": tx.metadata if hasattr(tx, 'metadata') and tx.metadata else {},
                    "pattern": suggestion["pattern"]  # Add pattern to each transaction
                })
            
            # Format recommended actions
            for correction in suggestion.get("corrections", []):
                action = {
                    "action_type": correction["action"],
                    "reason": correction.get("reason", "")
                }
                
                # Add transaction details
                if "tx" in correction:
                    tx = correction["tx"]
                    action["transaction"] = {
                        "date": tx.timestamp.strftime("%Y-%m-%d"),
                        "time": tx.timestamp.strftime("%H:%M:%S"),
                        "type": tx.tx_type,
                        "amount": tx.amount,
                        "tx_id": tx.tx_id,
                        "source": tx.source,
                        "metadata": tx.metadata if hasattr(tx, 'metadata') and tx.metadata else {}
                    }
                
                # Add action-specific details
                if correction["action"] == "IGNORE":
                    action["warning"] = correction.get("warning", "")
                
                elif correction["action"] == "CHANGE_TO_TRADE":
                    action["sent_asset"] = correction.get("sent_asset", "")
                    action["sent_amount"] = correction.get("sent_amount", "")
                    action["received_asset"] = correction.get("received_asset", "")
                    action["received_quantity"] = correction.get("received_quantity", 1)
                    action["ordiscan_link"] = correction.get("ordiscan_link", "")
                    action["oklink_link"] = correction.get("oklink_link", "")
                    action["ordinals_link"] = correction.get("ordinals_link", "")
                    action["requires_ordiscan"] = correction.get("requires_ordiscan", False)
                    
                    # Add blockchain transaction metadata for asset tags
                    if "transaction" in correction:
                        tx = correction["transaction"]
                        action["transaction"] = {
                            "date": tx.timestamp.strftime("%Y-%m-%d"),
                            "time": tx.timestamp.strftime("%H:%M:%S"),
                            "type": tx.tx_type,
                            "amount": tx.amount,
                            "tx_id": tx.tx_id,
                            "source": tx.source,
                            "metadata": tx.metadata if hasattr(tx, 'metadata') and tx.metadata else {}
                        }
                
                elif correction["action"] == "NO_ACTION_NEEDED":
                    # For RUNE_RECEIVE and other non-action patterns
                    # Pass through note and verification links
                    action["note"] = correction.get("note", "")
                    action["ordiscan_link"] = correction.get("ordiscan_link", "")
                    action["oklink_link"] = correction.get("oklink_link", "")
                    action["ordinals_link"] = correction.get("ordinals_link", "")
                    
                    # Add blockchain transaction metadata for asset tags
                    if "transaction" in correction:
                        tx = correction["transaction"]
                        action["transaction"] = {
                            "date": tx.timestamp.strftime("%Y-%m-%d"),
                            "time": tx.timestamp.strftime("%H:%M:%S"),
                            "type": tx.tx_type,
                            "amount": tx.amount,
                            "tx_id": tx.tx_id,
                            "source": tx.source,
                            "metadata": tx.metadata if hasattr(tx, 'metadata') and tx.metadata else {}
                        }
                
                elif correction["action"] == "CHANGE_TO_FEE":
                    pass  # No additional details needed
                
                elif correction["action"] == "MERGE_AS_TRANSFER":
                    if "txs" in correction:
                        action["transactions"] = [{
                            "date": tx.timestamp.strftime("%Y-%m-%d"),
                            "time": tx.timestamp.strftime("%H:%M:%S"),
                            "type": tx.tx_type,
                            "amount": tx.amount,
                            "tx_id": tx.tx_id
                        } for tx in correction["txs"]]
                
                formatted["recommended_actions"].append(action)
            
            formatted_suggestions.append(formatted)
        
        # Enrich source_a and source_b with pattern labels
        enriched_source_a = []
        for tx in state.source_a:
            tx_dict = tx.to_dict()
            key = f"{tx.source}_{tx.tx_id}_{tx.timestamp.isoformat()}"
            if key in tx_to_pattern:
                tx_dict["pattern"] = tx_to_pattern[key]
            enriched_source_a.append(tx_dict)
        
        enriched_source_b = []
        for tx in state.source_b:
            tx_dict = tx.to_dict()
            key = f"{tx.source}_{tx.tx_id}_{tx.timestamp.isoformat()}"
            if key in tx_to_pattern:
                tx_dict["pattern"] = tx_to_pattern[key]
            enriched_source_b.append(tx_dict)
        
        print(f"Pattern detection complete: {results['summary']['total_issues']} issues found")
        print(f"By severity: {results['summary']['by_severity']}")
        print(f"By pattern: {results['summary']['by_pattern']}")
        
        return {
            "status": "completed",
            "correction_suggestions": formatted_suggestions,
            "summary": results["summary"],
            "enriched_source_a": enriched_source_a,
            "enriched_source_b": enriched_source_b
        }
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Analysis error: {str(e)}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/api/results")
async def get_results():
    """
    Returns the reconciliation results.
    """
    def df_to_records(df):
        if df.empty: return []
        # Convert timestamps to string for JSON serialization
        records = df.to_dict(orient='records')
        for r in records:
            if 'source_a' in r and r['source_a']:
                r['source_a']['timestamp'] = str(r['source_a']['timestamp'])
            if 'source_b' in r and r['source_b']:
                r['source_b']['timestamp'] = str(r['source_b']['timestamp'])
            if 'timestamp' in r:
                r['timestamp'] = str(r['timestamp'])
        return records

    return {
        "matched": df_to_records(state.matched),
        "conflicts": df_to_records(state.conflicts),
        "missing_in_blockchain": df_to_records(state.missing_in_b),
        "anomalies": state.anomalies
    }

class FetchRuneRequest(BaseModel):
    tx_id: str
    api_source: str  # "oklink" or "unisat"

@app.post("/api/fetch-rune-info")
async def fetch_rune_info(request: FetchRuneRequest):
    """
    Fetch Rune information for a specific transaction using UniSat API.
    """
    import requests
    from src.config import UNISAT_API_KEY
    
    tx_id = request.tx_id
    
    if not tx_id or len(tx_id) != 64:
        raise HTTPException(status_code=400, detail="Invalid transaction ID")
    
    try:
        # Use UniSat Rune Event endpoint (singular)
        url = "https://open-api.unisat.io/v1/indexer/runes/event"
        headers = {
            "Accept": "application/json"
        }
        if UNISAT_API_KEY:
            headers['Authorization'] = f"Bearer {UNISAT_API_KEY}"
            print(f"Using UniSat API Key: Yes")
        else:
            print(f"Using UniSat API Key: No (Rate limits may apply)")
            
        # Passing txid as query param
        params = {'txid': tx_id}
            
        print(f"Fetching UniSat Rune info for {tx_id[:8]} from {url}...")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        print(f"UniSat Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and data.get('data'):
                # 'data' should be a list of events or an object containing 'detail'
                event_list = data['data']
                if isinstance(event_list, dict) and 'detail' in event_list:
                     event_list = event_list['detail']
                
                if not isinstance(event_list, list):
                    event_list = [event_list] if event_list else []

                found_runes = []
                seen_runes = set()

                for event in event_list:
                    # Check for rune info in event
                    # Structure might vary, checking common fields
                    rune_name = event.get('rune') or event.get('runeName') or event.get('symbol')
                    amount = event.get('amount')
                    divisibility = event.get('divisibility', 0)
                    
                    if rune_name and amount:
                        if rune_name not in seen_runes:
                            seen_runes.add(rune_name)
                            found_runes.append({
                                "name": rune_name,
                                "amount": str(amount),
                                "divisibility": int(divisibility)
                            })
                
                if found_runes:
                    return {
                        "success": True,
                        "source": "unisat",
                        "runes": found_runes,
                        "tx_id": tx_id
                    }
                else:
                    print(f"No Rune events found in parsed data from events endpoint: {str(event_list)[:200]}")
            else:
                 print(f"UniSat events API returned code != 0 or empty data: {data}")
                    
        # Fallback to standard TX endpoint if events endpoint fails or returns nothing
        print("Fallback to standard UniSat TX endpoint...")
        url_fallback = f"https://open-api.unisat.io/v1/indexer/tx/{tx_id}"
        response = requests.get(url_fallback, headers=headers, timeout=10)
        
        if response.status_code == 200:
             data = response.json()
             if data.get('code') == 0 and data.get('data'):
                tx_data = data['data']
                
                found_runes = []
                if 'vout' in tx_data:
                    for vout in tx_data['vout']:
                        if 'runes' in vout and len(vout['runes']) > 0:
                            for r in vout['runes']:
                                found_runes.append({
                                    "name": r.get('runeName') or r.get('name'),
                                    "amount": r.get('amount', '0'),
                                    "divisibility": int(r.get('divisibility', 0))
                                })
                
                if found_runes:
                    return {
                        "success": True,
                        "source": "unisat",
                        "runes": found_runes,
                        "tx_id": tx_id
                    }

        # If we reach here, neither endpoint worked
        print(f"UniSat API Failed. Status: {response.status_code}, Body: {response.text[:200]}")
        raise HTTPException(status_code=404, detail="Rune data not found on UniSat")

    except requests.Timeout:
        raise HTTPException(status_code=504, detail="UniSat API timeout")
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"UniSat API error: {str(e)}")
    except Exception as e:
        print(f"Exception in fetch_rune_info: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching Rune info: {str(e)}")

class ExportToSheetsRequest(BaseModel):
    sheet_url: str
    wallet_addresses: Optional[List[str]] = None

@app.post("/api/export-to-sheets")
async def export_to_sheets(request: ExportToSheetsRequest):
    """
    Export analyzed blockchain transactions to Google Sheets Universal Import Template.
    Works independently - does not require CEX data from Step 1.
    """
    if not state.source_b:
        raise HTTPException(status_code=400, detail="No blockchain data found. Please fetch blockchain data first (Step 2).")
    
    try:
        from src.reporting.sheets_exporter import export_transactions_to_sheets
        from src.reconciliation.ordinals_detector import detect_patterns, group_transactions_by_txid
        
        print(f"Starting Google Sheets export with {len(state.source_b)} blockchain transactions")
        
        # Get wallet addresses from request or use empty list
        my_wallets = request.wallet_addresses if request.wallet_addresses else []
        
        # Run pattern detection on blockchain transactions
        # Group transactions by TxID for pattern detection
        blockchain_groups = group_transactions_by_txid(state.source_b)
        
        print(f"Created {len(blockchain_groups)} transaction groups for pattern detection")
        
        # Detect patterns in each group
        patterns = []
        for group_key, tx_group in blockchain_groups.items():
            pattern = detect_patterns(tx_group, my_wallets, state.source_b)
            if pattern:
                patterns.append(pattern)
        
        print(f"Detected {len(patterns)} patterns")
        
        # Export to Google Sheets
        result = export_transactions_to_sheets(
            transactions=state.source_b,
            patterns=patterns,
            sheet_url=request.sheet_url
        )
        
        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])
        
        return {
            "status": "success",
            "message": result['message'],
            "row_count": result['row_count'],
            "review_count": result['review_count'],
            "patterns_detected": len(patterns)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Export to sheets error: {str(e)}")
        print(f"Traceback:\n{error_details}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
