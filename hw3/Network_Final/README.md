# Guidance and Explanation From 112550018

## Some Notes

可以在

```
/common/ip_port_config
```

設定相關 ip and port
在運行之前幫我確認是在 Network_Final/

## 啟動 Developer

```
python3 ./developer/dev_client.py
```

## 啟動 Player

```
python3 ./player/lobby_client.py
```

## 互動模式說明

本系統包含三種主要角色：Server、Developer Client（開發者端）、Lobby Client（玩家端）。各角色間的互動流程如下：

### 1. Developer Client 與 Server

- 開發者登入後，可將遊戲壓縮檔上傳至 Server。
- Server 驗證開發者身分，接收遊戲檔案並儲存於伺服器端，更新遊戲資料庫。
- 開發者可查詢、更新自己上架的遊戲資訊。

### 2. Lobby Client 與 Server

- 玩家登入/註冊後，可查詢遊戲商城、下載遊戲。
- 玩家可建立房間或加入現有房間，所有房間資訊由 Server 管理。
- 當房主選擇啟動遊戲時，Server 會動態啟動對應的 Game Server，並通知所有房間成員連線。

### 3. Lobby Client 之間的互動

- 玩家之間不直接通訊，所有房間管理、配對、遊戲啟動等訊息皆透過 Server 中介。
- 當遊戲開始後，各玩家的遊戲客戶端會連線到同一個 Game Server 進行遊戲內通訊。

### 4. 資料傳輸協定

- 所有 Client 與 Server 之間的通訊皆採用 TCP Socket，資料格式以 JSON 為主，方便擴充與除錯。
- 遊戲檔案上傳/下載則採用分段傳輸，確保大檔案穩定傳送。

---

### Server

-負責處理 player 跟 developer 的請求，並為 player handle game server

### Player

### Developer

### 互動流程圖（簡述）

```
Developer Client <----> Server <----> Lobby Client
                                 |
                                 +----> Game Server（遊戲啟動時動態產生）
```

- **開發者**與**Server**互動：遊戲上架、更新。
- **玩家**與**Server**互動：登入、查詢、下載、房間管理。
- **玩家**間互動：透過 Server 進行房間配對與遊戲啟動，遊戲內則連線到 Game Server。

---
