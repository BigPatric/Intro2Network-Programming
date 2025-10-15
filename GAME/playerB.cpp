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
    addrinfo hints{},*res;
    hints.ai_family=AF_UNSPEC; hints.ai_socktype=SOCK_STREAM;
    if(getaddrinfo(ip.c_str(),port.c_str(),&hints,&res)!=0){ perror("getaddrinfo"); return false; }
    int fd = socket(res->ai_family,res->ai_socktype,res->ai_protocol);
    if(fd < 0){ perror("socket"); freeaddrinfo(res); return false; }
    if(connect(fd,res->ai_addr,res->ai_addrlen)!=0){ perror("connect"); close(fd); freeaddrinfo(res); return false; }
    freeaddrinfo(res);
    string c;
    while(true){
       cout<<"[Lobby] r(register)/l(login)? "; cin>>c;
        if(c=="r"||c=="l")break;
        else{cout<<"Invalid choice, please input 'r' or 'l'\n"; continue;}  
    }
    
    cout<<"username: ";cin>>username; cout<<"password: ";string pw;cin>>pw;
    if(c=="r"){ tcpSendLine(fd,"action=register;username="+username+";password="+pw); string resp; tcpRecvLine(fd,resp); cout<<resp<<"\n"; }
    tcpSendLine(fd,"action=login;username="+username+";password="+pw);
    string resp; tcpRecvLine(fd,resp); cout<<resp<<"\n";
    close(fd);
    return resp.find("ok")!=string::npos;
}

