#include "headers.h"
#include "SimpleConfig.hpp"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include "NetworkUtils.hpp"
#include <vector>
#include <iostream>
#include <string>
#include <chrono>
#include <thread>

using namespace std;

string username;

// Function to handle login to the lobby server and maintain connection
int connectToLobby(const string& ip, const string& port) {
    addrinfo hints{}, *res;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(ip.c_str(), port.c_str(), &hints, &res) != 0) {
        perror("getaddrinfo");
        return -1;
    }
    int fd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (fd < 0) {
        perror("socket");
        freeaddrinfo(res);
        return -1;
    }
    if (connect(fd, res->ai_addr, res->ai_addrlen) != 0) {
        perror("connect");
        close(fd);
        freeaddrinfo(res);
        return -1;
    }
    freeaddrinfo(res);
    return fd;
}

bool login(int fd) {
    string c;
    while (true) {
        cout << "[Lobby] r(register)/l(login)? ";
        cin >> c;
        if (c == "r" || c == "l") break;
        cout << "Invalid choice, please input 'r' or 'l'\n";
    }

    cout << "username: ";
    cin >> username;
    cout << "password: ";
    string pw;
    cin >> pw;

    if (c == "r") {
    tcpSendMsg(fd, "action=register;username=" + username + ";password=" + pw);
        string resp;
    tcpRecvMsg(fd, resp);
        cout << "[Server] " << resp << "\n";
    }

    tcpSendMsg(fd, "action=login;username=" + username + ";password=" + pw);
    string resp;
    tcpRecvMsg(fd, resp);
    cout << "[Server] " << resp << "\n";
    
    if (resp.find("status=ok") != string::npos) {
        return true;
    } else {
        // If login fails, the server might close the connection, or we might want to.
        // For simplicity, we'll rely on the user to restart if login fails and connection drops.
        return false;
    }
}

// Unified game function
void game(int fd, bool startsFirst) {
    vector<char> b(9, ' ');
    auto show = [&]() {
        cout << "\n";
        for (int i = 0; i < 9; i++) {
            cout << (b[i] == ' ' ? '.' : b[i]) << ((i % 3 == 2) ? "\n" : " ");
        }
        cout.flush();
    };

    bool myturn = startsFirst;
    char myChar = startsFirst ? 'X' : 'O';
    char opponentChar = startsFirst ? 'O' : 'X';

    cout << "Game started. You are " << myChar << ". " << (startsFirst ? "You go first." : "Opponent goes first.") << endl;

    auto checkWinner = [&](const vector<char>& board) -> char {
        const int lines[8][3] = {{0, 1, 2}, {3, 4, 5}, {6, 7, 8}, {0, 3, 6}, {1, 4, 7}, {2, 5, 8}, {0, 4, 8}, {2, 4, 6}};
        for (auto& l : lines) {
            if (board[l[0]] != ' ' && board[l[0]] == board[l[1]] && board[l[1]] == board[l[2]]) return board[l[0]];
        }
        for (char c : board) if (c == ' ') return ' ';
        return 'D'; // Draw
    };

    while (true) {
        show();
        if (myturn) {
            int pos;
            cout << "Enter your move (0~8) or use 67 to surrender >:) ";
            cin >> pos;
            if (pos == 67) {
                cout << "You surrendered...\n";
                tcpSendMsg(fd, "action=game_over;result=lose");
                break;
            } else if (pos < 0 || pos > 8 || b[pos] != ' ') {
                cout << "Invalid move!!\n";
                continue;
            }
            b[pos] = myChar;
            tcpSendMsg(fd, "action=move;pos=" + to_string(pos));
            char res = checkWinner(b);
            if (res == myChar) {
                cout << "You win!\n";
                tcpSendMsg(fd, "action=game_over;result=win");
                break;
            } else if (res == 'D') {
                cout << "Draw!\n";
                tcpSendMsg(fd, "action=game_over;result=draw");
                break;
            }
            myturn = false;
        } else {
            cout << "Waiting for opponent's move...\n";
            string msg;
            if (!tcpRecvMsg(fd, msg)) break;
            auto m = parseMessage(msg);
            if (m["action"] == "move") {
                int p = stoi(m["pos"]);
                b[p] = opponentChar;
                char res = checkWinner(b);
                if (res == opponentChar) {
                    show();
                    cout << "You lose...\n";
                    break;
                } else if (res == 'D') {
                    show();
                    cout << "Draw!\n";
                    break;
                }
                myturn = true;
            } else if (m["action"] == "game_over") {
                string r = m["result"];
                if (r == "win") cout << "You lose...\n";
                else if (r == "draw") cout << "Draw!\n";
                else if (r == "lose") cout << "You win!\n";
                break;
            }
        }
    }
}

