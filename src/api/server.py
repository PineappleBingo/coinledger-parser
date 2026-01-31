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
                    "metadata": tx.metadata if hasattr(tx, 'metadata') and tx.metadata else {}
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
        
        print(f"Pattern detection complete: {results['summary']['total_issues']} issues found")
        print(f"By severity: {results['summary']['by_severity']}")
        print(f"By pattern: {results['summary']['by_pattern']}")
        
        return {
            "status": "completed",
            "correction_suggestions": formatted_suggestions,
            "summary": results["summary"]
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
