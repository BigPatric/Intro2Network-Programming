#include "headers.h"
#include "SimpleConfig.hpp"
#include <sys/socket.h>
#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <mutex>
#include <regex>
#include <sstream>
#include <iterator>
#include <cstdio>
#include "NetworkUtils.hpp"
using namespace std;

const char* ACCOUNTS_FILE = "accounts.json";
mutex acc_mtx;
mutex logged_mtx;
map<string,string> accounts;
set<string> logged;

void loadAccounts() {
    lock_guard<mutex> lk_acc(acc_mtx);
    accounts.clear();
    {
        lock_guard<mutex> lk_logged(logged_mtx);
        logged.clear();
    }
    ifstream ifs(ACCOUNTS_FILE);
    if(!ifs) return; // no file yet
    string txt((istreambuf_iterator<char>(ifs)), istreambuf_iterator<char>());
    try{
        // match objects: {"username":"u","password":"p","logged":0}
        std::regex re(R"(\{\s*\"username\"\s*:\s*\"([^\"]+)\"\s*,\s*\"password\"\s*:\s*\"([^\"]+)\"\s*,\s*\"logged\"\s*:\s*(0|1)\s*\})");
        auto begin = std::sregex_iterator(txt.begin(), txt.end(), re);
        auto end = std::sregex_iterator();
        for(auto it = begin; it != end; ++it){
            std::smatch m = *it;
            string u = m[1].str();
            string p = m[2].str();
            int lg = stoi(m[3].str());
            accounts[u] = p;
            if(lg){
                lock_guard<mutex> lk(logged_mtx);
                logged.insert(u);
            }
        }
    } catch(...) {
        // ignore parse errors
    }
}

void saveAccounts() {
    // lock both mutexes safely (std::lock + adopt_lock)
    std::lock(acc_mtx, logged_mtx);
    std::lock_guard<std::mutex> lk1(acc_mtx, std::adopt_lock);
    std::lock_guard<std::mutex> lk2(logged_mtx, std::adopt_lock);

    string tmp = string(ACCOUNTS_FILE) + ".tmp";
    ofstream ofs(tmp, ios::trunc);
    ofs << "{\n  \"users\": [\n";
    bool first = true;
    for(const auto &kv : accounts){
        if(!first) ofs << ",\n";
        first = false;
        const string &u = kv.first;
        const string &p = kv.second;
        int lg = logged.count(u) ? 1 : 0;
        auto esc = [](const string &s){
            string r; for(char c: s){ if(c=='\\' || c=='\"') r.push_back('\\'); r.push_back(c);} return r; };
        ofs << "    {\"username\":\"" << esc(u) << "\", \"password\":\"" << esc(p) << "\", \"logged\": " << lg << " }";
    }
    ofs << "\n  ]\n}\n";
    ofs.close();
    // replace atomically
    std::remove(ACCOUNTS_FILE);
    std::rename(tmp.c_str(), ACCOUNTS_FILE);
}

// handleCommand processes register/login/logout by username; login state is NOT bound to TCP connection
string handleCommand(const string &line) {
    auto m = parseMessage(line);
    string action = m["action"];
    if(action=="register"){
        string u=m["username"], p=m["password"];
        {
            lock_guard<mutex> lk(acc_mtx);
            if(accounts.count(u)) return "status=fail;msg=user_exists";
            accounts[u]=p;
        }
        saveAccounts();
        return "status=ok;msg=register_success";
    } else if(action=="login"){
        string u=m["username"], p=m["password"];
        // check credentials under acc_mtx
        {
            lock_guard<mutex> lk(acc_mtx);
            if(!accounts.count(u)) return "status=fail;msg=not_found";
            if(accounts[u]!=p) return "status=fail;msg=wrong_password";
        }
        // protect logged set
        {
            lock_guard<mutex> lk(logged_mtx);
            if(logged.count(u)) return "status=fail;msg=already_logged";
            logged.insert(u);
        }
        saveAccounts();
        return "status=ok;msg=login_success";
    } else if(action=="logout"){
        string u = m["username"];
        if(u.empty()) return "status=fail;msg=no_username";
        {
            lock_guard<mutex> lk(logged_mtx);
            logged.erase(u);
        }
        saveAccounts();
        return "status=ok;msg=logout_success";
    }
    return "status=fail;msg=unknown_action";
}

void handleClient(int fd){
    string line;
    string cur_user; // 紀錄此 TCP 連線登入的使用者（若有）
    while(tcpRecvLine(fd, line)){
        auto m = parseMessage(line);
        string action = m["action"];
        string resp = handleCommand(line);
        // 若 login 成功，記錄 username；若 logout 成功則清除
        if(action=="login"){
            if(resp.find("status=ok") != string::npos){
                cur_user = m["username"];
            }
        } else if(action=="logout"){
            if(resp.find("status=ok") != string::npos){
                cur_user.clear();
            }
        }
        tcpSendLine(fd, resp);
    }
    // TCP 斷線或讀取失敗時，若這條連線之前登入過就把使用者從 logged 移除
    if(!cur_user.empty()){
        {
            lock_guard<mutex> lk(logged_mtx);
            logged.erase(cur_user);
        }
        saveAccounts();
    }
    close(fd);
}

int main(int argc, char** argv){
    std::string portstr = "12000";
    // Try config.json if no argv
    if(argc>=2) {
        portstr = argv[1];
    } else {
        std::string txt = simplecfg::readFile("config.json");
        if(!txt.empty()){
            int p = simplecfg::getInt(txt, "lobby.port", 0);
            if(p>0) portstr = std::to_string(p);
        }
    }
    loadAccounts();

    addrinfo hints{},*res;
    hints.ai_family=AF_UNSPEC;
    hints.ai_socktype=SOCK_STREAM;
    hints.ai_flags=AI_PASSIVE;
    getaddrinfo(nullptr, portstr.c_str(), &hints, &res);
    int sfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    int yes=1; setsockopt(sfd,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
    ::bind(sfd,res->ai_addr,res->ai_addrlen);
    listen(sfd,10);
    freeaddrinfo(res);
    cout<<"Lobby server on port "<<portstr<<"\n";
    while(true){
        sockaddr_storage caddr; socklen_t clen=sizeof(caddr);
        int cfd = accept(sfd,(sockaddr*)&caddr,&clen);
        thread(handleClient,cfd).detach();
    }
}
