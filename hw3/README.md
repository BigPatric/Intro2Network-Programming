# HW3 - Game Store System

HW3 目前包含兩個版本：`GAME`（C++）與 `Network_Final`（Python）。

## 資料夾結構

```text
hw3/
├── GAME/
│   ├── Makefile
│   ├── NetworkUtils.hpp
│   ├── SimpleConfig.hpp
│   ├── headers.h
│   ├── config.json
│   ├── accounts.json
│   ├── lobby_server.cpp
│   ├── db_server.cpp
│   └── client.cpp
├── Network_Final/
│   ├── README.md
│   ├── clean_pycache.sh
│   ├── common/
│   ├── database/
│   ├── server/
│   ├── developer/
│   ├── player/
│   └── test_game/
└── README.md
```

## 子項目說明

### 1) GAME（C++）

```bash
cd /home/runner/work/Intro2Network-Programming/Intro2Network-Programming/hw3/GAME
make
```

執行檔：
- `./lobby_server`
- `./db_server`
- `./client`

### 2) Network_Final（Python）

請參考既有文件：`/hw3/Network_Final/README.md`。
