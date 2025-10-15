# Program Overview: Network Game Lobby and Player System

This project implements a simple networked game system with a lobby server and two player clients (PlayerA and PlayerB). The system allows users to register, log in, discover other players, and play a turn-based game (e.g., Tic-Tac-Toe) over the network.

## Components

### 1. Lobby Server (`lobby_server.cpp`)
- Manages user accounts (register, login, logout) using TCP.
- Stores account data in `accounts.json`.
- Handles multiple client connections sequentially.
- Responds to registration and login requests, and tracks logged-in users.

### 2. PlayerA Client (`playerA.cpp`)
- Connects to the lobby server for registration and login.
- Can scan the network for available players using UDP broadcast.
- Initiates game invitations to other players.
- Hosts the game as server if invitation is accepted.
- Handles the game logic and user interface for PlayerA (goes first, 'X').

### 3. PlayerB Client (`playerB.cpp`)
- Connects to the lobby server for registration and login.
- Waits for invitations from other players via UDP.
- Accepts or rejects invitations, then connects to the game as a client.
- Handles the game logic and user interface for PlayerB (goes second, 'O').

### 4. Shared Utilities
- `NetworkUtils.hpp`: Helper functions for message parsing, TCP/UDP send/receive.
- `SimpleConfig.hpp`: Simple config file reader for JSON-like settings.
- `headers.h`: Common C++ includes for all files.

## Workflow
1. **User Registration/Login:**
   - Both players use the lobby server to register and log in with a username and password.
2. **Player Discovery:**
   - PlayerA scans the network for available PlayerB clients using UDP.
   - PlayerB listens for scan requests and responds with availability.
3. **Game Invitation:**
   - PlayerA sends an invitation to a discovered PlayerB.
   - PlayerB accepts or rejects the invitation.
4. **Game Session:**
   - If accepted, a TCP connection is established for the game.
   - Players take turns making moves. The game ends with win, lose, draw, or surrender.
5. **Logout:**
   - Players can log out, which updates their status on the lobby server.

## Configuration
- `config.json` stores server IP, port, and other settings.
- `accounts.json` stores user credentials.

## How to Run
1. Start the lobby server: `./lobby_server`
2. Start PlayerA and PlayerB clients on different terminals or machines.
3. Follow prompts to register, log in, scan, invite, and play.

---

This document provides a high-level overview. For details, see code comments and each source file.
