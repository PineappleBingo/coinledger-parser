CoinLedger와 같은 세금 소프트웨어가 잘못 분류한 비트코인 트랜잭션을 Magic Eden, Runes, Ordinals 등의 최신 패턴을 반영하여 정확히 식별하고 수정하기 위한 **업데이트된 분석 로직 가이드 (v2.0)**입니다.

이 가이드는 기존 로직에 **Magic Eden의 고유한 온체인 지문(Fingerprint)**과 **Runes 프로토콜(OP_RETURN)** 식별 방식을 통합하여 정확도를 대폭 향상시켰습니다.

---

### 1. 트랜잭션 패턴 분석 및 식별 로직 (Pattern Recognition Logic v2.0)

새로운 소스(특히 Magic Eden 및 Runes 관련 자료)를 분석한 결과, 기존 로직에 다음의 **핵심 식별자(Identifiers)**가 추가되어야 합니다.

| 시나리오 (Scenario) | 트랜잭션 패턴 (On-Chain Pattern) | 식별 조건 (Detection Logic) | CoinLedger 수정 액션 |
| :--- | :--- | :--- | :--- |
| **1. Magic Eden 구매**<br>(Buy Now) | **[Sender]** User (`bc1q`/`3...`)<br>**[Outputs]**<br>1. Seller (`bc1q` 등)<br>2. **Marketplace Fee (2%)**<br>3. **Creator Royalty (Optional)**<br>4. User (`bc1p`)로 자산 이동 | 1. **2% 수수료 식별:** Output 중 하나가 Seller에게 간 금액의 정확히 **0.02배**인 Output이 존재함.<br>2. **주소 교차:** Sender(`bc1q`)에서 돈이 나가고, 동일 User의 `bc1p` 주소로 자산(Ordinal/Rune)이 들어옴.<br>3. **플랫폼:** Magic Eden으로 특정 가능. | **Trade**<br>• Type: Buy<br>• Sent: BTC (Total Spent)<br>• Rcvd: [Asset Name]<br>• Description: Magic Eden Buy |
| **2. Magic Eden 판매**<br>(Sell / Offer Accept) | **[Inputs]** User (`bc1p`)의 자산 UTXO<br>**[Outputs]** User (`bc1q`)로 큰 금액 입금 | 1. **Offer Accept:** 판매자가 제안을 수락할 때, 구매자의 자금이 **Multisig** 지갑을 거쳐 들어오는 2단계 트랜잭션이 발생할 수 있음.<br>2. **수수료 공제:** 입금액이 판매가에서 2% + 로열티가 빠진 금액임. | **Trade**<br>• Type: Sell<br>• Sent: [Asset Name]<br>• Rcvd: BTC (Received Amount) |
| **3. Runes Mint/Etch**<br>(룬 생성/발행) | **[OP_RETURN]** "Runestone" 데이터 포함<br>**[Output]** `bc1p`로 자산 이동 | 1. 트랜잭션 Output에 **`OP_RETURN`**이 포함되고, 해당 데이터가 Runes 프로토콜(Tag 13)을 따름.<br>2. 밈풀/탐색기 API에서 `runestone` 필드 확인.<br>3. **Cenotaph(잘못된 룬)** 여부 확인 필요 (Burn 처리됨). | **Trade**<br>• Type: Mint<br>• Sent: BTC (Fees)<br>• Rcvd: [Rune Name] (Qty: N) |
| **4. Magic Eden Offer**<br>(제안/입찰) | **[UTXO Lock]** 지갑 내 UTXO가 PSBT로 서명됨 (Off-chain) | 1. 실제 온체인 트랜잭션은 발생하지 않음 (CoinLedger 수집 불가).<br>2. 단, 해당 UTXO가 다른 곳에 쓰이면 Offer가 취소됨. | **N/A**<br>(수집 대상 아님) |
| **5. Batch Transfer**<br>(대량 전송/스윕) | **[Fee]** 1000 sats (Magic Eden Tracking Fee) | 1. Magic Eden을 통한 전송 시, 추적을 위해 **1000 sats (0.00001 BTC)**의 고정 수수료 Output이 발생함.<br>2. 이를 통해 단순 개인 전송이 아닌 플랫폼 이용 전송임을 식별. | **Transfer**<br>• Fee: 1000 sats + Network Fee |

---

### 2. Python Logic Implementation (Updated Code)

아래 코드는 Magic Eden과 Runes 식별 로직이 추가된 업데이트 버전입니다. `mempool.space` API 구조를 반영하여 로직을 구체화했습니다.

