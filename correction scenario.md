제공해주신 소스 파일(이전 Gemini 대화 내역)을 바탕으로, **CoinLedger의 잘못된 표기를 실제 비트코인 지갑(Ordinals/Runes) 내역과 대조하여 수정하는 앱**을 개발하기 위한 핵심 로직을 정리해 드립니다.

이 내용은 크게 **1. 수정이 필요한 4가지 핵심 시나리오**와 **2. 이를 구현하기 위한 코드 로직**으로 구성됩니다.

---

### 1. 수정해야 할 상황별 정리 (Correction Scenarios)

소스에 따르면 CoinLedger는 비트코인 오디널스/룬 거래의 특수성(Dust 전송)을 이해하지 못해 거래를 분리하거나 단순 입출금으로 오인합니다. 앱이 감지해야 할 패턴은 다음과 같습니다.

| 시나리오 (Pattern) | 식별 조건 (Condition) | 해결 방안 (Action Item) | 근거 |
| :--- | :--- | :--- | :--- |
| **1. 구매/민팅 (Mint/Buy)** | **[Withdrawal (큰 금액) + Deposit (546 sats)]**<br>동일 시간대(TxID)에 발생.<br>출금은 가스비+구매가, 입금은 '그릇' 역할의 Dust. | 1. **Deposit** (546 sats) $\rightarrow$ **Ignore (무시)**<br>2. **Withdrawal** $\rightarrow$ **Trade**로 변경<br>• Sent: BTC (출금액)<br>• Received: [자산명]*<br>*(자산명은 TxID로 Ordiscan 조회 필요)* |,,, |
| **2. 가스비 (Gas Fees)** | **[Withdrawal (소액)]**<br>짝이 되는 Deposit이 없음.<br>주로 `-0.000023 BTC` 등의 작은 단위. | 1. **Withdrawal** $\rightarrow$ **Fee (수수료)**로 변경<br>*비용 공제 처리됨* |,, |
| **3. 판매 (Sales)** | **[Deposit (큰 금액)]**<br>짝이 되는 Withdrawal이 없음.<br>단순 입금이 아니라 자산 판매 수익임. | 1. **Deposit** $\rightarrow$ **Trade**로 변경<br>• Sent: [판매한 자산명]<br>• Received: BTC (입금액) |,, |
| **4. 단순 이동 (Transfer)** | **[Withdrawal A + Deposit B]**<br>내 지갑(Fund)에서 내 지갑(Ordinals)으로 이동.<br>금액이 거의 유사함. | 1. 두 내역을 **Merge** $\rightarrow$ **Transfer**로 설정<br>*세금 이벤트 발생 안 함* |,, |
| **5. 대량 민팅 (Bulk Mint)** | **[Withdrawal 1건 + Deposit 여러 건]**<br>예: 546 sats 입금이 3번 동시에 발생. | 1. 모든 **Deposit** $\rightarrow$ **Ignore**<br>2. **Withdrawal** $\rightarrow$ **Trade** (수량: N개) |,, |

---

### 2. 앱 개발을 위한 로직 구현 가이드 (Pseudo Code)

소스 파일의 분석 과정을 자동화하는 알고리즘입니다. 이 로직은 CoinLedger CSV 데이터와 On-chain 데이터(TxID 기준)를 매핑하는 구조입니다.

