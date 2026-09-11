# HW3 - Game Store System (Python)

HW3 目前僅使用 `Network_Final`（Python）版本。

## 功能整體介紹

HW3 是一個「遊戲平台系統」，以 TCP 連線整合三種角色：玩家端、開發者端、與後端伺服器。  
整體流程如下：

1. 使用者（玩家/開發者）先登入系統。
2. 開發者可上傳與更新遊戲內容，維護平台上的遊戲資料。
3. 玩家可瀏覽遊戲、建立或加入房間，並在房間內啟動遊戲。
4. 伺服器負責連線管理、遊戲大廳/開發者服務邏輯，並透過 DB Server 存取資料庫。

換句話說，HW3 的核心目標是：建立一個支援「遊戲上架」與「玩家連線遊玩」的完整網路平台雛形。

### 範例遊戲與 UI 模組

- 範例遊戲：`test_game/Chess/`（`config.json` 內容描述為「簡單五子棋」，方向鍵移動、Enter 落子）。
- 玩家端 UI：`player/lobby_gui.py`，使用 `tkinter`（`tk`, `messagebox`, `simpledialog`）。
- 開發者端 UI：`developer/developer_gui.py`，使用 `tkinter`（`tk`, `filedialog`, `messagebox`）。

## 資料夾結構

```text
hw3/
└── Network_Final/
    ├── clean_pycache.sh
    ├── common/
    ├── database/
    ├── server/
    ├── developer/
    ├── player/
    └── test_game/
```

## 各目錄功能與關鍵檔案

| 目錄 | 功能 | 關鍵檔案 / 函式 |
|---|---|---|
| `common/` | 共用通訊與設定 | `protocol.py`：`send_json`/`recv_json`（JSON 封包）、`send_file`/`recv_file`（檔案傳輸）；`ip_port_config.py`：集中管理 IP/Port |
| `database/` | DB Server 與 SQLite 初始化 | `db_server.py`：啟動 DB socket 服務、處理 `select/insert/update/delete`；`initialize.py`：建立初始資料 |
| `server/` | 主伺服器與業務邏輯分派 | `server_main.py`：接收連線並依 `role` 分派；`lobby_service.py`：玩家登入、商城、房間、啟動遊戲；`developer_service.py`：上傳/更新遊戲；`connection_manager.py`：管理在線連線 |
| `developer/` | 開發者端客戶端（上架工具） | `developer_gui.py`：GUI 介面；`dev_client.py`：登入註冊、壓縮上傳、更新遊戲 |
| `player/` | 玩家端客戶端（大廳與遊戲啟動） | `lobby_gui.py`：玩家 GUI；`lobby_client.py`：登入註冊、下載遊戲、建立/加入房間、接收 `start_game` 並啟動遊戲 client |
| `test_game/` | 範例可上傳遊戲內容 | `Chess/client.py`（玩家端程式）、`Chess/game_server.py`（遊戲房間伺服器）、`Chess/config.json`（遊戲名稱、版本、描述等 metadata） |

## 執行前準備

```bash
cd /home/runner/work/Intro2Network-Programming/Intro2Network-Programming/hw3/Network_Final
```

### 清除快取

```bash
chmod +x clean_pycache.sh
./clean_pycache.sh
```

### 初始化資料庫

```bash
python3 ./database/initialize.py
```

## 啟動方式

- Server：`python3 ./server/server_main.py`
- Developer Client：`python3 ./developer/developer_gui.py`
- Player Lobby Client：`python3 ./player/lobby_gui.py`

## 架構概述

- Server 採分層設計：`server_main.py`、`connection_manager.py`、`developer_service.py`、`lobby_service.py`、`db_manager.py`。
- 開發者端與玩家端皆透過 TCP 長連線與伺服器互動。
- DB Server 專責資料庫 CRUD，主伺服器透過 socket 與其溝通。

## 角色職責

- 玩家：登入、瀏覽遊戲、建立/加入房間、啟動並遊玩遊戲。
- 開發者：登入、上傳與更新遊戲內容。

## 網路設定

可在 `common/ip_port_config` 調整相關 IP/Port。