// Function to scan for players and invite (Player A's role)
void scanAndInvite(const string& lip, const string& lport, const string& sip, int ps, int pe) {
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    timeval tv{1, 0};
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    vector<string> scan_ips;
    // A simple way to handle multiple IPs if they are comma-separated in config
    size_t start = 0, end;
    string ip_list = sip;
    while ((end = ip_list.find(',', start)) != string::npos) {
        scan_ips.push_back(ip_list.substr(start, end - start));
        start = end + 1;
    }
    scan_ips.push_back(ip_list.substr(start));

    cout << "Scanning " << scan_ips.size() << " target(s) on ports " << ps << ".." << pe << "\n";

    for (const auto& target_ip : scan_ips) {
        for (int p = ps; p <= pe; p++) {
            sockaddr_in d{};
            d.sin_family = AF_INET;
            d.sin_port = htons(p);
            inet_pton(AF_INET, target_ip.c_str(), &d.sin_addr);
            string msg = "action=scan";
            sendto(sock, msg.c_str(), msg.size(), 0, (sockaddr*)&d, sizeof(d));
        }
    }

    vector<pair<string, int>> found;
    char buf[256];
    sockaddr_in s;
    socklen_t sl = sizeof(s);
    auto startTime = chrono::steady_clock::now();
    while (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - startTime).count() < 1500) {
        int n = recvfrom(sock, buf, sizeof(buf) - 1, 0, (sockaddr*)&s, &sl);
        if (n > 0) {
            buf[n] = 0;
            auto m = parseMessage(buf);
            if (m["action"] == "available") {
                string ip = inet_ntoa(s.sin_addr);
                int port = ntohs(s.sin_port);
                cout << "Found " << m["username"] << " at " << ip << ":" << port << "\n";
                found.push_back({ip, port});
            }
        }
    }

    if (found.empty()) {
        cout << "No players found. Returning to lobby.\n";
        close(sock);
        return;
    }

    cout << "Choose player index to invite:\n";
    for (int i = 0; i < (int)found.size(); i++) {
        cout << "[" << i << "] " << found[i].first << ":" << found[i].second << "\n";
    }
    int idx;
    cin >> idx;
    if (idx < 0 || idx >= found.size()) {
        cout << "Invalid index. Returning to lobby.\n";
        close(sock);
        return;
    }

    sockaddr_in dest{};
    dest.sin_family = AF_INET;
    inet_pton(AF_INET, found[idx].first.c_str(), &dest.sin_addr);
    dest.sin_port = htons(found[idx].second);
    string inv = "action=invite;from=" + username;
    sendto(sock, inv.c_str(), inv.size(), 0, (sockaddr*)&dest, sizeof(dest));

    timeval tv_inv{10, 0};
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv_inv, sizeof(tv_inv));
    cout << "Invite sent, waiting up to 10 seconds for response...\n";
    char rbuf[256];
    int n = recvfrom(sock, rbuf, sizeof(rbuf) - 1, 0, (sockaddr*)&dest, &sl);

    if (n <= 0) {
        cout << "No reply to invite within timeout. Returning to lobby.\n";
        close(sock);
        return;
    }

    rbuf[n] = 0;
    auto m = parseMessage(rbuf);
    if (m["action"] == "accept") {
        addrinfo hints_tcp{}, *res_tcp;
        hints_tcp.ai_family = AF_UNSPEC;
        hints_tcp.ai_socktype = SOCK_STREAM;
        hints_tcp.ai_flags = AI_PASSIVE;
        getaddrinfo(nullptr, "0", &hints_tcp, &res_tcp);
        int sfd = socket(res_tcp->ai_family, res_tcp->ai_socktype, res_tcp->ai_protocol);
        int yes = 1;
        setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
        ::bind(sfd, res_tcp->ai_addr, res_tcp->ai_addrlen);
        sockaddr_in sa;
        socklen_t slen = sizeof(sa);
        getsockname(sfd, (sockaddr*)&sa, &slen);
        int port = ntohs(sa.sin_port);
        listen(sfd, 1);

        string msg = "action=tcp_info;port=" + to_string(port);
        sendto(sock, msg.c_str(), msg.size(), 0, (sockaddr*)&dest, sizeof(dest));
        cout << "Waiting for TCP connection on port " << port << "...\n";
        int cfd = accept(sfd, nullptr, nullptr);
        cout << "Connected. Starting game.\n";
        game(cfd, true); // Inviter starts first
        close(cfd);
        close(sfd);
        cout << "Game finished. Back to lobby.\n";
    } else {
        cout << "Invitation rejected or invalid response. Returning to lobby.\n";
    }
    close(sock);
}