```python
"""
Crypto Tax Fixer Logic
Based on sources:,,,,
"""

class TransactionFixer:
    def __init__(self, coinledger_data, wallet_addresses):
        self.transactions = coinledger_data  # List of CSV rows
        self.my_wallets = wallet_addresses   # ['bc1p...', 'bc1q...', '3...']

    def analyze_and_suggest_fix(self):
        # 1단계: 트랜잭션을 TxID(또는 시간) 기준으로 그룹화
        grouped_txs = self.group_by_txid(self.transactions)
        
        suggestions = []

        for txid, tx_group in grouped_txs.items():
            
            withdrawals = [t for t in tx_group if t.type == 'Withdrawal']
            deposits = [t for t in tx_group if t.type == 'Deposit']
            
            # --- 시나리오 1 & 5: 구매/민팅 (Split Trade Pattern) ---
            # 조건: 출금 1건 이상 존재 + 입금이 'Dust'(546 sats 등)인 경우
            if withdrawals and all(d.amount <= 0.00001 for d in deposits) and deposits:
                
                # 외부 API(Ordiscan/Mempool)를 통해 실제 자산명 조회
                asset_info = self.fetch_asset_info_from_chain(txid) 
                
                fix_action = {
                    "scenario": "Rune/Ordinal Mint",
                    "action_items": []
                }
                
                # 1. Dust 입금(들)은 무시 처리 (Ignore)
                for dust in deposits:
                    fix_action["action_items"].append({
                        "id": dust.id,
                        "original_type": "Deposit",
                        "new_action": "IGNORE",
                        "reason": "Dust packet (wrapper) for asset"
                    })
                
                # 2. 출금액을 Trade로 변경 (비용 처리)
                total_cost = sum(w.amount for w in withdrawals)
                fix_action["action_items"].append({
                    "id": withdrawals.id, # 대표 ID
                    "original_type": "Withdrawal",
                    "new_action": "CHANGE_TO_TRADE",
                    "sent_asset": "BTC",
                    "sent_amount": total_cost,
                    "received_asset": asset_info.name if asset_info else "Unknown Asset",
                    "received_quantity": len(deposits) # Bulk Mint 대응
                })
                suggestions.append(fix_action)

            # --- 시나리오 2: 단순 가스비 (Unpaired Withdrawal) ---
            # 조건: 소액 출금만 있고 짝이 되는 입금이 없으며, 자산 이동이 아님
            elif withdrawals and not deposits and withdrawals.amount < 0.0005:
                suggestions.append({
                    "scenario": "Gas Fee / Failed Tx",
                    "id": withdrawals.id,
                    "new_action": "CHANGE_TO_FEE",
                    "reason": "Network cost without asset acquisition"
                })

            # --- 시나리오 3: 판매 (Unpaired Large Deposit) ---
            # 조건: 큰 금액 입금만 존재 (상대방이 내 지갑이 아님)
            elif deposits and not withdrawals:
                if self.is_external_sender(txid): # 외부에서 들어온 돈
                    suggestions.append({
                        "scenario": "Asset Sale",
                        "id": deposits.id,
                        "new_action": "CHANGE_TO_TRADE",
                        "sent_asset": "CHECK_WALLET_HISTORY", # 사용자가 입력 필요
                        "received_asset": "BTC",
                        "reason": "Profit from selling Ordinal/Rune"
                    })

            # --- 시나리오 4: 단순 이동 (Self Transfer) ---
            # 조건: 내 지갑 A에서 나가서 내 지갑 B로 들어옴
            elif len(withdrawals) == 1 and len(deposits) == 1:
                if self.is_my_wallet(withdrawals.to_address): 
                    suggestions.append({
                        "scenario": "Self Transfer",
                        "ids": [withdrawals.id, deposits.id],
                        "new_action": "MERGE_AS_TRANSFER",
                        "reason": "Moving funds between own wallets"
                    })

        return suggestions

    def fetch_asset_info_from_chain(self, txid):
        # Ordiscan 등의 API를 호출하여 해당 TxID가 
        # Inscription이나 Rune Mint인지 확인하고 이름을 반환
        pass

```

### 3. 개발 시 핵심 고려사항 (Tips from Sources)

1.  **TxID 필수:** CoinLedger 데이터에 TxID가 없다면 정확도가 떨어집니다. 이 경우 `날짜/시간 + 금액`으로 매칭해야 합니다.
2.  **Dust 기준값:** 보통 `546 sats (0.00000546 BTC)`가 가장 많지만, `330 sats` 등 다른 경우도 있으니 `0.00001 BTC` 이하를 Dust로 간주하는 유연성이 필요합니다.
3.  **Ignore의 중요성:** 사용자가 UI에서 Dust Deposit을 단순히 삭제하는 것이 아니라 **"Ignore(무시)"** 처리하도록 안내해야 합니다. 그래야 나중에 자산 매도 시 취득 원가가 0원으로 잡히는 세금 폭탄을 막을 수 있습니다.
4.  **외부 링크 제공:** 사용자가 직접 확인할 수 있도록 `Ordiscan` 바로가기 링크를 제공하는 기능을 앱에 포함하면 좋습니다.