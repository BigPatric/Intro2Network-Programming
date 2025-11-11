CXX=g++
CXXFLAGS=-std=c++17 -pthread -O2

all: lobby_server db_server client

lobby_server: lobby_server.cpp NetworkUtils.hpp
	$(CXX) $(CXXFLAGS) lobby_server.cpp -o lobby_server

db_server: db_server.cpp NetworkUtils.hpp
	$(CXX) $(CXXFLAGS) db_server.cpp -o db_server

client: client.cpp NetworkUtils.hpp
	$(CXX) $(CXXFLAGS) client.cpp -o client

clean:
	rm -f lobby_server db_server client
