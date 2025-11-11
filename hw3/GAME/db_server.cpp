#include "headers.h"
#include "SimpleConfig.hpp"
#include "NetworkUtils.hpp"
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <map>
#include <mutex>
#include <thread>
#include <sys/socket.h>
#include <netdb.h>
#include <unistd.h>

using namespace std;

// In-memory database for user accounts, loaded from accounts.json
map<string, string> users;
mutex users_mutex; // Mutex to protect access to the users map and file

// Function to load users from accounts.json
void loadUsers() {
    lock_guard<mutex> guard(users_mutex);
    ifstream f("accounts.json");
    if (!f.is_open()) {
        cout << "[DB Server] accounts.json not found, starting with empty database.\n";
        return;
    }
    string content((istreambuf_iterator<char>(f)), istreambuf_iterator<char>());
    f.close();

    size_t pos = content.find("\"users\"");
    if (pos == string::npos) return;
    pos = content.find('[', pos);
    if (pos == string::npos) return;
    size_t end = content.find(']', pos);
    if (end == string::npos) return;

    string arr = content.substr(pos + 1, end - pos - 1);
    pos = 0;
    while (true) {
        size_t u_pos = arr.find("\"username\"", pos);
        size_t p_pos = arr.find("\"password\"", pos);
        if (u_pos == string::npos || p_pos == string::npos) break;
        size_t u_start = arr.find('\"', u_pos + 10) + 1;
        size_t u_end = arr.find('\"', u_start);
        size_t p_start = arr.find('\"', p_pos + 10) + 1;
        size_t p_end = arr.find('\"', p_start);
        string username = arr.substr(u_start, u_end - u_start);
        string password = arr.substr(p_start, p_end - p_start);
        users[username] = password;
        pos = p_end;
    }
    cout << "[DB Server] Loaded " << users.size() << " users.\n";
}

// Function to save users back to accounts.json
void saveUsers() {
    ofstream f("accounts.json");
    f << "{\n";
    f << "  \"users\": [\n";
    for (auto it = users.begin(); it != users.end(); ++it) {
        f << "    {\n";
        f << "      \"username\": \"" << it->first << "\",\n";
        f << "      \"password\": \"" << it->second << "\"\n";
        f << "    }";
        if (next(it) != users.end()) {
            f << ",\n";
        } else {
            f << "\n";
        }
    }
    f << "  ]\n";
    f << "}\n";
    f.close();
}

void handle_client(int fd) {
    while (true) {
        string msg;
        if (!tcpRecvMsg(fd, msg)) {
            cout << "[DB Server] Client disconnected." << endl;
            break;
        }

        cout << "[DB Server] Received: " << msg << endl;
        auto params = parseMessage(msg);
        string action = params["action"];
        string username = params["username"];
        string password = params["password"];
        string response;

        if (action == "register") {
            lock_guard<mutex> guard(users_mutex);
            if (users.count(username)) {
                response = "status=error;message=Username already exists.";
            } else {
                users[username] = password;
                saveUsers();
                response = "status=ok;message=Register success.";
            }
        } else if (action == "login") {
            lock_guard<mutex> guard(users_mutex);
            if (users.count(username) && users[username] == password) {
                response = "status=ok;message=Login success.";
            } else {
                response = "status=error;message=Invalid username or password.";
            }
        } else {
            response = "status=error;message=Unknown action.";
        }

        if (!tcpSendMsg(fd, response)) {
            cout << "[DB Server] Failed to send response." << endl;
            break;
        }
    }
    close(fd);
}

int main() {
    loadUsers();

    string db_ip = "127.0.0.1";
    string db_port = "12001";

    string txt = simplecfg::readFile("config.json");
    if (!txt.empty()) {
        db_ip = simplecfg::getString(txt, "db_server.ip", db_ip);
        db_port = simplecfg::getString(txt, "db_server.port", db_port);
    }

    addrinfo hints{}, *res;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;

    getaddrinfo(db_ip.c_str(), db_port.c_str(), &hints, &res);
    int sfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    int yes = 1;
    setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    ::bind(sfd, res->ai_addr, res->ai_addrlen);
    listen(sfd, 5);
    freeaddrinfo(res);

    cout << "[DB Server] Listening on " << db_ip << ":" << db_port << endl;

    while (true) {
        int cfd = accept(sfd, nullptr, nullptr);
        if (cfd < 0) {
            perror("accept");
            continue;
        }
        cout << "[DB Server] Accepted new connection." << endl;
        thread(handle_client, cfd).detach();
    }

    close(sfd);
    return 0;
}
