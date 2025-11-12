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

## 規格對應說明

- 2 人對戰、各自棋盤與計分，互不影響。
- 伺服器統一處理所有遊戲邏輯（方塊生成、重力、消行、得分、結束），客戶端只送出 INPUT 並渲染 SNAPSHOT。
- 同步與一致性：
        - 遊戲開始時 Game Server 廣播 WELCOME（包含 seed 與 bagRule='7bag'）與 TEMPO（gravityPlan 固定 dropMs=500）。伺服器以相同 seed 啟動雙方的 7-bag 隨機器，確保序列一致。
        - 以輸入事件驅動，並每 0.5 秒廣播 SNAPSHOT；客戶端採用約 150ms 的渲染緩衝以平滑顯示。
- 結束條件：採用「存活賽」為主；若 30 秒內未分出勝負，以分數較高者勝（作為平手決勝）。
