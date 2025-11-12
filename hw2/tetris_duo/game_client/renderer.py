import pygame, sys, time

CELL = 20
MARGIN = 10

COLORS = {
    0: (20,20,20),
    1: (200,50,50),
    2: (80,180,255),  # active piece color
}

# Shapes for rendering active piece
SHAPES = {
    'I': [[1,1,1,1]],
    'O': [[1,1],[1,1]],
    'T': [[0,1,0],[1,1,1]],
    'S': [[0,1,1],[1,1,0]],
    'Z': [[1,1,0],[0,1,1]],
    'J': [[1,0,0],[1,1,1]],
    'L': [[0,0,1],[1,1,1]],
}

class Renderer:
    def __init__(self, width=800, height=600, buffer_ms=150):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Tetris Duo - Client')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Consolas', 16)
        self.my_state = None
        self.opp_state = None
        self.my_queue = []
        self.opp_queue = []
        self.buffer_ms = buffer_ms

    def update_state(self, my_state, opp_state):
        now = int(time.time()*1000)
        if my_state:
            self.my_queue.append(my_state)
        if opp_state:
            self.opp_queue.append(opp_state)
        # 保持佇列長度適中
        if len(self.my_queue) > 120:
            self.my_queue = self.my_queue[-120:]
        if len(self.opp_queue) > 120:
            self.opp_queue = self.opp_queue[-120:]

    def _pick_buffered(self, queue):
        if not queue:
            return None
        target = int(time.time()*1000) - self.buffer_ms
        # 找到最後一個 at <= target 的快照
        chosen = None
        keep_from = 0
        for i, st in enumerate(queue):
            at = st.get('at', 0)
            if at <= target:
                chosen = st
                keep_from = i
            else:
                break
        if chosen is None:
            # 還沒有足夠延遲，就用最舊的
            chosen = queue[0]
            keep_from = 0
        # 丟掉過舊的
        if keep_from > 0:
            del queue[:keep_from]
        return chosen

    def _decode_board_rle(self, rle):
        # 返回 20x10 的 0/1 grid
        grid = [[0]*10 for _ in range(20)]
        if not rle:
            return grid
        rows = rle.split('|')
        for y, row in enumerate(rows[:20]):
            x = 0
            for seg in row.split(','):
                try:
                    v_s, c_s = seg.split(':')
                    v = int(v_s)
                    c = int(c_s)
                except ValueError:
                    continue
                for _ in range(min(c, 10 - x)):
                    if 0 <= x < 10:
                        grid[y][x] = 1 if v else 0
                    x += 1
                if x >= 10:
                    break
        return grid

    def draw_compact_board(self, x, y, state):
        if state is None:
            txt = self.font.render('No data', True, (255,255,255))
            self.screen.blit(txt, (x, y))
            return
        score = state.get('score', 0)
        lines = state.get('lines', 0)
        self.screen.blit(self.font.render(f'Score: {score}', True, (255,255,255)), (x, y))
        self.screen.blit(self.font.render(f'Lines: {lines}', True, (255,255,255)), (x, y+20))
        rle = state.get('boardRLE', '')
        grid = self._decode_board_rle(rle)
        # draw locked tiles
        for row in range(20):
            for col in range(10):
                rect = pygame.Rect(x + col*CELL, y + 60 + row*CELL, CELL-1, CELL-1)
                color = COLORS[1] if grid[row][col] else COLORS[0]
                pygame.draw.rect(self.screen, color, rect)
        # draw active piece overlay (approx)
        act = state.get('active') or {}
        shape = act.get('shape')
        ax = act.get('x')
        ay = act.get('y')
        mat = SHAPES.get(shape)
        if mat is not None and ax is not None and ay is not None:
            for ry, r in enumerate(mat):
                for rx, v in enumerate(r):
                    if v:
                        cx = ax + rx
                        cy = ay + ry
                        if 0 <= cx < 10 and 0 <= cy < 20:
                            rect = pygame.Rect(x + cx*CELL, y + 60 + cy*CELL, CELL-1, CELL-1)
                            pygame.draw.rect(self.screen, COLORS[2], rect)

    def render_frame(self):
        # 以緩衝佇列挑選要顯示的狀態
        self.my_state = self._pick_buffered(self.my_queue) or self.my_state
        self.opp_state = self._pick_buffered(self.opp_queue) or self.opp_state
        self.screen.fill((30,30,30))
        self.draw_compact_board(MARGIN, MARGIN, self.my_state)
        self.draw_compact_board(400, MARGIN, self.opp_state)
        pygame.display.flip()
        self.clock.tick(60)