void game(int fd){
    vector<char> b(9,' ');
    auto show=[&](){cout<<"\n";for(int i=0;i<9;i++){cout<<(b[i]==' '?'.':b[i])<<((i%3==2)?"\n":" ");}cout.flush();};
    bool myturn=false;
    auto checkWinner=[&](const vector<char>& board)->char{
        const int lines[8][3] = {{0,1,2},{3,4,5},{6,7,8},{0,3,6},{1,4,7},{2,5,8},{0,4,8},{2,4,6}};
        for(auto &l:lines){
            if(board[l[0]]!=' ' && board[l[0]]==board[l[1]] && board[l[1]]==board[l[2]]) return board[l[0]];
        }
        for(char c:board) if(c==' ') return ' ';
        return 'D';
    };
    cout << "You go next, you are O\n";
    while(true){
        show();
        if(myturn){
            int pos; cout<<"Enter your move (0~8) or use 67 to surrender >:) "; cin>>pos;
            if(pos==67){ cout<<"You surrendered...\n"; tcpSendLine(fd, "action=game_over;result=lose"); break; }
            else if(pos<0||pos>8||b[pos]!=' '){cout<<"Invalid move!!\n";continue;}
            b[pos]='O';
            tcpSendLine(fd,"action=move;pos="+to_string(pos));
            // check if this move ends the game
            char res = checkWinner(b);
            if(res=='O'){
                cout<<"You win!\n"; tcpSendLine(fd, "action=game_over;result=win"); break;
            } else if(res=='D'){
                cout<<"Draw!\n"; tcpSendLine(fd, "action=game_over;result=draw"); break;
            }
            myturn=false;
        }else{
            string msg;if(!tcpRecvLine(fd,msg))break;
            auto m=parseMessage(msg);
            if(m["action"]=="move"){
                int p=stoi(m["pos"]);b[p]='X';
                // check if opponent's move ends the game
                char res = checkWinner(b);
                if(res=='X'){ show(); cout<<"You lose...\n"; break; }
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
    string lip="127.0.0.1", lport="12000"; int udp_port=0;

    std::string txt = simplecfg::readFile("config.json");
    if(!txt.empty()){
        lip = simplecfg::getString(txt, "lobby.ip", lip);
        lport = simplecfg::getString(txt, "lobby.port", lport);
    }
    
    if(!lobbyLogin(lip,lport))return 1;

    while(true){

        // select UDP port to bind
        while(true){
            string cmd;
            cout<<"Enter UDP port to bind (18000 ~ 18030) or logout to exit: ";
            cin >> cmd;
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
            else{
                try
                {
                    udp_port = stoi(cmd);
                    if(udp_port < 18000 || udp_port > 18030){
                        cout<<"Port out of range. Please enter a value between 18000 and 18030.\n";
                        continue;
                    }
                }
                catch(const std::exception& e)
                {
                    cout<<"Invalid input. Please enter a numeric port.\n";
                    cin.clear();
                    string junk; getline(cin,junk);
                    continue; 
                }
                
            }
            if(udp_port < 18000 || udp_port > 18030){
                cout<<"Port out of range. Please enter a value between 18000 and 18030.\n";
                continue;
            }
            break;
        }

        int sock=socket(AF_INET,SOCK_DGRAM,0);
        if(sock<0){ perror("socket"); return 1; }
        sockaddr_in addr{}; addr.sin_family=AF_INET; addr.sin_port=htons(udp_port); addr.sin_addr.s_addr=INADDR_ANY;
        if(::bind(sock,(sockaddr*)&addr,sizeof(addr))!=0){ perror("bind"); close(sock); udp_port = 0; continue; }
        if(udp_port==0){ sockaddr_in a2; socklen_t l2=sizeof(a2); getsockname(sock,(sockaddr*)&a2,&l2); udp_port = ntohs(a2.sin_port); }
        cout<< username << " listening on UDP port: "<<udp_port<<"\n";

        bool restart_select_port = false;

        while(true){
            char buf[512]; sockaddr_in sender; socklen_t slen=sizeof(sender);
            int n = recvfrom(sock,buf,sizeof(buf)-1,0,(sockaddr*)&sender,&slen);
            if(n<=0) continue;
            buf[n]=0;
            auto m = parseMessage(buf);
            string act = m["action"];
            if(act=="scan"){
                string msg="action=available;username="+username;
                sendto(sock,msg.c_str(),msg.size(),0,(sockaddr*)&sender,slen);
            } else if(act=="invite"){
                cout<<"Invite from "<<m["from"]<<" accept?(y/n): "; string ans; cin>>ans;
                if(ans=="y"){
                    string ok="action=accept"; sendto(sock,ok.c_str(),ok.size(),0,(sockaddr*)&sender,slen);

                    // 等待對方回傳 tcp_info，設定 10 秒 timeout，避免永久阻塞
                    timeval tv_inv{10,0}; setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,&tv_inv,sizeof(tv_inv));
                    char buf2[256]; sockaddr_in s2; socklen_t l2=sizeof(s2);
                    int n2=recvfrom(sock,buf2,sizeof(buf2)-1,0,(sockaddr*)&s2,&l2);
                    // 恢復 blocking（或零 timeout）
                    timeval tv_zero{0,0}; setsockopt(sock,SOL_SOCKET,SO_RCVTIMEO,&tv_zero,sizeof(tv_zero));

                    if(n2<=0){
                        cout<<"No tcp_info received (timeout or error). Return to lobby.\n";
                        // 繼續等待新的 UDP 訊息
                    } else {
                        buf2[n2]=0;
                        auto m2=parseMessage(buf2);
                        if(m2["action"]=="tcp_info"){
                            string ip = inet_ntoa(s2.sin_addr);
                            int port = stoi(m2["port"]);
                            addrinfo hints{},*res; hints.ai_family=AF_UNSPEC; hints.ai_socktype=SOCK_STREAM;
                            if(getaddrinfo(ip.c_str(), to_string(port).c_str(), &hints, &res)!=0){
                                perror("getaddrinfo"); cout<<"Cannot resolve TCP target. Return to lobby.\n";
                            } else {
                                int fd=socket(res->ai_family,res->ai_socktype,res->ai_protocol);
                                if(fd<0){ perror("socket"); freeaddrinfo(res); continue; }
                                if(connect(fd,res->ai_addr,res->ai_addrlen)!=0){
                                    perror("connect"); freeaddrinfo(res); close(fd);
                                    cout<<"TCP connect failed. Return to lobby.\n";
                                } else {
                                    freeaddrinfo(res);
                                    cout<<"Connected TCP "<<ip<<":"<<port<<"\n";
                                    game(fd); close(fd);
                                    cout<<"Game finished. Returning to UDP port selection.\n";
                                    // 要回到選擇 UDP port 的步驟
                                    restart_select_port = true;
                                    break; // 跳出內層接收迴圈
                                }
                            }
                        } else {
                            cout<<"Unexpected response: "<<buf2<<"\n";
                        }
                    }
                } else {
                    string rej="action=reject"; sendto(sock,rej.c_str(),rej.size(),0,(sockaddr*)&sender,slen);
                    cout << "You have declined the invitation from " << m["from"] << ". Waiting for new invitations...\n";
                }
            }
        } // end inner recv loop

        close(sock);
        if(restart_select_port){
            udp_port = 0;
            continue;
        }
    }
}
