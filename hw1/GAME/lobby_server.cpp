#include "headers.h"
#include "SimpleConfig.hpp"
#include <sys/socket.h>
#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <regex>
#include <sstream>
#include <iterator>
#include <cstdio>
#include "NetworkUtils.hpp"
using namespace std;

const char* ACCOUNTS_FILE = "accounts.json";
map<string, string> accounts;
map<string, int> logged;

// Helper: escape special characters in a string
string escapeString(const string &s) {
    string r; 
    for(char c: s) { 
        if(c == '\\' || c == '\"') r.push_back('\\'); 
        r.push_back(c);
    } 
    return r;
}

// Load accounts from file
void loadAccounts() {
    // No locking needed
    accounts.clear();
    logged.clear();
    ifstream ifs(ACCOUNTS_FILE);
    if(!ifs) return;
    string txt((istreambuf_iterator<char>(ifs)), istreambuf_iterator<char>());
    try {
    // Only match username/password
        std::regex re("\\{\\s*\"username\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"password\"\\s*:\\s*\"([^\"]+)\"\\s*\\}");
        auto begin = std::sregex_iterator(txt.begin(), txt.end(), re);
        auto end = std::sregex_iterator();
        for(auto it = begin; it != end; ++it) {
            std::smatch m = *it;
            string u = m[1].str();
            string p = m[2].str();
            accounts[u] = p;
            logged[u] = 0; // Not logged in initially
        }
    } catch(...) {
    // Ignore parse errors
    }
}

// Save accounts to file
void saveAccounts() {
    // No locking needed
    string tmp = string(ACCOUNTS_FILE) + ".tmp";
    ofstream ofs(tmp, ios::trunc);
    ofs << "{\n  \"users\": [\n";
    bool first = true;
    for(const auto &kv : accounts) {
        if(!first) ofs << ",\n";
        first = false;
        const string &u = kv.first;
        const string &p = kv.second;
        ofs << "    {\"username\":\"" << escapeString(u)
            << "\", \"password\":\"" << escapeString(p)
            << "\"}";
    }
    ofs << "\n  ]\n}\n";
    ofs.close();
    std::remove(ACCOUNTS_FILE);
    std::rename(tmp.c_str(), ACCOUNTS_FILE);
}

// Handle one command and return response
string handleCommand(const string &line) {
    // No locking needed
    auto m = parseMessage(line);
    string action = m["action"];
    string username = m["username"];
    
    if(action == "register") {
        string password = m["password"];
        
        if(accounts.count(username)) {
            return "status=fail;msg=user_exists";
        }
        
        accounts[username] = password;
        saveAccounts();
        return "status=ok;msg=register_success";
        
    } else if(action == "login") {
        string password = m["password"];

        if(!accounts.count(username)) {
            return "status=fail;msg=not_found";
        }
        
        if(accounts[username] != password) {
            return "status=fail;msg=wrong_password";
        }
        
        if(logged[username] != 0) {
            return "status=fail;msg=already_logged";
        }
        logged[username] += 1;
        saveAccounts();
        return "status=ok;msg=login_success";
        
    } else if(action == "logout") {
        if(username.empty()) {
            return "status=fail;msg=no_username";
        }
        
        logged[username] = 0;
        return "status=ok;msg=logout_success";
    }
    
    return "status=fail;msg=unknown_action";
}

// Handle one client connection
void handleClient(int fd) {
    string line;
    string current_user;
    
    while(tcpRecvLine(fd, line)) {
        auto m = parseMessage(line);
        string action = m["action"];
        string username = m["username"];
        
        string response = handleCommand(line);
        
    // Update current user's status for this connection
        if(action == "login" && response.find("status=ok") != string::npos ) {
            current_user = username;
            logged[username] += 1;
        } else if(action == "logout" && response.find("status=ok") != string::npos) {
            if(current_user == username) {
                current_user.clear();
            }
        }
        
        tcpSendLine(fd, response);
    }

    close(fd);
}

int main(int argc, char** argv) {
    string portstr = "12001";
   
    string txt = simplecfg::readFile("config.json");
    if(!txt.empty()) {
        int p = simplecfg::getInt(txt, "lobby.port", 0);
        if(p > 0) portstr = std::to_string(p);
    }
    
    
    // Load account data
    loadAccounts();
    
    // Create server socket (TCP)
    addrinfo hints{}, *res;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM; // TCP
    hints.ai_flags = AI_PASSIVE;
    
    getaddrinfo(nullptr, portstr.c_str(), &hints, &res);
    int sfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol); // TCP socket
    
    int yes = 1; 
    setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    
    ::bind(sfd, res->ai_addr, res->ai_addrlen); // bind TCP socket
    listen(sfd, 10); // listen TCP socket
    freeaddrinfo(res);
    
    cout << "Lobby server running on port " << portstr << "\n";
    
    // Main loop: accept connections (TCP)
    while(true) {
        sockaddr_storage client_addr;
        socklen_t client_len = sizeof(client_addr);
        int client_fd = accept(sfd, (sockaddr*)&client_addr, &client_len); // TCP accept
        handleClient(client_fd); // Call directly, no thread
    }

    return 0;
}