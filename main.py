import argparse
import sys
import os
from src.ingest.mhtml_parser import extract_transactions_from_mhtml, normalize_mhtml_data
from src.ingest.csv_parser import smart_csv_load, normalize_csv_data
from src.reconciliation.blockchain import BlockchainClient
from src.reconciliation.engine import ReconciliationEngine
from src.reconciliation.anomaly import AnomalyDetector
from src.reporting.excel_export import generate_reconciliation_report

def main():
    parser = argparse.ArgumentParser(description="BitMatch: Dual-Ledger Reconciliation Agent")
    
    # Input arguments
    parser.add_argument("--csv", help="Path to CoinLedger CSV export")
    parser.add_argument("--mhtml", help="Path to CoinLedger MHTML export")
    parser.add_argument("--wallet", help="Wallet address for blockchain verification")
    parser.add_argument("--chain", default="ethereum", help="Blockchain network (default: ethereum)")
    parser.add_argument("--output", default="reconciliation_report.xlsx", help="Output Excel file path")
    
    args = parser.parse_args()
    
    if not args.csv and not args.mhtml:
        print("Error: Must provide either --csv or --mhtml file.")
        sys.exit(1)
        
    print("--- BitMatch Agent Started ---")
    
    # 1. Ingest Data (Source A)
    source_a_txs = []
    try:
        if args.mhtml:
            print(f"Parsing MHTML: {args.mhtml}...")
            df = extract_transactions_from_mhtml(args.mhtml)
            source_a_txs = normalize_mhtml_data(df)
        elif args.csv:
            print(f"Parsing CSV: {args.csv}...")
            df = smart_csv_load(args.csv)
            source_a_txs = normalize_csv_data(df)
            
        print(f"Loaded {len(source_a_txs)} transactions from Source A.")
    except Exception as e:
        print(f"Error ingesting data: {e}")
        sys.exit(1)

    # 2. Fetch Blockchain Data (Source B)
    source_b_txs = []
    if args.wallet:
        print(f"Fetching blockchain data for {args.wallet}...")
        client = BlockchainClient()
        source_b_txs = client.fetch_transactions(args.wallet, args.chain)
        print(f"Loaded {len(source_b_txs)} transactions from Source B.")
    else:
        print("Warning: No wallet address provided. Skipping blockchain verification.")

    # 3. Reconcile
    print("Running reconciliation engine...")
    engine = ReconciliationEngine()
    matched, conflicts, missing_in_b = engine.reconcile(source_a_txs, source_b_txs)
    
    print(f"Results: {len(matched)} Matched, {len(conflicts)} Conflicts, {len(missing_in_b)} Missing in Blockchain")

    # 4. Detect Anomalies
    print("Detecting anomalies...")
    # Combine all transactions for anomaly detection
    all_txs = source_a_txs + source_b_txs
    detector = AnomalyDetector(all_txs)
    anomalies = detector.detect_anomalies()
    print(f"Found {len(anomalies)} anomalies.")

    # 5. Generate Report
    print(f"Generating report: {args.output}...")
    generate_reconciliation_report(matched, conflicts, missing_in_b, anomalies, args.output)
    
    print("--- Process Completed Successfully ---")

if __name__ == "__main__":
    main()
