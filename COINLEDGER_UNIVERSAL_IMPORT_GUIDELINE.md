COINLEDGER_UNIVERSAL_IMPORT_GUIDELINE.md
Target System: Good Antigravity / AI Logic
Reference Source: CoinLedger Universal Manual Import Template Guide Purpose: Defines the strict schema and formatting rules for generating CSV files to manually import transactions into CoinLedger.

--------------------------------------------------------------------------------
1. File Structure Overview
The CSV file MUST contain the following headers in this exact order. Do not delete optional columns; leave them blank if unused.
Column Header
Status
Description
Format/Validation
Date (UTC)
Required
Timestamp of transaction in Coordinated Universal Time.
mm/dd/yyyy hh:mm:ss
Platform
Optional
Name of the exchange/wallet (e.g., "Magic Eden", "Unisat").
String
Asset Sent
Cond.
Ticker symbol of asset disposed (e.g., BTC).
String (No currency symbols)
Amount Sent
Cond.
Quantity of asset disposed.
Number (No , or $)
Asset Received
Cond.
Ticker symbol of asset acquired (e.g., RUNE).
String (No currency symbols)
Amount Received
Cond.
Quantity of asset acquired.
Number (No , or $)
Fee Currency
Optional
Ticker of the fee asset (usually BTC or ETH).
String
Fee Amount
Optional
Quantity of fee paid.
Number
Type
Required*
Classification of the transaction.
Approved Enum (See Section 3)
Description
Optional
Notes or context.
String
TxHash
Optional
Transaction ID for verification.
String
*Type is mandatory for Deposits/Withdrawals. It is optional for Trades if both Sent/Received columns are filled.

--------------------------------------------------------------------------------
2. Critical Formatting Rules (AI Instructions)
1. Date Formatting: Dates MUST be in UTC. The required format is mm/dd/yyyy hh:mm:ss (e.g., 04/20/2024 14:30:00). Do not use ISO 8601 or other formats.
2. No Currency Symbols: Do NOT include $, €, or £ in Amount columns. Use raw numbers only.
3. No Special Characters: Do NOT use + or - to indicate direction. The column (Sent vs. Received) determines direction.
4. Handling Empty Data: If a field is not applicable (e.g., "Asset Sent" for a Mining reward), leave the cell BLANK.
    ◦ DO NOT enter 0, N/A, or ---. This will cause the import to fail.

--------------------------------------------------------------------------------
3. Transaction Type Logic Mapping
When generating rows based on the ANALYSIS_LOGIC_V2.md patterns, map them to the Universal Template as follows:
Scenario A: Trades (Buys, Sells, Swaps)
Used for: Fiat On-Ramps (P1), Runes Minting (P2), Swaps.
• Logic: Both "Sent" and "Received" columns must be populated.
• Type Field: Optional (can be left blank or labeled Trade).
• Example (Runes Mint):
    ◦ Asset Sent: BTC
    ◦ Amount Sent: 0.0005
    ◦ Asset Received: DOG.GO.TO.THE.MOON
    ◦ Amount Received: 1000
    ◦ Type: Trade
Scenario B: Income / Deposits
Used for: Staking Rewards, Airdrops, Mining.
• Logic: Only "Received" columns are populated. "Sent" columns MUST be blank.
• Type Field: MANDATORY. Must be one of:
    ◦ Income
    ◦ Interest
    ◦ Mining
    ◦ Staking
    ◦ Airdrop
    ◦ Gift Received
    ◦ Deposit (Note: Deposit is treated as a non-taxable self-transfer).
Scenario C: Withdrawals / Expenses
Used for: Merchant Payments, Gifts Sent, Gas Fees (if standalone).
• Logic: Only "Sent" columns are populated. "Received" columns MUST be blank.
• Type Field: MANDATORY. Must be one of:
    ◦ Gift Sent
    ◦ Merchant Payment
    ◦ Interest Payment
    ◦ Withdrawal (Note: Withdrawal is treated as a non-taxable self-transfer).

--------------------------------------------------------------------------------
4. Special Handling for NFTs & Runes
NFTs
• Constraint: Before importing a CSV with NFT data, the user must add a "Custom Asset" in CoinLedger for that specific NFT (e.g., "BAYC #123").
• CSV Generation: Enter the NFT name (e.g., "BAYC #123") exactly as the Asset Sent or Asset Received.
Fees
• Logic: Only populate Fee Currency and Fee Amount if the fee was not already deducted from the Amount Received or added to the Amount Sent. If the exchange data already netted the fee, leave these columns blank.

--------------------------------------------------------------------------------
5. JSON to CSV Logic Example
Input (from Logic V2):
{
  "pattern": "P2_RUNES_MINT",
  "timestamp": "2024-04-20T14:30:00Z",
  "sent_asset": "BTC",
  "sent_amount": 0.0005,
  "received_asset": "RUNEALPHA",
  "received_amount": 1000,
  "txid": "abc12345"
}
Output (Universal Template Row):
Date (UTC),Platform,Asset Sent,Amount Sent,Asset Received,Amount Received,Fee Currency,Fee Amount,Type,Description,TxHash
04/20/2024 14:30:00,UniSat,BTC,0.0005,RUNEALPHA,1000,,,Trade,Runes Mint detected by Logic V2,abc12345