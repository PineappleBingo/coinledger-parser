# BitMatch: Dual-Ledger Reconciliation Agent

BitMatch is a specialized audit reconciliation agent designed for the Korean cryptocurrency tax compliance market. It addresses the gap between centralized exchange reporting and blockchain verification.

## Features

- **MHTML Parsing**: Extract transaction tables directly from saved webpages (CoinLedger, etc.) to bypass CSV format volatility.
- **Blockchain Verification**: Direct RPC calls to verify on-chain data.
- **AI-Powered Schema Inference**: Automatically map CSV headers to a unified schema using Gemini.
- **Fuzzy Matching Engine**: Match transactions based on TxID, time window, and amount.
- **Korean Language Support**: Native Korean UI and error messages.

## Setup (Track B - Local Development)

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Environment**:
    Copy `.env.example` to `.env` and fill in your API keys.
    ```bash
    cp .env.example .env
    ```

3.  **Run Reconciliation**:
    (Instructions to be added as features are implemented)

## Project Structure

- `data/`: Place your CSV and MHTML files here.
- `src/ingest/`: Data ingestion logic (Agent Alpha).
- `src/reconciliation/`: Matching engine (Agent Beta).
- `src/reporting/`: UI and export logic (Agent Gamma).