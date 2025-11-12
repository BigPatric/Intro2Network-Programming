import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import socket
from common.protocol import send_msg, recv_msg

class DBClient:
    def __init__(self, host='127.0.0.1', port=10001):
        self.host = host
        self.port = port

    def _request(self, req):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))
        send_msg(s, req)
        res = recv_msg(s)
        s.close()
        return res

    def create(self, collection, data):
        return self._request({'collection': collection, 'action': 'create', 'data': data})

    def read(self, collection, key=None, value=None):
        return self._request({'collection': collection, 'action': 'read', 'data': {'key': key, 'value': value}})

    def update(self, collection, key, value, new_data):
        return self._request({'collection': collection, 'action': 'update', 'data': {'key': key, 'value': value, 'new_data': new_data}})

    def delete(self, collection, key, value):
        return self._request({'collection': collection, 'action': 'delete', 'data': {'key': key, 'value': value}})

    def query(self, collection, q):
        return self._request({'collection': collection, 'action': 'query', 'data': {'q': q}})
