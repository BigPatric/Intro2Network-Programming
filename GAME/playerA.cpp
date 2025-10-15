#include "headers.h"
#include "SimpleConfig.hpp"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include "NetworkUtils.hpp"
using namespace std;

string username;

bool lobbyLogin(const string& ip,const string& port){
    addrinfo hints{},*res;hints.ai_family=AF_UNSPEC;hints.ai_socktype=SOCK_STREAM;
    getaddrinfo(ip.c_str(),port.c_str(),&hints,&res);
    int fd=socket(res->ai_family,res->ai_socktype,res->ai_protocol);
    connect(fd,res->ai_addr,res->ai_addrlen);freeaddrinfo(res);
    string c;
    while(true){
    cout<<"[Lobby] r(register)/l(login)? ";cin>>c;
    if(c=="r"||c=="l")break;
    cout<<"Invalid choice, please input 'r' or 'l'\n";
    }
    cout<<"username: ";cin>>username;cout<<"password: ";string pw;cin>>pw;
    if(c=="r"){tcpSendLine(fd,"action=register;username="+username+";password="+pw);string r;tcpRecvLine(fd,r);cout<<r<<"\n";}
    tcpSendLine(fd,"action=login;username="+username+";password="+pw);string r;tcpRecvLine(fd,r);cout<<r<<"\n";
    close(fd);return r.find("ok")!=string::npos;
}

void game(int fd){
    vector<char>b(9,' ');auto show=[&](){cout<<"\n";for(int i=0;i<9;i++){cout<<(b[i]==' '?'.':b[i])<<((i%3==2)?"\n":" ");}};
    bool myturn=true;
    auto checkWinner=[&](const vector<char>& board)->char{
        const int lines[8][3] = {{0,1,2},{3,4,5},{6,7,8},{0,3,6},{1,4,7},{2,5,8},{0,4,8},{2,4,6}};
        for(auto &l:lines){
            if(board[l[0]]!=' ' && board[l[0]]==board[l[1]] && board[l[1]]==board[l[2]]) return board[l[0]];
        }
        for(char c:board) if(c==' ') return ' ';
        return 'D';
    };
    cout << "You go first, you are X\n";
    while(true){
        show();
        if(myturn){
            int pos; cout<<"Your move (0~8): "; cin>>pos;
            if(pos<0||pos>8||b[pos]!=' '){cout<<"Invalid\n";continue;}
            b[pos]='X';
            tcpSendLine(fd,"action=move;pos="+to_string(pos));
            // check if this move ends the game
            char res = checkWinner(b);
            if(res=='X'){
                cout<<"You win!\n"; tcpSendLine(fd, "action=game_over;result=win"); break;
            } else if(res=='D'){
                cout<<"Draw!\n"; tcpSendLine(fd, "action=game_over;result=draw"); break;
            }
            myturn=false;
        }else{
            string msg;if(!tcpRecvLine(fd,msg))break;auto m=parseMessage(msg);
            if(m["action"]=="move"){
                int p=stoi(m["pos"]);b[p]='O';
                // check if opponent's move ends the game
                char res = checkWinner(b);
                if(res=='O'){ show(); cout<<"You lose...\n"; break; }
                else if(res=='D'){ show(); cout<<"Draw!\n"; break; }
                myturn=true;
            } else if(m["action"]=="game_over"){
                string r = m["result"];
                if(r=="win") cout<<"You lose...\n";
                else if(r=="draw") cout<<"Draw!\n";
                else if(r=="lose") cout<<"You win!\n";
                break;
            }
        }
    }
}


