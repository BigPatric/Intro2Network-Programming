#include "headers.h"
#include "SimpleConfig.hpp"
#include "NetworkUtils.hpp"
#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <mutex>
#include <fstream>

using namespace std;

// Globals

struct ClientState {
    bool is_logged_in = false;
    string username;
    string state = "lobby"; // lobby, waiting, gaming
    int room_id = -1; // -1 表示未進入房間
};

// Game room 結構
struct GameRoom {
    int id;
    vector<string> players; // 玩家 username
    string status; // waiting, gaming
};

map<int, GameRoom> game_rooms; // room_id -> GameRoom
int next_room_id = 1;

map<int, ClientState> clients; // fd -> state
map<string, bool> logged_in_users; // username -> online

string db_server_ip;
string db_server_port;


// Function to forward requests to the DB server
string forward_to_db(const string& request) {
    addrinfo hints{}, *res;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    if (getaddrinfo(db_server_ip.c_str(), db_server_port.c_str(), &hints, &res) != 0) {
        perror("getaddrinfo_db");
        return "status=error;message=DB server connection failed.";
    }

    int fd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (fd < 0) {
        perror("socket_db");
        freeaddrinfo(res);
        return "status=error;message=DB server connection failed.";
    }

    if (connect(fd, res->ai_addr, res->ai_addrlen) != 0) {
        perror("connect_db");
        close(fd);
        freeaddrinfo(res);
        return "status=error;message=DB server connection failed.";
    }
    freeaddrinfo(res);

    tcpSendMsg(fd, request);
    string response;
    tcpRecvMsg(fd, response);
    close(fd);
    return response;
}


void handle_client_msg(int fd) {
    string line;
    if (!tcpRecvMsg(fd, line)) {
        // client disconnected
        if (clients[fd].is_logged_in && !clients[fd].username.empty()) {
            logged_in_users[clients[fd].username] = false;
            cout << "[Lobby] User " << clients[fd].username << " disconnected and was logged out." << endl;
        }
        clients.erase(fd);
        close(fd);
        return;
    }
    cout << "[Lobby] Received: " << line << endl;
    auto m = parseMessage(line);
    string action = m["action"];
    string username = m["username"];
    string response;

    if (action == "register" || action == "login") {
        response = forward_to_db(line);
        if (action == "login" && response.find("status=ok") != string::npos) {
            if (logged_in_users.count(username) && logged_in_users[username]) {
                response = "status=error;message=User already logged in on another client.";
            } else {
                logged_in_users[username] = true;
                clients[fd].is_logged_in = true;
                clients[fd].username = username;
            }
        }
    } else if (action == "logout") {
        if (clients[fd].is_logged_in && !clients[fd].username.empty()) {
            logged_in_users[clients[fd].username] = false;
            clients[fd].is_logged_in = false;
            clients[fd].username.clear();
            response = "status=ok;message=Logout successful.";
        } else {
            response = "status=error;message=Not logged in.";
        }
    } else if (action == "list_users") {
        if (clients[fd].is_logged_in) {
            string user_list;
            for (auto const& [fd2, state] : clients) {
                if (state.is_logged_in) {
                    if (!user_list.empty()) user_list += ";";
                    user_list += state.username + "," + state.state;
                }
            }
            response = "status=ok;users=" + user_list;
        } else {
            response = "status=error;message=Not logged in.";
        }
    } else if (action == "list_rooms") {
        // 查詢所有房間
        string room_list;
        for (auto& [rid, room] : game_rooms) {
            if (!room_list.empty()) room_list += ";";
            room_list += "room_id=" + to_string(room.id) + ",status=" + room.status + ",players=";
            for (size_t i = 0; i < room.players.size(); ++i) {
                room_list += room.players[i];
                if (i + 1 < room.players.size()) room_list += ",";
            }
        }
        response = "status=ok;rooms=" + room_list;
    } else if (action == "create_room") {
        if (clients[fd].is_logged_in && clients[fd].state == "lobby") {
            int rid = next_room_id++;
            GameRoom room;
            room.id = rid;
            room.status = "waiting";
            room.players.push_back(clients[fd].username);
            game_rooms[rid] = room;
            clients[fd].state = "waiting";
            clients[fd].room_id = rid;
            response = "status=ok;room_id=" + to_string(rid);
        } else {
            response = "status=error;message=Cannot create room.";
        }
    } else if (action == "join_room") {
        int rid = stoi(m["room_id"]);
        if (game_rooms.count(rid) && clients[fd].is_logged_in && clients[fd].state == "lobby") {
            game_rooms[rid].players.push_back(clients[fd].username);
            clients[fd].state = "waiting";
            clients[fd].room_id = rid;
            response = "status=ok;room_id=" + to_string(rid);
        } else {
            response = "status=error;message=Cannot join room.";
        }
    } else if (action == "start_game") {
        int rid = clients[fd].room_id;
        if (game_rooms.count(rid) && clients[fd].is_logged_in && clients[fd].state == "waiting") {
            game_rooms[rid].status = "gaming";
            for (auto& uname : game_rooms[rid].players) {
                for (auto& [fd2, state] : clients) {
                    if (state.username == uname) {
                        state.state = "gaming";
                    }
                }
            }
            response = "status=ok;game_started=1";
        } else {
            response = "status=error;message=Cannot start game.";
        }
    } else if (action == "leave_room") {
        int rid = clients[fd].room_id;
        if (game_rooms.count(rid) && clients[fd].is_logged_in && clients[fd].state != "lobby") {
            auto& room = game_rooms[rid];
            room.players.erase(remove(room.players.begin(), room.players.end(), clients[fd].username), room.players.end());
            clients[fd].state = "lobby";
            clients[fd].room_id = -1;
            if (room.players.empty()) game_rooms.erase(rid);
            response = "status=ok;left_room=1";
        } else {
            response = "status=error;message=Cannot leave room.";
        }
    } else {
        response = "status=error;message=Unknown action.";
    }
    tcpSendMsg(fd, response);
}

