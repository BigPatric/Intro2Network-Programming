# HW2 - Tetris Duo (Python)

本作業為雙人即時對戰俄羅斯方塊，包含 Lobby Server、DB Server、Game Server 與 Client。

## 資料夾結構

```text
hw2/
└── tetris_duo/
    ├── requirements.txt
    ├── config.py
    ├── data.json
    ├── common/
    ├── db_server/
    ├── lobby_server/
    ├── game_server/
    └── game_client/
```

## 執行指引

1) 安裝依賴（可用 uv 或 venv）：

可選一：

```bash
cd /home/runner/work/Intro2Network-Programming/Intro2Network-Programming/hw2/tetris_duo
uv pip install -r requirements.txt
```

可選二：

```bash
cd /home/runner/work/Intro2Network-Programming/Intro2Network-Programming/hw2/tetris_duo
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2) 依序啟動服務（建議三個終端）：

- 啟動 DB Server：`uv run -m db_server.db_server`
- 啟動 Lobby Server：`uv run -m lobby_server.lobby_server`
- 啟動 Client（兩個視窗各跑一次）：`uv run -m game_client.client`

### 簡化路徑：直連模式（不走 Lobby/DB）

1) 啟動 Game Server：`uv run -m game_server.game_server 10002`

2) 兩個終端直連：

- `uv run -m game_client.client --direct 127.0.0.1:10002`
- `uv run -m game_client.client --direct 127.0.0.1:10002`

## 操作

- Left/Right：左右移動
- Down：Soft Drop
- Space：Hard Drop
- Z：Rotate（順時針）
- C：Hold（保留/交換）

## 帳號登入/註冊

- 註冊需輸入名稱與密碼。
- 密碼以 PBKDF2-HMAC-SHA256（100,000 次）加鹽雜湊後儲存於 `data.json`。

## 規格重點

- 2 人對戰、各自棋盤與計分。
- 遊戲邏輯由伺服器統一處理，Client 僅送 INPUT 與渲染 SNAPSHOT。
- 遊戲開始時由 Server 廣播 WELCOME（seed、bagRule）與 TEMPO。
- 結束條件以存活為主，若 60 秒未分勝負，以分數決勝。

## 設定檔

`config.py` 統一管理：

- `LOBBY_HOST`, `LOBBY_PORT`
- `DB_HOST`, `DB_PORT`
- `GAME_PORT_MIN`, `GAME_PORT_MAX`
- `GAME_BIND_HOST`, `GAME_CONNECT_HOST`

## 注意事項

- 等待對戰期間會使用短連線輪詢房間資訊。
- 若修改 `GAME_BIND_HOST`，請同步調整 `GAME_CONNECT_HOST`。
