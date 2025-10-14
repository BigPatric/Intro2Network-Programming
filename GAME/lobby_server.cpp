#include "headers.h"
#include "SimpleConfig.hpp"
#include <sys/socket.h>
#include <netdb.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <mutex>
#include "NetworkUtils.hpp"
using namespace std;

const char* ACCOUNTS_FILE = "accounts.txt";
mutex acc_mtx;
map<string,string> accounts;
set<string> logged;

void loadAccounts() {
    ifstream ifs(ACCOUNTS_FILE);
    string u,p;
    while(ifs >> u >> p) accounts[u]=p;
}
void saveAccounts() {
    ofstream ofs(ACCOUNTS_FILE);
    for(auto &kv:accounts) ofs<<kv.first<<" "<<kv.second<<"\n";
}

// handleCommand now receives a reference to currentUser for this connection
string handleCommand(const string &line, string &currentUser) {
    auto m = parseMessage(line);
    string action = m["action"];
    if(action=="register"){
        string u=m["username"], p=m["password"];
        lock_guard<mutex> lk(acc_mtx);
        if(accounts.count(u)) return "status=fail;msg=user_exists";
        accounts[u]=p; saveAccounts();
        return "status=ok;msg=register_success";
    } else if(action=="login"){
        string u=m["username"], p=m["password"];
        lock_guard<mutex> lk(acc_mtx);
        if(!accounts.count(u)) return "status=fail;msg=not_found";
        if(accounts[u]!=p) return "status=fail;msg=wrong_password";
        if(logged.count(u)) return "status=fail;msg=already_logged";
        logged.insert(u);
        currentUser = u; // associate this connection with the logged-in user
        return "status=ok;msg=login_success";
    } else if(action=="logout"){
        string u=m["username"];
        lock_guard<mutex> lk(acc_mtx);
        logged.erase(u);
        if(currentUser == u) currentUser.clear();
        return "status=ok;msg=logout_success";
    }
    return "status=fail;msg=unknown_action";
}

void handleClient(int fd){
    string line;
    string currentUser; // track which user (if any) is associated with this connection
    while(tcpRecvLine(fd, line)){
        string resp = handleCommand(line, currentUser);
        tcpSendLine(fd, resp);
    }
    // connection closed or error -> ensure we cleanup logged state for this user
    if(!currentUser.empty()){
        lock_guard<mutex> lk(acc_mtx);
        if(logged.count(currentUser)){
            logged.erase(currentUser);
            cout<<"Cleanup: user "<<currentUser<<" logged out due to disconnect"<<"\n";
        }
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
