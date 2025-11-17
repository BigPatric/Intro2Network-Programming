# Global configuration for server/client hosts and ports
# Modify these values to relocate services without touching source code.

LOBBY_HOST = '140.113.17.12'
LOBBY_PORT = 10000

DB_HOST = '140.113.17.12'
DB_PORT = 10001

# Game server dynamic port range
GAME_PORT_MIN = 10002
GAME_PORT_MAX = 20000
GAME_BIND_HOST = '140.113.17.12'  # host used by game server to bind
GAME_CONNECT_HOST = '140.113.17.12'  # host used by client to connect

# Future expansion placeholders
# TLS_ENABLED = False
# LOG_LEVEL = 'INFO'
