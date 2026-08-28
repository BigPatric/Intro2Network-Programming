# homework1 Two-Player Online Game
  Implementing a simple online game
  Starting with a lobby server that stores each player’s unique ID and password information, 
  players can log in or register via the TCP protocol. Next, you will implement two types of players, 
  referred to as Player A and Player B for simplicity. Both players must log in to the lobby server 
  and obtain authorization before proceeding to the next steps.
  
  Player B listens on a port in specific range using the UDP protocol, waiting for game invitations from Player A. 
  Player A scans the same range of ports via UDP, selects one of the available Player B, and sends an invitation.
  Once Player B accepts the invitation, Player A initializes a TCP listener and replies with the connection information to Player B. 
  Player B then joins the game using the provided information, and the two players can start playing.
<img width="1577" height="1668" alt="image" src="https://github.com/user-attachments/assets/a16068f4-df0f-4e53-bed1-68be80e317b4" />

# homework2 雙人即時對戰遊戲設計與實作（雙人俄羅斯方塊）
  
  <img width="1182" height="948" alt="image" src="https://github.com/user-attachments/assets/c5a10a2f-be36-4c78-b1c2-4a8079e54ba8" />
  
# homework3：Game Store System
建立一個讓開發者可以管理自己遊戲的系統。開發者可以在這個平台上：

1. 上傳遊戲
    1. 雙人 CLI 遊戲
    2. 雙人 GUI 遊戲
    3. 多人以上之小遊戲
2. 更新遊戲（版本更新）
3. 下架遊戲

為了讓遊戲被上傳後可以在大廳端穩定啟動，你需要設計一套**統一的遊戲規格**（例如檔案結構、啟動方式、必要的介面等），讓不同開發者寫出的遊戲都能被同一套平台正確管理與啟動。

2. **優化遊戲大廳與商城平台**
    
    你需要提供一個介面，讓玩家可以：
    
    1. 瀏覽目前大廳狀態
        - 玩家列表
        - 房間列表
        - 上架遊戲列表
    2. 建立房間並遊玩遊戲
    3. 瀏覽商城中的遊戲
        1. 檢視遊戲詳細資訊（例如：名稱、作者、版本、簡介等）
        2. 為遊戲評分與撰寫評論
    
    整個大廳與商城的體驗應該讓使用者能「看得懂現在有哪些遊戲、有哪些房間、有哪些玩家正在做什麼」，並且可以順利完成選擇遊戲 → 建立房間 → 進入遊戲的流程。
    
3. **支援玩家自由遊玩與更新遊戲版本**
    
    玩家在遊玩遊戲之前，會先從商城下載最新版本的遊戲。系統需要支援：
    
    1. 遊玩前下載對應遊戲，或自動更新至該遊戲的最新版本
    2. 在遊玩時，自動啟動對應的 game client，並連線至 server 端已啟動的 game server
    3. 遊玩結束後，自動釋放相關資源，並回到房間或大廳等待狀態