```python
class CryptoTaxAnalyzerV2:
    def __init__(self, user_wallets):
        self.user_wallets = user_wallets # List of user's addresses (bc1q, bc1p, 3...)
        self.taproot_wallets = [w for w in user_wallets if w.startswith('bc1p')]
        self.magic_eden_fee_ratio = 0.02  # 2% Fee identifier
        self.tracking_fee_sats = 1000     # Magic Eden Tracking Fee

    def identify_magic_eden_transaction(self, tx_data):
        """
        Magic Eden 거래 여부를 판단하는 휴리스틱 로직
        """
        outputs = tx_data.get('vout', [])
        
        # 1. 2% 수수료 패턴 확인 (Forensic Marker)
        # 모든 Output 조합 중 B = A * 0.02 관계가 있는지 확인
        amounts = [out['value'] for out in outputs if out['scriptpubkey_type'] != 'op_return']
        for amt in amounts:
            potential_fee = int(amt * self.magic_eden_fee_ratio)
            # 허용 오차(tolerance)를 두어 2% 수수료 Output이 존재하는지 확인
            if any(abs(fee - potential_fee) < 10 for fee in amounts if fee != amt):
                return True, "Magic Eden Buy/Sell (2% Fee Detected)"

        # 2. 1000 sats 추적 수수료 확인 (Batch Transfer)
        if any(out['value'] == self.tracking_fee_sats for out in outputs):
            return True, "Magic Eden Batch Transfer"

        return False, None

    def analyze_transaction(self, tx_data):
        txid = tx_data['txid']
        is_me, me_type = self.identify_magic_eden_transaction(tx_data)
        
        # --- Runes Protocol Detection (New) ---
        # OP_RETURN Output 내 Runestone 데이터 확인
        is_rune = False
        rune_metadata = None
        for out in tx_data.get('vout', []):
            if out['scriptpubkey_type'] == 'op_return':
                # Runestone 매직 바이트 또는 디코딩 로직 (외부 라이브러리/API 필요)
                # 예: mempool.space API는 별도의 필드로 룬 정보를 제공할 수 있음
                if self.check_runestone(out['scriptpubkey_asm']):
                    is_rune = True
                    break
        
        # --- CoinLedger Classification Logic ---
        
        # Case 1: Magic Eden Buy / Rune Mint
        if (is_me or is_rune) and self.is_outgoing(tx_data):
            # 내 지갑에서 BTC가 나갔고, 자산(Runes/Ordinal)이 들어왔거나 ME 거래임
            asset_name = self.fetch_asset_name(txid) # Ordiscan API 호출
            return {
                "Type": "Trade",
                "Asset Sent": "BTC",
                "Amount Sent": self.calculate_total_sent(tx_data),
                "Asset Received": asset_name if asset_name else "Unknown Asset",
                "Amount Received": 1, # 수량 확인 필요 (Runes의 경우 다수일 수 있음)
                "Description": f"{me_type if is_me else 'Rune Mint'}"
            }

        # Case 2: Offer Accept (Sell)
        # Multisig 지갑에서 내 지갑으로 BTC가 들어오는 경우
        if is_me and self.is_incoming(tx_data):
            return {
                "Type": "Trade",
                "Asset Sent": "Check Wallet History", # 판매한 자산명
                "Amount Sent": 1,
                "Asset Received": "BTC",
                "Amount Received": self.calculate_total_received(tx_data),
                "Description": "Magic Eden Sale (Offer Accepted)"
            }

        return None

    def check_runestone(self, script_asm):
        # Runes 프로토콜 식별 (OP_RETURN + 13 + Data)
        return "OP_RETURN OP_PUSHNUM_13" in script_asm or "OP_RETURN 13" in script_asm

    def fetch_asset_name(self, txid):
        # Ordiscan / Hiro API / Mempool.space API 통합
        pass
```

### 3. 개발 및 사용자를 위한 핵심 팁 (Guidelines for App Logic)

앱 로직을 구현할 때 다음 사항들을 반드시 고려해야 합니다.

1.  **API 소스 이원화 전략:**
    *   **Mempool.space API:** 기본 트랜잭션 구조, 수수료, OP_RETURN(`Runestone`) 존재 여부 확인에 최적입니다. 최근 업데이트로 Runes 태깅이 지원됩니다.
    *   **Hiro / Ordiscan API:** 특정 Ordinal Inscription 번호, BRC-20 토큰 이름, 이미지 데이터 등 **"자산의 메타데이터"**를 가져오는 데 필수적입니다.

2.  **주소 역할 분리 인식 (Xverse/Unisat 표준):**
    *   앱은 사용자의 `bc1q`(Payment)와 `bc1p`(Ordinal/Runes) 주소를 모두 입력받아야 합니다.
    *   `bc1q`에서 나가고 `bc1p`로 들어오는 흐름은 99% 확률로 **"자산 구매"** 또는 **"민팅"**입니다. 이를 `Self-Transfer`로 분류하면 안 됩니다.

3.  **CoinLedger Import 포맷 (CSV) 주의사항:**
    *   **Date 포맷:** 반드시 `mm/dd/yyyy hh:mm:ss` (UTC) 형식을 지켜야 합니다.
    *   **Type 필드:** `Trade`는 필수가 아니지만, 입출금(`Deposit`/`Withdrawal`)은 필수입니다. 구매/판매는 무조건 **`Trade`**로 변환하여 출력하세요.
    *   **Ignore 처리:** `bc1p` 주소로 들어오는 `546 sats` 입금 내역은 CoinLedger 상에서 **반드시 `Ignore`** 처리하거나 Trade의 결과물(Received Asset)로 병합하도록 안내해야 합니다.

4.  **Forensic Markers 활용:**
    *   앱 UI에서 "이 거래는 Magic Eden에서 2% 수수료가 발생했으므로 NFT 구매로 추정됩니다."와 같이 사용자에게 **근거를 제시**해주면 신뢰도가 높아집니다.