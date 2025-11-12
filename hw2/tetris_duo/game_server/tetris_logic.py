# 完整核心遊戲邏輯：碰撞檢查、旋轉 (簡化)、行清除、分數、7-bag
import random, time, copy

# Use compact shape definitions with rotation via matrix transforms
SHAPES = {
    'I': [[1,1,1,1]],
    'O': [[1,1],[1,1]],
    'T': [[0,1,0],[1,1,1]],
    'S': [[0,1,1],[1,1,0]],
    'Z': [[1,1,0],[0,1,1]],
    'J': [[1,0,0],[1,1,1]],
    'L': [[0,0,1],[1,1,1]],
}

def rotate_matrix(mat):
    return [list(row) for row in zip(*mat[::-1])]

class BagGenerator:
    def __init__(self, seed=None):
        self.seed = seed
        self.rnd = random.Random(seed)
        self.bag = []

    def next(self):
        if not self.bag:
            self.bag = list(SHAPES.keys())
            self.rnd.shuffle(self.bag)
        return self.bag.pop(0)

class Board:
    WIDTH = 10
    HEIGHT = 20

    def __init__(self, seed=None):
        self.grid = [[0]*self.WIDTH for _ in range(self.HEIGHT)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.baggen = BagGenerator(seed)
        self.next_queue = [self.baggen.next() for _ in range(5)]
        self.hold = None
        self.can_hold = True
        self.spawn()

    def spawn(self):
        shape = self.next_queue.pop(0)
        self.next_queue.append(self.baggen.next())
        mat = SHAPES[shape]
        self.active = {'shape': shape, 'mat': mat, 'x': (self.WIDTH - len(mat[0]))//2, 'y': 0}
        if self.collides(self.active['x'], self.active['y'], self.active['mat']):
            self.game_over = True
        else:
            self.game_over = False

    def collides(self, x, y, mat):
        for ry, row in enumerate(mat):
            for rx, v in enumerate(row):
                if not v:
                    continue
                gx = x + rx
                gy = y + ry
                if gx < 0 or gx >= self.WIDTH or gy < 0 or gy >= self.HEIGHT:
                    return True
                if self.grid[gy][gx]:
                    return True
        return False

    def lock_piece(self):
        mat = self.active['mat']
        x = self.active['x']
        y = self.active['y']
        for ry, row in enumerate(mat):
            for rx, v in enumerate(row):
                if v:
                    self.grid[y+ry][x+rx] = 1
        cleared = self.clear_lines()
        self.update_score(cleared)
        self.can_hold = True
        self.spawn()

    def clear_lines(self):
        new_grid = [r for r in self.grid if not all(r)]
        cleared = self.HEIGHT - len(new_grid)
        if cleared:
            for _ in range(cleared):
                new_grid.insert(0, [0]*self.WIDTH)
            self.grid = new_grid
            self.lines += cleared
        return cleared

    def update_score(self, cleared):
        # Classic scoring: 0,40,100,300,1200 scaled by level
        points = {0:0,1:40,2:100,3:300,4:1200}
        self.score += points.get(cleared, 0) * self.level

    def hard_drop(self):
        while not self.collides(self.active['x'], self.active['y']+1, self.active['mat']):
            self.active['y'] += 1
        self.lock_piece()

    def soft_drop(self):
        if not self.collides(self.active['x'], self.active['y']+1, self.active['mat']):
            self.active['y'] += 1
            self.score += 1
        else:
            self.lock_piece()

    def move(self, dx):
        nx = self.active['x'] + dx
        if not self.collides(nx, self.active['y'], self.active['mat']):
            self.active['x'] = nx

    def rotate(self):
        new_mat = rotate_matrix(self.active['mat'])
        # simple wall-kick: try original, left, right, up
        tests = [(0,0),(-1,0),(1,0),(0,-1)]
        for dx, dy in tests:
            if not self.collides(self.active['x']+dx, self.active['y']+dy, new_mat):
                self.active['mat'] = new_mat
                self.active['x'] += dx
                self.active['y'] += dy
                return

    def hold_piece(self):
        if not self.can_hold:
            return
        if self.hold is None:
            self.hold = self.active['shape']
            self.spawn()
        else:
            # swap
            cur = self.active['shape']
            self.active = {'shape': self.hold, 'mat': SHAPES[self.hold], 'x': (self.WIDTH - len(SHAPES[self.hold][0]))//2, 'y': 0}
            self.hold = cur
        self.can_hold = False

    def tick(self):
        # gravity tick
        if not self.collides(self.active['x'], self.active['y']+1, self.active['mat']):
            self.active['y'] += 1
        else:
            self.lock_piece()

    def board_rle(self):
        rows = []
        for r in self.grid:
            cnt = 0
            last = r[0]
            parts = []
            for c in r:
                if c == last:
                    cnt += 1
                else:
                    parts.append(f"{last}:{cnt}")
                    last = c
                    cnt = 1
            parts.append(f"{last}:{cnt}")
            rows.append(','.join(parts))
        return '|'.join(rows)

    def snapshot(self):
        return {
            'boardRLE': self.board_rle(),
            'active': {'shape': self.active['shape'], 'x': self.active['x'], 'y': self.active['y']},
            'hold': self.hold,
            'next': self.next_queue[:3],
            'score': self.score,
            'lines': self.lines,
            'level': self.level,
            'at': int(time.time()*1000)
        }
