# Tetris Duo 遊戲

## 執行指引

1) 安裝依賴（可用 uv 或 venv）：

     可選一：
     uv pip install -r requirements.txt

     可選二：
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt

2) 依序啟動服務（建議用三個終端視窗）：

     - 啟動 DB Server：
         uv run -m db_server.db_server

     - 啟動 Lobby Server：
         uv run -m lobby_server.lobby_server

        - 啟動 Client（兩個視窗各跑一次，先註冊再登入，使用 Lobby 建房/加房）：
            uv run -m game_client.client

### 簡化路徑：直連模式（不走 Lobby/DB）

    1) 直接啟動 Game Server（預設等待兩人連線）：
        uv run -m game_server.game_server 10002

    2) 在兩個終端視窗各自啟動 Client 並直連：
        uv run -m game_client.client --direct 127.0.0.1:10002
        uv run -m game_client.client --direct 127.0.0.1:10002

    這種方式最簡單，避免 Lobby/DB 造成的相依問題，特別適合本地快速測試。

## 操作

- Left/Right：左右移動
- Down：Soft Drop
- Space：Hard Drop
- Z：Rotate（順時針）
- C：Hold（保留/交換）

## 帳號登入/註冊（新增：密碼）

- 註冊時需輸入「名稱」與「密碼」，密碼將以 PBKDF2-HMAC-SHA256（100,000 次）加鹽雜湊後儲存於本地 data.json。
- 登入時需輸入對應密碼；舊有（尚未設定密碼）的帳號可用「空密碼」登入，建議重新註冊以啟用密碼。

## 規格對應說明

- 2 人對戰、各自棋盤與計分，互不影響。
- 伺服器統一處理所有遊戲邏輯（方塊生成、重力、消行、得分、結束），客戶端只送出 INPUT 並渲染 SNAPSHOT。
- 同步與一致性：
        - 遊戲開始時 Game Server 廣播 WELCOME（包含 seed 與 bagRule='7bag'）與 TEMPO（gravityPlan 固定 dropMs=500）。伺服器以相同 seed 啟動雙方的 7-bag 隨機器，確保序列一致。
        - 以輸入事件驅動，並每 0.5 秒廣播 SNAPSHOT；客戶端採用約 150ms 的渲染緩衝以平滑顯示。
- 結束條件：採用「存活賽」為主；若 60 秒內未分出勝負，以分數較高者勝（作為平手決勝）。

## 新增功能與設定（本次更新）

1. 防止重複登入：同一帳號同時只能有一個有效 Lobby 連線。第二個登入請求會收到 `already logged in elsewhere` 錯誤訊息。
2. 對局結束返回房間：Game Server 對局結束時會向雙方廣播 `GAME_OVER`。Client 進入房間後的「再戰 / 離開房間」選單，房主可直接啟動下一局，玩家可選擇退出回 Lobby。
3. 統一設定檔：新增 `config.py`，集中所有 Host/Port 常數：
     - `LOBBY_HOST`, `LOBBY_PORT`
     - `DB_HOST`, `DB_PORT`
     - `GAME_PORT_MIN`, `GAME_PORT_MAX`（動態建立 Game Server 埠範圍）
     - `GAME_BIND_HOST`（Game Server 綁定位址）
     - `GAME_CONNECT_HOST`（Client 連線位址）

修改埠或部署位址時僅需調整 `config.py`，其餘程式碼自動引用。

### GAME_OVER 訊息格式範例

        {
            "type": "GAME_OVER",
            "winner": "Alice",       // 平手為 null
            "summary": {
                "Alice": {"score": 1200, "lines": 10},
                "Bob":   {"score": 800,  "lines": 8}
            }
        }

### 再戰流程簡述

1. 兩位玩家完成一局 -> Client 顯示成績。
2. 房主在房間選單選擇「再戰」，向 Lobby 發送 `start_game` 取得新的 game_port。
3. 雙方重新連線至新的 Game Server，房間保持人員不變。
4. 可重複再戰；若任一方選擇退出，返回 Lobby 選單。

## 設定調整範例

若需在同一主機開多組服務，可複製專案並於各副本修改 `config.py` 中的 `LOBBY_PORT`, `DB_PORT` 及遊戲埠範圍避免衝突，例如：

    LOBBY_PORT = 12000
    DB_PORT = 12001
    GAME_PORT_MIN = 12002
    GAME_PORT_MAX = 13000

## 注意事項

- 客戶端等待對戰時仍會使用短連線輪詢房間資訊；這些短連線不會建立長期登入狀態，因此不會觸發重複登入限制。
- 若修改 `GAME_BIND_HOST` 讓伺服器於公網暴露，請同時調整 `GAME_CONNECT_HOST` 供 Client 正確連線。
- 日後可擴充 `config.py` 加入 TLS、LOG_LEVEL 等設定參數。
