CXX=g++
CXXFLAGS=-std=c++17 -pthread -O2

all: lobby_server playerA playerB

lobby_server: lobby_server.cpp NetworkUtils.hpp
	$(CXX) $(CXXFLAGS) lobby_server.cpp -o lobby_server

playerA: playerA.cpp NetworkUtils.hpp
	$(CXX) $(CXXFLAGS) playerA.cpp -o playerA

playerB: playerB.cpp NetworkUtils.hpp
	$(CXX) $(CXXFLAGS) playerB.cpp -o playerB

clean:
	rm -f lobby_server playerA playerB
