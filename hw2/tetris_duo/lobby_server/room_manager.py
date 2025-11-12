import threading, time

class RoomManager:
    def __init__(self):
        self.rooms = {}
        self.lock = threading.Lock()

    def create(self, host_user, name=None, visibility='public'):
        with self.lock:
            rid = len(self.rooms) + 1
            room = {
                'id': rid,
                'name': name or f'Room{rid}',
                'hostUserId': host_user,
                'visibility': visibility,
                'inviteList': [],
                'players': [host_user],
                'status': 'idle',
                'createdAt': int(time.time()*1000)
            }
            self.rooms[rid] = room
            return room

    def list_public(self):
        with self.lock:
            return [r for r in self.rooms.values() if r['visibility'] == 'public']

    def join(self, rid, user):
        with self.lock:
            room = self.rooms.get(rid)
            if not room:
                return None
            if len(room['players']) >= 2:
                return False
            room['players'].append(user)
            return room

    def leave(self, rid, user):
        with self.lock:
            room = self.rooms.get(rid)
            if not room:
                return None
            if user in room['players']:
                room['players'].remove(user)
            return room
