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
    def __init__(self, width=1400, height=1000, buffer_ms=150):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Tetris Duo - Client')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Consolas', 24)
        self.small_font = pygame.font.SysFont('Consolas', 16)
        self.my_state = None
        self.opp_state = None
        self.my_queue = []
        self.opp_queue = []
        self.buffer_ms = buffer_ms
        self.room_id = None
        self.role = None
        self.start_time = None
        # 與伺服器 game_server.game_server 的 duration_sec (60s) 對齊
        self.duration_sec = 60
        self.user_name = None
    def set_room_info(self, room_id, role, start_time=None, user_name=None):
        self.room_id = room_id
        self.role = role
        self.start_time = start_time or int(time.time()*1000)
        if user_name:
            self.user_name = user_name

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

    def draw_compact_board(self, x, y, state, scale=1):
        if state is None:
            txt = self.small_font.render('No data', True, (255,255,255))
            self.screen.blit(txt, (x, y))
            return
        score = state.get('score', 0)
        lines = state.get('lines', 0)
        self.screen.blit(self.small_font.render(f'Score: {score}', True, (255,255,255)), (x, y))
        self.screen.blit(self.small_font.render(f'Lines: {lines}', True, (255,255,255)), (x, y+20))
        rle = state.get('boardRLE', '')
        grid = self._decode_board_rle(rle)
        cell_size = CELL * scale
        for row in range(20):
            for col in range(10):
                rect = pygame.Rect(x + col*cell_size, y + 60 + row*cell_size, cell_size-1, cell_size-1)
                color = COLORS[1] if grid[row][col] else COLORS[0]
                pygame.draw.rect(self.screen, color, rect)
        act = state.get('active') or {}
        shape = act.get('shape')
        ax = act.get('x')
        ay = act.get('y')
        # 伺服器若提供當前旋轉矩陣，優先使用；否則退回到預設形狀
        mat = act.get('mat') or SHAPES.get(shape)
        if mat is not None and ax is not None and ay is not None:
            for ry, r in enumerate(mat):
                for rx, v in enumerate(r):
                    if v:
                        cx = ax + rx
                        cy = ay + ry
                        if 0 <= cx < 10 and 0 <= cy < 20:
                            rect = pygame.Rect(x + cx*cell_size, y + 60 + cy*cell_size, cell_size-1, cell_size-1)
                            pygame.draw.rect(self.screen, COLORS[2], rect)

    def render_frame(self):
        self.my_state = self._pick_buffered(self.my_queue) or self.my_state
        self.opp_state = self._pick_buffered(self.opp_queue) or self.opp_state
        self.screen.fill((30,30,30))

        # Show room, role, user name
        info_text = f'Room: {self.room_id if self.room_id else "-"} Role: {self.role if self.role else "-"}'
        if self.user_name:
            info_text += f'  Player: {self.user_name}'
        txt = self.font.render(info_text, True, (255,255,0))
        self.screen.blit(txt, (MARGIN, MARGIN))

        # Show timer (mm:ss)
        if self.start_time:
            now = int(time.time()*1000)
            remain = max(0, self.duration_sec - (now - self.start_time)//1000)
            mm = remain // 60
            ss = remain % 60
            timer_txt = self.font.render(f'Time left: {mm:01d}:{ss:02d}', True, (255,100,100))
            self.screen.blit(timer_txt, (MARGIN, MARGIN+40))

        # Enlarge own board
        self.draw_compact_board(MARGIN, MARGIN+80, self.my_state, scale=2)
        # Opponent board normal size
        self.draw_compact_board(600, MARGIN+80, self.opp_state, scale=1)

        # Controls hint (bottom right)
        tips = [
            "Controls:",
            "← →: Move left/right",
            "Z: Rotate piece ",
            "↓: Soft drop",
            "Space: Hard drop",
            "C: Hold piece",
            "Q: Quit game"
        ]
        # 計算右下角起始座標
        tip_x = self.screen.get_width() - 320
        tip_y = self.screen.get_height() - (len(tips)*22) - 30
        for i, tip in enumerate(tips):
            tip_txt = self.small_font.render(tip, True, (180,220,255))
            self.screen.blit(tip_txt, (tip_x, tip_y + i*22))

        pygame.display.flip()
        self.clock.tick(60)