// Function to wait for an invitation (Player B's role)
void waitForInvitation() {
    int udp_port = 0;
    while (true) {
        cout << "Enter UDP port to listen on (18000-18030): ";
        cin >> udp_port;
        if (cin.fail() || udp_port < 18000 || udp_port > 18030) {
            cout << "Invalid port. Please enter a number between 18000 and 18030.\n";
            cin.clear();
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            continue;
        }
        break;
    }

    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("socket");
        return;
    }
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(udp_port);
    addr.sin_addr.s_addr = INADDR_ANY;
    if (::bind(sock, (sockaddr*)&addr, sizeof(addr)) != 0) {
        perror("bind");
        close(sock);
        return;
    }
    cout << username << " listening for invitations on UDP port: " << udp_port << "\n";

    while (true) {
        char buf[512];
        sockaddr_in sender;
        socklen_t slen = sizeof(sender);
        cout << "Waiting for UDP messages... (To exit, you might need to Ctrl+C)\n";
        int n = recvfrom(sock, buf, sizeof(buf) - 1, 0, (sockaddr*)&sender, &slen);
        if (n <= 0) continue;
        buf[n] = 0;
        auto m = parseMessage(buf);
        string act = m["action"];

        if (act == "scan") {
            string msg = "action=available;username=" + username;
            sendto(sock, msg.c_str(), msg.size(), 0, (sockaddr*)&sender, slen);
        } else if (act == "invite") {
            cout << "Invite from " << m["from"] << ". Accept? (y/n): ";
            string ans;
            cin >> ans;
            if (ans == "y") {
                string ok = "action=accept";
                sendto(sock, ok.c_str(), ok.size(), 0, (sockaddr*)&sender, slen);

                timeval tv_tcp{10, 0};
                setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv_tcp, sizeof(tv_tcp));
                char buf2[256];
                int n2 = recvfrom(sock, buf2, sizeof(buf2) - 1, 0, (sockaddr*)&sender, &slen);
                timeval tv_zero{0, 0}; // Restore blocking
                setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &tv_zero, sizeof(tv_zero));

                if (n2 <= 0) {
                    cout << "Did not receive TCP info from host. Returning to wait mode.\n";
                } else {
                    buf2[n2] = 0;
                    auto m2 = parseMessage(buf2);
                    if (m2["action"] == "tcp_info") {
                        string ip = inet_ntoa(sender.sin_addr);
                        int port = stoi(m2["port"]);
                        addrinfo hints_tcp{}, *res_tcp;
                        hints_tcp.ai_family = AF_UNSPEC;
                        hints_tcp.ai_socktype = SOCK_STREAM;
                        getaddrinfo(ip.c_str(), to_string(port).c_str(), &hints_tcp, &res_tcp);
                        int fd = socket(res_tcp->ai_family, res_tcp->ai_socktype, res_tcp->ai_protocol);
                        if (connect(fd, res_tcp->ai_addr, res_tcp->ai_addrlen) == 0) {
                            cout << "TCP connection successful. Starting game.\n";
                            freeaddrinfo(res_tcp);
                            game(fd, false); // Invitee goes second
                            close(fd);
                            cout << "Game finished. Returning to lobby menu.\n";
                            break; // Exit wait loop and go back to main menu
                        } else {
                            perror("connect");
                            freeaddrinfo(res_tcp);
                            close(fd);
                            cout << "TCP connect failed. Returning to wait mode.\n";
                        }
                    }
                }
            } else {
                string rej = "action=reject";
                sendto(sock, rej.c_str(), rej.size(), 0, (sockaddr*)&sender, slen);
                cout << "Invitation declined. Waiting for new invitations...\n";
            }
        }
    }
    close(sock);
}

