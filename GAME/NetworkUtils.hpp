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
inline bool tcpSendLine(int fd, const std::string &line) {
    std::string s = line + "\n";
    ssize_t n = send(fd, s.c_str(), s.size(), 0);
    return n == (ssize_t)s.size();
}

// --- TCP recv one line ---
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
