# HW2 - Tetris Duo (Python)

本作業為雙人即時對戰俄羅斯方塊，包含 Lobby Server、DB Server、Game Server 與 Client。

## 資料夾結構

```text
hw2/
├── tetris_duo/
│   ├── requirements.txt
│   ├── config.py
│   ├── data.json
│   ├── README.md
│   ├── common/
│   ├── db_server/
│   ├── lobby_server/
│   ├── game_server/
│   └── game_client/
└── README.md
```

## 快速開始

```bash
cd /home/runner/work/Intro2Network-Programming/Intro2Network-Programming/hw2/tetris_duo
pip install -r requirements.txt
```

依序啟動：

1. `python -m db_server.db_server`
2. `python -m lobby_server.lobby_server`
3. 開兩個視窗執行：`python -m game_client.client`

## 延伸說明

- 更完整的流程、協定與玩法請見：`/tetris_duo/README.md`
