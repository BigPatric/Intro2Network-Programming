// Very small helper for reading simple JSON-like config values without external deps.
#pragma once
#include <string>
#include <fstream>
#include <sstream>
#include <cctype>

namespace simplecfg {
    inline std::string readFile(const std::string &path){
        std::ifstream ifs(path);
        if(!ifs) return std::string();
        std::ostringstream ss; ss << ifs.rdbuf();
        return ss.str();
    }

    // Trim helpers
    inline std::string trim(const std::string &s){
        size_t a=0,b=s.size();
        while(a<b && std::isspace((unsigned char)s[a])) ++a;
        while(b>a && std::isspace((unsigned char)s[b-1])) --b;
        return s.substr(a,b-a);
    }

    // Find last occurrence of a key name (without quotes) and return raw value text after ':'
    inline bool findRawValue(const std::string &txt, const std::string &key, std::string &out){
        std::string q = '"' + key + '"';
        size_t pos = txt.rfind(q);
        if(pos==std::string::npos) return false;
        size_t colon = txt.find(':', pos + q.size());
        if(colon==std::string::npos) return false;
        size_t i = colon+1;
        // skip spaces
        while(i<txt.size() && std::isspace((unsigned char)txt[i])) ++i;
        // read until comma or brace
        size_t j=i;
        if(i<txt.size() && txt[i]=='\"'){
            ++i; j = i;
            while(j<txt.size() && txt[j]!='\"') ++j;
            out = txt.substr(i, j-i);
            return true;
        } else {
            while(j<txt.size() && txt[j]!=',' && txt[j] != '}' && txt[j] != '\n') ++j;
            out = trim(txt.substr(i, j-i));
            return true;
        }
    }

    inline std::string getString(const std::string &txt, const std::string &path, const std::string &def=""){
        // path like "lobby.ip" -> we take last segment as key
        auto pos = path.rfind('.');
        std::string key = (pos==std::string::npos)? path : path.substr(pos+1);
        std::string val;
        if(findRawValue(txt, key, val)) return val;
        return def;
    }

    inline int getInt(const std::string &txt, const std::string &path, int def=0){
        auto pos = path.rfind('.');
        std::string key = (pos==std::string::npos)? path : path.substr(pos+1);
        std::string val;
        if(findRawValue(txt, key, val)){
            try{ return std::stoi(val); }catch(...){ return def; }
        }
        return def;
    }
}
