# HW3 - Game Store System (Python)

HW3 目前僅使用 `Network_Final`（Python）版本。

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
