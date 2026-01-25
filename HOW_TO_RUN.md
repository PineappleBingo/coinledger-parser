# How to Run BitMatch

## 1. Project Overview
**Identity**: BitMatch is a specialized audit reconciliation agent designed for the Korean cryptocurrency tax compliance market. It addresses the gap between centralized exchange reporting and blockchain verification.

**North Star**: To provide a seamless, dual-ledger reconciliation process that verifies CEX data against on-chain reality using AI-powered schema inference and fuzzy matching.

## 2. Environment Setup

### MCP Servers
No specific MCP servers are required for the core functionality of this project.

### Environment Variables
The following environment variables are required. Copy `.env.example` to `.env` in the project root and fill them in:

- `DEPLOYMENT_TIER`: Set to `development` or `production`.
- `GEMINI_API_KEY`: Your Google Gemini API key (for AI parsing).
- `QUICKNODE_RPC_URL`: Your Blockchain RPC URL (e.g., from QuickNode or Infura).

**UI Selection Instructions**:
1.  Create a `.env` file in the root directory `coinledger-parser`.
2.  Paste the content from `.env.example`.
3.  Replace the placeholder values with your actual API keys.

## 3. Execution Instructions (Local)

### Backend (API Server)
The backend is a FastAPI application that handles file parsing, blockchain fetching, and reconciliation logic.

**Folder Location**: `coinledger-parser` (Root)

```bash
cd coinledger-parser
# Ensure virtual environment is active
source .venv/bin/activate
# Run the server
uvicorn src.api.server:app --reload
```

*The server will start at `http://127.0.0.1:8000`.*

### Frontend (User Interface)
The frontend is a React/Vite application that provides the interactive workflow.

**Folder Location**: `coinledger-parser/frontend`

```bash
cd coinledger-parser/frontend
# Install dependencies (if first time)
npm install
# Run the dev server
npm run dev
```

*The UI will be available at `http://localhost:5173`.*

## 4. UI Component Interaction

Once both the backend and frontend are running, open your browser to `http://localhost:5173`.

### Workflow Steps:

1.  **Upload CEX Export**:
    - Click "Choose File" and select your CEX export file (CSV or MHTML).
    - Click "Upload & Preview".
    - **Result**: The "Source A: CEX Export" table will populate with parsed data.

2.  **Fetch Blockchain Data**:
    - Enter the wallet address associated with the CEX account.
    - Click "Fetch & Preview".
    - **Result**: The "Source B: Blockchain" table will populate with on-chain transactions.

3.  **Analyze & Reconcile**:
    - Click "Run Analysis".
    - **Result**: The view will switch to the "Reconciliation Report" showing:
        - **Matched Transactions**: Confirmed matches.
        - **Conflicts**: Discrepancies between CEX and Chain.
        - **Missing in CEX**: Transactions found on-chain but missing from the export.