int main(int argc,char**argv){
    string lip="127.0.0.1", lport="12000", sip="127.0.0.1"; int ps=18000, pe=18030;

    std::string txt = simplecfg::readFile("config.json");
    if(!txt.empty()){
        lip = simplecfg::getString(txt, "lobby.ip", lip);
        lport = simplecfg::getString(txt, "lobby.port", lport);
        sip = simplecfg::getString(txt, "playerA.scan_ip", sip);
        ps = simplecfg::getInt(txt, "playerA.port_start", ps);
        pe = simplecfg::getInt(txt, "playerA.port_end", pe);
    }
    
    if(!lobbyLogin(lip,lport)) return 1;

    while(true){
        cout<<"[Lobby] type 'scan' to search players, 'logout' to exit: ";
        string cmd; cin>>cmd;
        if(cmd=="logout"){
            // perform logout to clear server-side login state
            cout << "Good Bye " << username << " (❍ᴥ❍ʋ) !\n";
            addrinfo hints{},*res;hints.ai_family=AF_UNSPEC;hints.ai_socktype=SOCK_STREAM;
            getaddrinfo(lip.c_str(),lport.c_str(),&hints,&res);
            int fd=socket(res->ai_family,res->ai_socktype,res->ai_protocol);
            connect(fd,res->ai_addr,res->ai_addrlen);freeaddrinfo(res);
            string out = "action=logout;username="+username;
            tcpSendLine(fd,out);
            string r; tcpRecvLine(fd,r); cout<<r<<"\n";
            close(fd);
            // return to login prompt
            if(!lobbyLogin(lip,lport)) return 0;
            continue;
        }
        if(cmd!="scan"){
            cout<<"Unknown command\n"; continue;
        }

        // Prepare UDP socket used for all probes/replies
        int sock=socket(AF_INET,SOCK_DGRAM,0);
        timeval tv{1,0};setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));

        // support multiple scan IPs from config (or single sip)
        std::vector<std::string> scan_ips = {"140.113.17.12", "140.113.17.13", "140.113.17.14"};
        cout<<"Scanning "<<scan_ips.size()<<" target(s) ports "<<ps<<".."<<pe<<"\n";

        // send probes to every target IP and port in the configured ranges
        for(const auto &target_ip : scan_ips){
            for(int p=ps;p<=pe;p++){
                sockaddr_in d{};d.sin_family=AF_INET;d.sin_port=htons(p);inet_pton(AF_INET,target_ip.c_str(),&d.sin_addr);
                string msg="action=scan";sendto(sock,msg.c_str(),msg.size(),0,(sockaddr*)&d,sizeof(d));
            }
        }

        // collect replies for a short window (1500ms)
        vector<pair<string,int>>found;char buf[256];sockaddr_in s; socklen_t sl=sizeof(s);
        auto start=chrono::steady_clock::now();
        while(chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now()-start).count()<1500){
            int n=recvfrom(sock,buf,sizeof(buf)-1,0,(sockaddr*)&s,&sl);
            if(n>0){buf[n]=0;auto m=parseMessage(buf);
                if(m["action"]=="available"){string ip=inet_ntoa(s.sin_addr);int port=ntohs(s.sin_port);
                    cout<<"Found "<<m["username"]<<" at "<<ip<<":"<<port<<"\n";found.push_back({ip,port});}}
        }
        if(found.empty()){cout<<"No players found. Return to lobby."<<"\n"; close(sock); continue;}
        cout<<"Choose index: \n";for(int i=0;i<(int)found.size();i++)cout<<"["<<i<<"] "<<found[i].first<<":"<<found[i].second<<"\n";
        int idx;cin>>idx;if(idx<0||idx>=found.size()){close(sock); cout<<"Invalid index, returning to lobby.\n"; continue;}

        sockaddr_in dest{};dest.sin_family=AF_INET;inet_pton(AF_INET,found[idx].first.c_str(),&dest.sin_addr);dest.sin_port=htons(found[idx].second);
        string inv="action=invite;from="+username;sendto(sock,inv.c_str(),inv.size(),0,(sockaddr*)&dest,sizeof(dest));

        // give the peer more time to accept/decline (10 seconds)
        timeval tv_inv{10,0}; setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,&tv_inv,sizeof(tv_inv));
        cout<<"Invite sent, waiting up to 10 seconds for response...\n";
        char rbuf[256];socklen_t rl=sizeof(dest);int n=recvfrom(sock,rbuf,sizeof(rbuf)-1,0,(sockaddr*)&dest,&rl);

        if(n<=0){cout<<"No reply to invite within timeout, returning to lobby.\n"; close(sock); continue;}
            rbuf[n]=0; auto m=parseMessage(rbuf);
            if(m["action"]=="accept"){
                addrinfo hints{};hints.ai_family=AF_UNSPEC;hints.ai_socktype=SOCK_STREAM;hints.ai_flags=AI_PASSIVE;
                addrinfo*res;getaddrinfo(nullptr,"0",&hints,&res);
                int sfd=socket(res->ai_family,res->ai_socktype,res->ai_protocol);
                int yes=1;setsockopt(sfd,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes)); ::bind(sfd,res->ai_addr,res->ai_addrlen);
                sockaddr_in sa; socklen_t slen=sizeof(sa);getsockname(sfd,(sockaddr*)&sa,&slen);int port=ntohs(sa.sin_port);
                listen(sfd,1);
                string msg="action=tcp_info;port="+to_string(port);
                sendto(sock,msg.c_str(),msg.size(),0,(sockaddr*)&dest,sizeof(dest));
                cout<<"Waiting TCP on port "<<port<<"...\n";
                int cfd=accept(sfd,nullptr,nullptr);
                cout<<"Connected. Start game\n";game(cfd);close(cfd);close(sfd);
                cout<<"Game finished. Back to lobby.\n";
            }else{
                cout<<"Rejected or no response. Return to lobby.\n";
            }
            close(sock);
    }
}
