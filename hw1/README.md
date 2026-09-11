# HW1 - Two-Player Online Game (C++)

本作業實作一個雙人網路連線遊戲，包含 Lobby Server、Player A、Player B。

## 資料夾結構

```text
hw1/
├── GAME/
│   ├── Makefile
│   ├── NetworkUtils.hpp
│   ├── SimpleConfig.hpp
│   ├── headers.h
│   ├── config.json
│   ├── accounts.json
│   ├── lobby_server.cpp
│   ├── playerA.cpp
│   └── playerB.cpp
└── README.md
```

## 啟動方式

```bash
cd /home/runner/work/Intro2Network-Programming/Intro2Network-Programming/hw1/GAME
make
```

建議開三個終端：

1. 啟動 Lobby Server：`./lobby_server`
2. 啟動 Player B：`./playerB`
3. 啟動 Player A：`./playerA`

## 備註

- 主要使用 TCP/UDP 進行 Lobby、邀請與對戰連線流程。
- 連線參數可調整 `config.json` / `SimpleConfig.hpp`。
