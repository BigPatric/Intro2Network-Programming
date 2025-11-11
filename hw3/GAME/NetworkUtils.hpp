#pragma once
#include <string>
#include <sstream>
#include <map>
#include <unistd.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <iostream>

// --- helper: parse key=value;key=value into map ---
inline std::map<std::string,std::string> parseMessage(const std::string &msg) {
    std::map<std::string,std::string> result;
    std::stringstream ss(msg);
    std::string kv;
    while(std::getline(ss, kv, ';')) {
        auto pos = kv.find('=');
        if(pos != std::string::npos) {
            std::string key = kv.substr(0,pos);
            std::string val = kv.substr(pos+1);
            result[key] = val;
        }
    }
    return result;
}

// --- build message string from map ---
inline std::string buildMessage(const std::map<std::string,std::string> &m) {
    std::string s;
    for(auto &kv : m) {
        if(!s.empty()) s += ";";
        s += kv.first + "=" + kv.second;
    }
    return s;
}

// --- TCP send line ---
// --- TCP send line (deprecated, use tcpSendMsg) ---
inline bool tcpSendLine(int fd, const std::string &line) {
    std::string s = line + "\n";
    ssize_t n = send(fd, s.c_str(), s.size(), 0);
    return n == (ssize_t)s.size();
}

// --- TCP send length-prefixed message ---
inline bool tcpSendMsg(int fd, const std::string &msg) {
    uint32_t len = htonl(msg.size());
    if (send(fd, &len, sizeof(len), 0) != sizeof(len)) return false;
    size_t sent = 0;
    while (sent < msg.size()) {
        ssize_t n = send(fd, msg.data() + sent, msg.size() - sent, 0);
        if (n <= 0) return false;
        sent += n;
    }
    return true;
}

// --- TCP recv one line ---
// --- TCP recv one line (deprecated, use tcpRecvMsg) ---
inline bool tcpRecvLine(int fd, std::string &out) {
    out.clear();
    char c;
    while(true){
        ssize_t n = recv(fd, &c, 1, 0);
        if(n <= 0) return false;
        if(c == '\n') break;
        out.push_back(c);
    }
    return true;
}

// --- TCP recv length-prefixed message ---
inline bool tcpRecvMsg(int fd, std::string &msg) {
    uint32_t len_net;
    ssize_t n = recv(fd, &len_net, sizeof(len_net), MSG_WAITALL);
    if (n != sizeof(len_net)) return false;
    uint32_t len = ntohl(len_net);
    msg.resize(len);
    size_t recvd = 0;
    while (recvd < len) {
        ssize_t m = recv(fd, &msg[recvd], len - recvd, 0);
        if (m <= 0) return false;
        recvd += m;
    }
    return true;
}
