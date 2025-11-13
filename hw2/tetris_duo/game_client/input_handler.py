import pygame

KEY_MAP = {
    pygame.K_LEFT: 'LEFT',
    pygame.K_RIGHT: 'RIGHT',
    pygame.K_DOWN: 'SOFT',
    pygame.K_SPACE: 'HARD',
    pygame.K_z: 'ROT',
    pygame.K_c: 'HOLD',
}

class InputHandler:
    def __init__(self, network):
        self.network = network
        self.quit_requested = False
        self.last_rot_time = 0  # 防抖用

    def pump(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                # 不在此直接結束程式，交由上層回到 Lobby
                self.quit_requested = True
            if e.type == pygame.KEYDOWN:
                action = KEY_MAP.get(e.key)
                if action == 'ROT':
                    now = pygame.time.get_ticks()
                    if now - self.last_rot_time < 80:
                        continue  # 80ms 內不重複送旋轉
                    self.last_rot_time = now
                if action:
                    self.network.send_input(action)
            # allow other events be handled by renderer