void listOnlineUsers(int lobby_fd) {
    tcpSendMsg(lobby_fd, "action=list_users");
    string resp;
    if (tcpRecvMsg(lobby_fd, resp)) {
        auto m = parseMessage(resp);
        if (m["status"] == "ok") {
            cout << "\n--- Online Users ---\n";
            string users = m["users"];
            size_t start = 0, end;
            if (users.empty()) {
                cout << "No other users online." << endl;
            } else {
                while ((end = users.find(',', start)) != string::npos) {
                    cout << "- " << users.substr(start, end - start) << endl;
                    start = end + 1;
                }
                cout << "- " << users.substr(start) << endl;
            }
            cout << "--------------------\n";
        } else {
            cout << "[Error] " << m["message"] << endl;
        }
    } else {
        cout << "Connection to lobby server lost." << endl;
    }
}

int main(int argc, char** argv) {
    string lip = "127.0.0.1", lport = "12000", sip = "127.0.0.1";
    int ps = 18000, pe = 18030;

    string txt = simplecfg::readFile("config.json");
    if (!txt.empty()) {
        lip = simplecfg::getString(txt, "lobby.ip", lip);
        lport = simplecfg::getString(txt, "lobby.port", lport);
        sip = simplecfg::getString(txt, "player.scan_ip", sip); // Using a generic scan_ip
        ps = simplecfg::getInt(txt, "player.port_start", ps);
        pe = simplecfg::getInt(txt, "player.port_end", pe);
    }

    while (true) {
        cout << "Connecting to lobby server..." << endl;
        int lobby_fd = connectToLobby(lip, lport);
        if (lobby_fd < 0) {
            cout << "Failed to connect to lobby server. Retrying in 5 seconds..." << endl;
            this_thread::sleep_for(chrono::seconds(5));
            continue;
        }

        if (!login(lobby_fd)) {
            cout << "Login failed. Please check your credentials or register." << endl;
            close(lobby_fd);
            // Pause before retrying to avoid spamming connection attempts
            this_thread::sleep_for(chrono::seconds(2));
            continue;
        }

        // Main menu loop
        while (true) {
            cout << "\n[Lobby Menu]\n";
            cout << "1. Scan for players (Invite someone)\n";
            cout << "2. Wait for invitation\n";
            cout << "3. List online players\n";
            cout << "4. Logout\n";
            cout << "Choose an option: ";
            string choice;
            cin >> choice;

            if (choice == "1") {
                scanAndInvite(lip, lport, sip, ps, pe);
            } else if (choice == "2") {
                waitForInvitation();
            } else if (choice == "3") {
                listOnlineUsers(lobby_fd);
            } else if (choice == "4") {
                cout << "Good Bye " << username << " (❍ᴥ❍ʋ) !\n";
                tcpSendMsg(lobby_fd, "action=logout;username=" + username);
                string r;
                tcpRecvMsg(lobby_fd, r); // Receive confirmation
                cout << "[Server] " << r << "\n";
                close(lobby_fd);
                break; // Breaks inner loop to go to re-login
            } else {
                cout << "Invalid choice. Please try again.\n";
            }
        }
    }

    return 0;
}
