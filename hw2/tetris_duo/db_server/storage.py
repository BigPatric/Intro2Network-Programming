import json, threading, os, time

class Database:
    def __init__(self, path='data.json'):
        self.path = path
        self.lock = threading.Lock()
        if not os.path.exists(path):
            with open(path, 'w') as f:
                json.dump({"User": [], "Room": [], "GameLog": []}, f)

    def load(self):
        with self.lock:
            with open(self.path, 'r') as f:
                return json.load(f)

    def save(self, data):
        with self.lock:
            with open(self.path, 'w') as f:
                json.dump(data, f, indent=2)

    def _next_id(self, items):
        if not items:
            return 1
        return max(x.get('id', 0) for x in items) + 1

    def handle_request(self, req):
        data = self.load()
        collection = req.get('collection')
        action = req.get('action')
        payload = req.get('data', {})

        if collection not in data:
            return {"error": "Unknown collection"}

        if action == 'create':
            item = payload.copy()
            item['id'] = self._next_id(data[collection])
            item['createdAt'] = int(time.time()*1000)
            data[collection].append(item)
            self.save(data)
            return {"status": "ok", "id": item['id']}

        elif action == 'read':
            key, value = payload.get('key'), payload.get('value')
            if key is None:
                return {"result": data[collection]}
            result = [x for x in data[collection] if x.get(key) == value]
            return {"result": result}

        elif action == 'update':
            key, value = payload.get('key'), payload.get('value')
            new_data = payload.get('new_data', {})
            updated = 0
            for item in data[collection]:
                if item.get(key) == value:
                    item.update(new_data)
                    updated += 1
            self.save(data)
            return {"status": "ok", "updated": updated}

        elif action == 'delete':
            key, value = payload.get('key'), payload.get('value')
            before = len(data[collection])
            data[collection] = [x for x in data[collection] if x.get(key) != value]
            self.save(data)
            return {"status": "ok", "deleted": before - len(data[collection])}

        elif action == 'query':
            q = payload.get('q', {})
            res = []
            for item in data[collection]:
                ok = True
                for k, v in q.items():
                    if item.get(k) != v:
                        ok = False
                        break
                if ok:
                    res.append(item)
            return {"result": res}

        else:
            return {"error": "Unknown action"}