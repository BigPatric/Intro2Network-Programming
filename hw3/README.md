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