int main(int argc, char** argv) {
    string lobby_ip = "127.0.0.1";
    string lobby_port = "12000";
    db_server_ip = "127.0.0.1";
    db_server_port = "12001";

    string txt = simplecfg::readFile("config.json");
    if (!txt.empty()) {
        lobby_ip = simplecfg::getString(txt, "lobby.ip", lobby_ip);
        lobby_port = simplecfg::getString(txt, "lobby.port", lobby_port);
        db_server_ip = simplecfg::getString(txt, "db_server.ip", db_server_ip);
        db_server_port = simplecfg::getString(txt, "db_server.port", db_server_port);
    }

    addrinfo hints{}, *res;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

    getaddrinfo(lobby_ip.c_str(), lobby_port.c_str(), &hints, &res);
    int sfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    int yes = 1;
    setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    ::bind(sfd, res->ai_addr, res->ai_addrlen);
    listen(sfd, 10);
    freeaddrinfo(res);

    cout << "[Lobby Server] Listening on " << lobby_ip << ":" << lobby_port << endl;
    cout << "[Lobby Server] Connecting to DB Server at " << db_server_ip << ":" << db_server_port << endl;

    fd_set master, readfds;
    int fdmax = sfd;
    set<int> client_fds;
    FD_ZERO(&master);
    FD_SET(sfd, &master);

    while (true) {
        readfds = master;
        if (select(fdmax + 1, &readfds, nullptr, nullptr, nullptr) == -1) {
            perror("select");
            break;
        }
        for (int i = 0; i <= fdmax; ++i) {
            if (FD_ISSET(i, &readfds)) {
                if (i == sfd) {
                    // new connection
                    int cfd = accept(sfd, nullptr, nullptr);
                    if (cfd < 0) {
                        perror("accept");
                        continue;
                    }
                    cout << "[Lobby Server] Accepted new connection." << endl;
                    FD_SET(cfd, &master);
                    if (cfd > fdmax) fdmax = cfd;
                    client_fds.insert(cfd);
                    clients[cfd] = ClientState();
                } else {
                    // client message
                    handle_client_msg(i);
                    // 若 client 已移除，則從 master set 移除
                    if (clients.find(i) == clients.end()) {
                        FD_CLR(i, &master);
                        client_fds.erase(i);
                    }
                }
            }
        }
    }

    close(sfd);
    return 0;
}