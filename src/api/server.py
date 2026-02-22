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
    append: bool = False  # If True, append to existing source_b instead of replacing

@app.post("/api/fetch-blockchain")
async def fetch_blockchain(req: FetchRequest):
    """
    Fetches blockchain data and returns it for preview.
    Supports optional date range filtering.
    """
    try:
        client = BlockchainClient()
        new_txs = client.fetch_transactions(req.wallet_address, req.chain)
        
        # Filter new transactions by date range BEFORE accumulating
        if req.from_date or req.to_date:
            from datetime import datetime
            import pytz
            
            filtered_txs = []
            for tx in new_txs:
                if req.from_date:
                    from_dt = datetime.strptime(req.from_date, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
                    if tx.timestamp < from_dt:
                        continue
                if req.to_date:
                    to_dt = datetime.strptime(req.to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, tzinfo=pytz.UTC)
                    if tx.timestamp > to_dt:
                        continue
                filtered_txs.append(tx)
            
            new_txs = filtered_txs
            print(f"Filtered to {len(new_txs)} transactions between {req.from_date} and {req.to_date}")
        
        # Accumulate into state (for JSON export / analysis later)
        if req.append:
            state.source_b.extend(new_txs)
        else:
            state.source_b = list(new_txs)
        
        # Return ONLY the new transactions (frontend accumulates its own list)
        blockchain_data = [tx.to_dict() for tx in new_txs]
        
        return {
            "message": "Blockchain data fetched successfully",
            "count": len(blockchain_data),
            "total_accumulated": len(state.source_b),
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
                    action["hiro_link"] = correction.get("hiro_link", "")
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
                    action["hiro_link"] = correction.get("hiro_link", "")
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
    api_source: str = "unisat"  # default to unisat, optional
    wallet_addresses: Optional[List[str]] = None

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
        # 1. Primary: UniSat TX details endpoint (returns both runes and inscriptions inside vout)
        url = f"https://open-api.unisat.io/v1/indexer/tx/{tx_id}"
        headers = {
            "Accept": "application/json"
        }
        if UNISAT_API_KEY:
            headers['Authorization'] = f"Bearer {UNISAT_API_KEY}"
            
        print(f"Fetching UniSat TX info for {tx_id[:8]} from {url}...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"UniSat Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0 and data.get('data'):
                tx_data = data['data']
                found_runes = []
                seen_names = set()
                
                if 'vout' in tx_data:
                    for vout in tx_data['vout']:
                        # Feature 8: Filter by wallet address if provided
                        vout_address = vout.get('scriptPubKey', {}).get('address')
                        if request.wallet_addresses and vout_address not in request.wallet_addresses:
                            continue

                        # Check for Runes
                        if 'runes' in vout and vout['runes']:
                            for r in vout['runes']:
                                name = r.get('runeName') or r.get('name') or r.get('symbol')
                                if name and name not in seen_names:
                                    seen_names.add(name)
                                    found_runes.append({
                                        "name": name,
                                        "amount": str(r.get('amount', '0')),
                                        "divisibility": int(r.get('divisibility', 0))
                                    })
                        
                        # Check for Ordinal Inscriptions
                        if 'inscriptions' in vout and vout['inscriptions']:
                            for ins in vout['inscriptions']:
                                ins_id = ins if isinstance(ins, str) else ins.get('inscriptionId', '')
                                if ins_id and ins_id not in seen_names:
                                    seen_names.add(ins_id)
                                    
                                    # Fetch rich metadata for this inscription
                                    name = f"Ordinal Inscription"
                                    content_type = "unknown"
                                    content_url = f"https://ordinals.com/content/{ins_id}"
                                    
                                    try:
                                        meta_url = f"https://open-api.unisat.io/v1/indexer/inscription/info/{ins_id}"
                                        meta_res = requests.get(meta_url, headers=headers, timeout=5)
                                        if meta_res.status_code == 200:
                                            m_data = meta_res.json().get('data', {})
                                            
                                            # Check if there's a delegate that has the actual content/name
                                            if m_data.get('hasDeligate') and m_data.get('deligate'):
                                                deligate_id = m_data.get('deligate')
                                                del_url = f"https://open-api.unisat.io/v1/indexer/inscription/info/{deligate_id}"
                                                del_res = requests.get(del_url, headers=headers, timeout=5)
                                                if del_res.status_code == 200:
                                                    m_data = del_res.json().get('data', m_data)
                                            
                                            # Extract name and collection
                                            meta_obj = m_data.get('meta', {}) or {}
                                            name = meta_obj.get('name') or m_data.get('inscriptionName')
                                            
                                            collection = None
                                            # Try to find collection name
                                            if isinstance(meta_obj.get('collection'), dict):
                                                collection = meta_obj['collection'].get('name')
                                            elif isinstance(meta_obj.get('collection'), str):
                                                collection = meta_obj['collection']
                                            elif m_data.get('collectionName'):
                                                collection = m_data.get('collectionName')

                                            if not name or name.startswith("Inscription #"):
                                                try:
                                                    from src.config import HIRO_API_KEY
                                                    if HIRO_API_KEY and ins_id:
                                                        h_url = f"https://api.hiro.so/ordinals/v1/inscriptions/{ins_id}"
                                                        h_res = requests.get(h_url, headers={"Accept": "application/json", "x-hiro-api-key": HIRO_API_KEY}, timeout=5)
                                                        if h_res.status_code == 200:
                                                            h_meta = h_res.json().get("metadata", {})
                                                            if isinstance(h_meta, dict) and h_meta.get("Name"):
                                                                name = h_meta.get("Name")
                                                except Exception:
                                                    pass

                                            if not name:
                                                num = m_data.get('inscriptionNumber')
                                                name = f"Inscription #{num}" if num is not None else "Ordinal Inscription"
                                            
                                            content_type = m_data.get('contentType', 'unknown')
                                            if m_data.get('inscriptionId'):
                                                content_url = f"https://ordinals.com/content/{m_data.get('inscriptionId')}"
                                    except Exception as e:
                                        print(f"Failed to fetch rich ordinal info: {e}")

                                    found_runes.append({
                                        "name": name,
                                        "collection": collection,
                                        "inscription_id": ins_id,
                                        "inscription_number": num,
                                        "amount": "1",
                                        "divisibility": 0,
                                        "content_type": content_type,
                                        "content_url": content_url
                                    })
                
                if found_runes:
                    return {
                        "success": True,
                        "source": "unisat",
                        "runes": found_runes,
                        "tx_id": tx_id
                    }
                else:
                    print(f"No runes/ordinals found in UniSat vout data")
        # 2. Fallback: Try Hiro API (sunsetting March 2026, 900 req/min)
        from src.config import HIRO_API_KEY
        if HIRO_API_KEY:
            print("Fallback to Hiro API...")
            try:
                hiro_url = f"https://api.hiro.so/ordinals/v1/inscriptions?output={tx_id}:0"
                hiro_headers = {
                    "Accept": "application/json",
                    "x-hiro-api-key": HIRO_API_KEY
                }
                hiro_response = requests.get(hiro_url, headers=hiro_headers, timeout=15)
                
                if hiro_response.status_code == 200:
                    hiro_data = hiro_response.json()
                    results = hiro_data.get('results', [])
                    found_runes = []
                    for item in results:
                        content_type = item.get('content_type', 'Inscription')
                        number = item.get('number')
                        insc_id = item.get('id', '')
                        if number is not None:
                            name = f"Inscription #{number}"
                            content_url = f"https://ordinals.com/content/{insc_id}" if insc_id else ""
                            collection = None
                            
                            if insc_id:
                                try:
                                    # Still enrich via UniSat if possible
                                    meta_url = f"https://open-api.unisat.io/v1/indexer/inscription/info/{insc_id}"
                                    headers = {"Accept": "application/json"}
                                    from src.config import UNISAT_API_KEY
                                    if UNISAT_API_KEY: headers['Authorization'] = f"Bearer {UNISAT_API_KEY}"
                                    meta_res = requests.get(meta_url, headers=headers, timeout=5)
                                    if meta_res.status_code == 200:
                                        m_data = meta_res.json().get('data', {})
                                        
                                        if m_data.get('hasDeligate') and m_data.get('deligate'):
                                            deligate_id = m_data.get('deligate')
                                            del_url = f"https://open-api.unisat.io/v1/indexer/inscription/info/{deligate_id}"
                                            del_res = requests.get(del_url, headers=headers, timeout=5)
                                            if del_res.status_code == 200:
                                                m_data = del_res.json().get('data', m_data)
                                        
                                        meta_obj = m_data.get('meta', {}) or {}
                                        fetched_name = meta_obj.get('name') or m_data.get('inscriptionName')
                                        if not fetched_name or fetched_name.startswith("Inscription #"):
                                            try:
                                                from src.config import HIRO_API_KEY
                                                if HIRO_API_KEY and insc_id:
                                                    h_url = f"https://api.hiro.so/ordinals/v1/inscriptions/{insc_id}"
                                                    h_res = requests.get(h_url, headers={"Accept": "application/json", "x-hiro-api-key": HIRO_API_KEY}, timeout=5)
                                                    if h_res.status_code == 200:
                                                        h_meta = h_res.json().get("metadata", {})
                                                        if isinstance(h_meta, dict) and h_meta.get("Name"):
                                                            fetched_name = h_meta.get("Name")
                                            except Exception:
                                                pass
                                        if fetched_name: name = fetched_name
                                        
                                        if isinstance(meta_obj.get('collection'), dict):
                                            collection = meta_obj['collection'].get('name')
                                        elif isinstance(meta_obj.get('collection'), str):
                                            collection = meta_obj['collection']
                                        elif m_data.get('collectionName'):
                                            collection = m_data.get('collectionName')
                                            
                                        m_content_type = m_data.get('contentType')
                                        if m_content_type: content_type = m_content_type
                                except Exception as e:
                                    print(f"Failed to fetch rich ordinal info in Hiro fallback: {e}")
                                    
                            found_runes.append({
                                "name": name,
                                "amount": "1",
                                "inscription_id": insc_id,
                                "inscription_number": number,
                                "collection": collection,
                                "content_type": content_type,
                                "content_url": content_url,
                                "divisibility": 0
                            })
                    if found_runes:
                        return {
                            "success": True,
                            "source": "hiro",
                            "runes": found_runes,
                            "tx_id": tx_id
                        }
                
                # Also try Hiro Runes endpoint
                hiro_runes_url = f"https://api.hiro.so/runes/v1/transactions/{tx_id}/activity"
                runes_response = requests.get(hiro_runes_url, headers=hiro_headers, timeout=15)
                if runes_response.status_code == 200:
                    runes_data = runes_response.json()
                    results = runes_data.get('results', [])
                    found_runes = []
                    rune_balances = {}
                    
                    for item in results:
                        if item.get('operation') == 'receive':
                            receiver = item.get('receiver_address') or item.get('address')
                            if request.wallet_addresses and receiver not in request.wallet_addresses:
                                continue
                                
                            rune_name = item.get('rune', {}).get('name') or item.get('rune', {}).get('spaced_name', '')
                            amount_val = float(item.get('amount', '0'))
                            divisibility = item.get('rune', {}).get('divisibility', 0)
                            
                            if rune_name:
                                if rune_name not in rune_balances:
                                    rune_balances[rune_name] = {'amount': 0.0, 'divisibility': divisibility}
                                rune_balances[rune_name]['amount'] += amount_val

                    for name, data in rune_balances.items():
                        # Format avoiding scientific notation for floats
                        amt_str = f"{data['amount']:.8f}".rstrip('0').rstrip('.')
                        found_runes.append({
                            "name": name,
                            "amount": amt_str,
                            "divisibility": data['divisibility']
                        })
                    if found_runes:
                        return {
                            "success": True,
                            "source": "hiro",
                            "runes": found_runes,
                            "tx_id": tx_id
                        }
            except Exception as hiro_err:
                print(f"Hiro fallback error: {hiro_err}")

        # Fallback 3: UniSat Inscription lookup (for Ordinals)
        print("Fallback to UniSat Inscription lookup...")
        try:
            inscription_url = f"https://open-api.unisat.io/v1/indexer/tx/{tx_id}/inscription-transfers"
            insc_response = requests.get(inscription_url, headers=headers, timeout=15)
            
            if insc_response.status_code == 200:
                insc_data = insc_response.json()
                if insc_data.get('code') == 0 and insc_data.get('data'):
                    transfers = insc_data['data']
                    if isinstance(transfers, dict) and 'detail' in transfers:
                        transfers = transfers['detail']
                    if not isinstance(transfers, list):
                        transfers = [transfers] if transfers else []
                    
                    found_inscriptions = []
                    for transfer in transfers:
                        insc_number = transfer.get('inscriptionNumber') or transfer.get('number')
                        insc_id = transfer.get('inscriptionId') or transfer.get('id')
                        content_type = transfer.get('contentType', '')
                        
                        if insc_number is not None or insc_id:
                            name = f"Inscription #{insc_number}" if insc_number is not None else "Ordinal Inscription"
                            content_url = f"https://ordinals.com/content/{insc_id}" if insc_id else ""
                            collection = None
                            
                            if insc_id:
                                try:
                                    meta_url = f"https://open-api.unisat.io/v1/indexer/inscription/info/{insc_id}"
                                    meta_res = requests.get(meta_url, headers=headers, timeout=5)
                                    if meta_res.status_code == 200:
                                        m_data = meta_res.json().get('data', {})
                                        
                                        if m_data.get('hasDeligate') and m_data.get('deligate'):
                                            deligate_id = m_data.get('deligate')
                                            del_url = f"https://open-api.unisat.io/v1/indexer/inscription/info/{deligate_id}"
                                            del_res = requests.get(del_url, headers=headers, timeout=5)
                                            if del_res.status_code == 200:
                                                m_data = del_res.json().get('data', m_data)
                                        
                                        meta_obj = m_data.get('meta', {}) or {}
                                        fetched_name = meta_obj.get('name') or m_data.get('inscriptionName')
                                        if not fetched_name or fetched_name.startswith("Inscription #"):
                                            try:
                                                from src.config import HIRO_API_KEY
                                                if HIRO_API_KEY and insc_id:
                                                    h_url = f"https://api.hiro.so/ordinals/v1/inscriptions/{insc_id}"
                                                    h_res = requests.get(h_url, headers={"Accept": "application/json", "x-hiro-api-key": HIRO_API_KEY}, timeout=5)
                                                    if h_res.status_code == 200:
                                                        h_meta = h_res.json().get("metadata", {})
                                                        if isinstance(h_meta, dict) and h_meta.get("Name"):
                                                            fetched_name = h_meta.get("Name")
                                            except Exception:
                                                pass
                                        if fetched_name:
                                            name = fetched_name
                                            
                                        if isinstance(meta_obj.get('collection'), dict):
                                            collection = meta_obj['collection'].get('name')
                                        elif isinstance(meta_obj.get('collection'), str):
                                            collection = meta_obj['collection']
                                        elif m_data.get('collectionName'):
                                            collection = m_data.get('collectionName')
                                            
                                        m_content_type = m_data.get('contentType')
                                        if m_content_type:
                                            content_type = m_content_type
                                except Exception as e:
                                    print(f"Failed to fetch rich ordinal info in fallback: {e}")

                            found_inscriptions.append({
                                "name": name,
                                "collection": collection,
                                "inscription_id": insc_id or '',
                                "inscription_number": insc_number,
                                "content_type": content_type,
                                "content_url": content_url,
                                "amount": "1"
                            })
                    
                    if found_inscriptions:
                        return {
                            "success": True,
                            "source": "unisat-inscription",
                            "runes": found_inscriptions,  # reuse runes field for compatibility
                            "inscriptions": found_inscriptions,
                            "tx_id": tx_id
                        }
                    else:
                        print(f"No inscriptions found in transfer data: {str(transfers)[:200]}")
        except Exception as insc_err:
            print(f"UniSat inscription fallback error: {insc_err}")

        # If all sources failed, return graceful "not found" (not a crash)
        print(f"All APIs failed to find Rune/Ordinal data for {tx_id[:8]}")
        return {
            "success": False,
            "source": "none",
            "runes": [],
            "tx_id": tx_id,
            "message": "No Rune/Ordinal data found. This may be a standard BTC transaction."
        }

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


# ============================================================
# JSON Export / Upload (Step 2 data caching)
# ============================================================

@app.post("/api/export-blockchain-json")
async def export_blockchain_json():
    """
    Export fetched Source B (blockchain) data as JSON for offline caching.
    Users can re-upload this later to avoid re-fetching from the API.
    """
    if not state.source_b:
        raise HTTPException(status_code=400, detail="No blockchain data to export. Fetch blockchain data first (Step 2).")
    
    data = {
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "transaction_count": len(state.source_b),
        "transactions": [tx.to_dict() for tx in state.source_b]
    }
    
    return data


class UploadBlockchainJsonRequest(BaseModel):
    transactions: list
    version: Optional[str] = "1.0"


@app.post("/api/upload-blockchain-json")
async def upload_blockchain_json(request: UploadBlockchainJsonRequest):
    """
    Upload cached blockchain JSON to restore Source B without re-fetching.
    Accepts the same format exported by /api/export-blockchain-json.
    """
    try:
        import pytz
        
        restored_txs = []
        for tx_data in request.transactions:
            # Parse timestamp back to datetime
            ts = tx_data.get("timestamp", "")
            if isinstance(ts, str):
                try:
                    timestamp = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    timestamp = datetime.now(tz=pytz.UTC)
            else:
                timestamp = datetime.now(tz=pytz.UTC)
            
            tx = UnifiedTransaction(
                timestamp=timestamp,
                asset=tx_data.get("asset", "BTC"),
                amount=float(tx_data.get("amount", 0)),
                fee=float(tx_data.get("fee", 0)),
                tx_id=tx_data.get("tx_id", ""),
                tx_type=tx_data.get("tx_type", "Unknown"),
                source=tx_data.get("source", "BLOCKCHAIN"),
                price_krw=tx_data.get("price_krw"),
                metadata=tx_data.get("metadata", {}),
                witness_data=tx_data.get("witness_data", []),
                raw_hex=tx_data.get("raw_hex")
            )
            restored_txs.append(tx)
        
        state.source_b = restored_txs
        
        return {
            "message": "Blockchain data restored successfully",
            "count": len(restored_txs)
        }
    except Exception as e:
        import traceback
        print(f"Upload JSON error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================
# Blockchain-Only Analysis (Option C — no CEX required)
# ============================================================

class AnalyzeBlockchainOnlyRequest(BaseModel):
    wallet_addresses: Optional[List[str]] = None


@app.post("/api/analyze-blockchain-only")
async def analyze_blockchain_only(request: AnalyzeBlockchainOnlyRequest):
    """
    Analyze blockchain transactions WITHOUT CEX data.
    Runs pattern detection on Source B and produces Source C
    (CoinLedger-labeled normalized transactions).
    """
    if not state.source_b:
        raise HTTPException(status_code=400, detail="No blockchain data found. Please fetch or upload blockchain data first (Step 2).")
    
    try:
        from src.reconciliation.ordinals_detector import detect_patterns, group_transactions_by_txid
        
        my_wallets = request.wallet_addresses if request.wallet_addresses else []
        
        print(f"Starting blockchain-only analysis with {len(state.source_b)} transactions")
        
        # Group transactions by TxID
        blockchain_groups = group_transactions_by_txid(state.source_b)
        print(f"Created {len(blockchain_groups)} transaction groups")
        
        # Detect patterns
        patterns = []
        tx_to_pattern = {}
        
        for group_key, tx_group in blockchain_groups.items():
            pattern = detect_patterns(tx_group, my_wallets, state.source_b)
            if pattern:
                patterns.append(pattern)
                
                corrections_map = {id(c["tx"]): c.get("action") for c in pattern.get("corrections", []) if "tx" in c}
                
                # Map each transaction in this group to its detected pattern
                for tx in tx_group:
                    # Make key unique by including amount
                    key = f"{tx.source}_{tx.tx_id}_{tx.timestamp.isoformat()}_{tx.amount}"
                    if key not in tx_to_pattern:
                        tx_to_pattern[key] = {
                            "pattern": pattern.get("pattern", ""),
                            "confidence": pattern.get("confidence", 0),
                            "action": corrections_map.get(id(tx))
                        }
        
        # Build Source C: CoinLedger-labeled transactions
        source_c = []
        for tx in state.source_b:
            tx_dict = tx.to_dict()
            key = f"{tx.source}_{tx.tx_id}_{tx.timestamp.isoformat()}_{tx.amount}"
            
            matched_pattern = tx_to_pattern.get(key, None)
            
            if matched_pattern:
                # Apply CoinLedger label from pattern
                pattern_name = matched_pattern["pattern"]
                action = matched_pattern["action"]
                tx_dict["pattern"] = pattern_name
                tx_dict["confidence"] = matched_pattern["confidence"]
                
                # Map pattern to CoinLedger type
                coinledger_type_map = {
                    "MINT_BUY": "Mint",
                    "BULK_MINT": "Mint",
                    "SALE": "Trade",
                    "NFT_TRADE": "Trade",
                    "MAGIC_EDEN_BUY": "Trade",
                    "MAGIC_EDEN_BUY_ISOLATED": "Trade",
                    "MAGIC_EDEN_SALE": "Trade",
                    "GAS_FEE": "Withdrawal",
                    "SELF_TRANSFER": "Ignored",
                    "RUNE_RECEIVE": "Deposit",
                    "RUNE_CENOTAPH": "Investment Loss",
                    "BRC20_TRANSFER": "Trade",
                    "FIAT_ONRAMP": "Trade",
                    "PSBT_SWAP": "Trade",
                }
                
                if action == "IGNORE":
                    tx_dict["coinledger_type"] = "Ignored"
                else:
                    tx_dict["coinledger_type"] = coinledger_type_map.get(pattern_name, tx.tx_type)
                
                # Map to description
                description_map = {
                    "MINT_BUY": "Ordinal/Rune Mint detected",
                    "BULK_MINT": "Bulk Ordinal/Rune Mint detected",
                    "SALE": "NFT/Rune Sale detected",
                    "NFT_TRADE": "NFT Marketplace Trade",
                    "MAGIC_EDEN_BUY": "Magic Eden Buy (2% fee detected)",
                    "MAGIC_EDEN_BUY_ISOLATED": "Magic Eden Buy (Isolated Deposit)",
                    "MAGIC_EDEN_SALE": "Magic Eden Sale",
                    "GAS_FEE": "Network Fee / Gas",
                    "SELF_TRANSFER": "Self-transfer between own wallets",
                    "RUNE_RECEIVE": "Rune/Ordinal received (non-taxable)",
                    "RUNE_CENOTAPH": "Malformed Rune (burned)",
                    "BRC20_TRANSFER": "BRC-20 transfer inscription",
                    "FIAT_ONRAMP": "Fiat on-ramp purchase",
                    "PSBT_SWAP": "PSBT Marketplace Swap",
                }
                
                if action == "IGNORE":
                    # Differentiate: withdrawal = payment, deposit = dust wrapper
                    if tx.tx_type in ['Withdrawal', 'Send'] and pattern_name in ['MINT_BUY', 'BULK_MINT']:
                        tx_dict["description"] = "BTC payment for Ordinal/Rune mint (cost basis on companion row)"
                    else:
                        tx_dict["description"] = "Dust wrapper for Ordinal/Rune (not taxable income)"
                else:
                    tx_dict["description"] = description_map.get(pattern_name, "")
            else:
                # No pattern matched — use raw transaction type
                tx_dict["pattern"] = None
                tx_dict["confidence"] = 0
                tx_dict["coinledger_type"] = tx.tx_type  # Deposit/Withdrawal as-is
                tx_dict["description"] = ""
            
            # Add verification links
            if tx.tx_id and len(tx.tx_id) > 10 and tx.source != "CEX":
                tx_dict["verify_mempool"] = f"https://mempool.space/tx/{tx.tx_id}"
                tx_dict["verify_blockchain"] = f"https://www.blockchain.com/btc/tx/{tx.tx_id}"
                tx_dict["verify_ordiscan"] = f"https://ordiscan.com/tx/{tx.tx_id}"
            
            source_c.append(tx_dict)
        
        # Summary stats
        pattern_counts = {}
        for p in patterns:
            pname = p.get("pattern", "UNKNOWN")
            pattern_counts[pname] = pattern_counts.get(pname, 0) + 1
        
        print(f"Blockchain-only analysis complete: {len(patterns)} patterns detected")
        
        return {
            "status": "completed",
            "source_c": source_c,
            "summary": {
                "total_transactions": len(state.source_b),
                "patterns_detected": len(patterns),
                "by_pattern": pattern_counts,
            },
            "patterns": [
                {
                    "pattern": p.get("pattern"),
                    "confidence": p.get("confidence"),
                    "severity": p.get("severity", "MEDIUM"),
                    "description": p.get("description", ""),
                    "affected_count": len(p.get("affected_transactions", [])),
                }
                for p in patterns
            ]
        }
        
    except Exception as e:
        import traceback
        print(f"Blockchain-only analysis error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
