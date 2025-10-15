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

// 辅助函数：转义字符串中的特殊字符
string escapeString(const string &s) {
    string r; 
    for(char c: s) { 
        if(c == '\\' || c == '\"') r.push_back('\\'); 
        r.push_back(c);
    } 
    return r;
}

void loadAccounts() {
    // 不需要加鎖
    accounts.clear();
    logged.clear();
    ifstream ifs(ACCOUNTS_FILE);
    if(!ifs) return;
    string txt((istreambuf_iterator<char>(ifs)), istreambuf_iterator<char>());
    try {
        // 只匹配 username/password
        std::regex re("\\{\\s*\"username\"\\s*:\\s*\"([^\"]+)\"\\s*,\\s*\"password\"\\s*:\\s*\"([^\"]+)\"\\s*\\}");
        auto begin = std::sregex_iterator(txt.begin(), txt.end(), re);
        auto end = std::sregex_iterator();
        for(auto it = begin; it != end; ++it) {
            std::smatch m = *it;
            string u = m[1].str();
            string p = m[2].str();
            accounts[u] = p;
            logged[u] = 0; // 初始未登录
        }
    } catch(...) {
        // 忽略解析錯誤
    }
}

void saveAccounts() {
    // 不需要加鎖
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

string handleCommand(const string &line) {
    // 不需要加鎖
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

void handleClient(int fd) {
    string line;
    string current_user;
    
    while(tcpRecvLine(fd, line)) {
        auto m = parseMessage(line);
        string action = m["action"];
        string username = m["username"];
        
        string response = handleCommand(line);
        
        // 更新当前连接的用户状态
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
    
    
    // 加载账户数据
    loadAccounts();
    
    // 创建服务器套接字
    addrinfo hints{}, *res;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_flags = AI_PASSIVE;
    
    getaddrinfo(nullptr, portstr.c_str(), &hints, &res);
    int sfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    
    int yes = 1; 
    setsockopt(sfd, SOL_SOCKET, SO_REUSEADDR, &yes, sizeof(yes));
    
    ::bind(sfd, res->ai_addr, res->ai_addrlen);
    listen(sfd, 10);
    freeaddrinfo(res);
    
    cout << "Lobby server running on port " << portstr << "\n";
    
    // 主循环接受连接
    while(true) {
        sockaddr_storage client_addr;
        socklen_t client_len = sizeof(client_addr);
        int client_fd = accept(sfd, (sockaddr*)&client_addr, &client_len);
        handleClient(client_fd); // 直接呼叫，不用 thread
    }
    
    return 0;
}