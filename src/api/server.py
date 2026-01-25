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
    temp_path = f"data/temp_{file.filename}"
    os.makedirs("data", exist_ok=True)
    
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        if file.filename.endswith(".mhtml") or file.filename.endswith(".html"):
            df = extract_transactions_from_mhtml(temp_path)
            state.source_a = normalize_mhtml_data(df)
        elif file.filename.endswith(".csv"):
            df = smart_csv_load(temp_path)
            state.source_a = normalize_csv_data(df)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
            
        # Return the data for preview
        return {
            "message": "File uploaded successfully", 
            "count": len(state.source_a),
            "data": state.source_a
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class FetchRequest(BaseModel):
    wallet_address: str
    chain: str = "ethereum"

@app.post("/api/fetch-blockchain")
async def fetch_blockchain(req: FetchRequest):
    """
    Fetches blockchain data and returns it for preview.
    """
    try:
        client = BlockchainClient()
        state.source_b = client.fetch_transactions(req.wallet_address, req.chain)
        
        return {
            "message": "Blockchain data fetched successfully",
            "count": len(state.source_b),
            "data": state.source_b
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze():
    """
    Runs reconciliation on the already loaded source_a and source_b.
    """
    if not state.source_a:
        raise HTTPException(status_code=400, detail="No CEX data found. Please upload a file.")
    if not state.source_b:
        raise HTTPException(status_code=400, detail="No blockchain data found. Please fetch blockchain data.")
        
    try:
        # Run Reconciliation
        engine = ReconciliationEngine()
        state.matched, state.conflicts, state.missing_in_b = engine.reconcile(state.source_a, state.source_b)
        
        # Detect Anomalies
        all_txs = state.source_a + state.source_b
        detector = AnomalyDetector(all_txs)
        state.anomalies = detector.detect_anomalies()
        
        return {
            "status": "completed",
            "stats": {
                "matched": len(state.matched),
                "conflicts": len(state.conflicts),
                "missing_in_blockchain": len(state.missing_in_b),
                "anomalies": len(state.anomalies)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
