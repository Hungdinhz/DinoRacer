"""
Game Manager - Quản lý vòng lặp game, tính điểm, va chạm
"""
import pygame
import random
import math
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound, load_image

SKY_TOP     = (100, 180, 230)
SKY_BOT     = (255, 210, 120)
GROUND_COL  = (160, 120, 60)
GROUND_LINE = (120, 85, 35)
CLOUD_COL   = (255, 255, 255)
TEXT_LIGHT  = (255, 255, 255)
GO_BORDER   = (255, 200, 50)
GO_RED      = (220, 50,  30)
GO_GREEN    = (80,  200, 80)


class Particle:
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1, 4)
        self.life = random.randint(20, 45)
        self.max_life = self.life
        self.size = random.randint(4, 10)
        self.color = random.choice([
            (255, 80, 30), (255, 180, 0), (255, 230, 80), (200, 50, 20)
        ])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.life -= 1

    def draw(self, screen):
        alpha = int(255 * self.life / self.max_life)
        r, g, b = self.color
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (self.size, self.size), self.size)
        screen.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


class Cloud:
    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 400)
        self.y = y if y is not None else random.randint(20, 150)
        self.speed = random.uniform(0.4, 1.2)
        self.w = random.randint(90, 160)
        self.h = random.randint(28, 50)

    def update(self):
        self.x -= self.speed
        if self.x < -(self.w + 20):
            self.x = SCREEN_WIDTH + random.randint(50, 300)
            self.y = random.randint(20, 150)
            self.w = random.randint(90, 160)
            self.h = random.randint(28, 50)

    def draw(self, screen):
        pygame.draw.ellipse(screen, CLOUD_COL, (self.x, self.y, self.w, self.h))
        pygame.draw.ellipse(screen, CLOUD_COL,
                            (self.x + self.w // 5, self.y - self.h // 2,
                             self.w * 3 // 5, self.h))
        pygame.draw.ellipse(screen, CLOUD_COL,
                            (self.x + self.w // 2, self.y - self.h // 3,
                             self.w // 2, self.h * 4 // 5))


_bg_cache = {}
_tile_cache = {}


def _get_bg(bg_index):
    if bg_index not in _bg_cache:
        img = load_image(f"background/bg{bg_index}.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        if img is None:
            surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            for y in range(SCREEN_HEIGHT):
                t = y / SCREEN_HEIGHT
                r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
                g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
                b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
                pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_WIDTH, y))
            img = surf
        _bg_cache[bg_index] = img
    return _bg_cache[bg_index]


def _get_tile(name, size):
    key = (name, size)
    if key not in _tile_cache:
        _tile_cache[key] = load_image(f"tiles/{name}", size)
    return _tile_cache[key]


class GameManager:
    def __init__(self, screen, is_ai_mode=False):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.is_ai_mode = is_ai_mode
        self.highscore_human, self.highscore_ai = load_highscore()

        avail = pygame.font.get_fonts()
        title_font = 'impact' if 'impact' in avail else 'arial'
        self.font_hud   = pygame.font.SysFont('Arial', 24, bold=True)
        self.font_large = pygame.font.SysFont(title_font, 68, bold=True)
        self.font_med   = pygame.font.SysFont('Arial', 30, bold=True)
        self.font_small = pygame.font.SysFont('Arial', 20)
        self.font_speed = pygame.font.SysFont('Arial', 18)

        self.pause_btn = pygame.Rect(SCREEN_WIDTH - 70, 10, 50, 50)
        self.clouds = [
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(20, 150))
            for _ in range(7)
        ]
        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []
        self.go_flash_timer = 0
        self.bg_index = 1
        self.reset()

    def reset(self):
        self.dino = Dino()
        self.obstacles = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        self.game_over = False
        self.paused = False
        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []
        self.go_flash_timer = 0
        self.bg_index = 1

    def toggle_pause(self):
        self.paused = not self.paused

    def spawn_obstacle(self):
        if self.last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(SCREEN_WIDTH + 50, speed)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x

    def check_collision(self):
        dino_rect = self.dino.get_rect()
        margin = 8
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)
        for obs in self.obstacles:
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                return True
        return False

    def update(self, action=None):
        if self.paused:
            return
        if self.game_over:
            self.particles = [p for p in self.particles if p.life > 0]
            for p in self.particles:
                p.update()
            self.go_flash_timer += 1
            return

        if action is not None:
            jump, duck, _ = action
            if jump > 0.5:
                self.dino.jump()
            self.dino.duck(duck > 0.5)

        self.dino.update()
        self.spawn_obstacle()

        self.ground_offset = (self.ground_offset + self.game_speed) % 64
        self.bg_offset = (self.bg_offset + self.game_speed * 0.15) % SCREEN_WIDTH

        prev_score = self.score
        for obs in self.obstacles:
            obs.update()
            if obs.x < self.dino.x and not obs.passed:
                obs.passed = True
                self.score += 1
        if self.score // 100 > prev_score // 100 and self.score > 0:
            play_sound("score")

        self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
        if self.obstacles:
            self.last_obstacle_x = max(o.x for o in self.obstacles)

        self.game_speed = OBSTACLE_SPEED_MIN + (self.score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
        self.game_speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
        self.bg_index = min(1 + self.score // 50, 5)

        for c in self.clouds:
            c.update()

        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
            rect = self.dino.get_rect()
            for _ in range(40):
                self.particles.append(Particle(rect.centerx, rect.centery))
            h_cur = self.highscore_ai if self.is_ai_mode else self.highscore_human
            if self.score > h_cur:
                if self.is_ai_mode:
                    self.highscore_ai = self.score
                    save_highscore(ai=self.score)
                else:
                    self.highscore_human = self.score
                    save_highscore(human=self.score)

    def get_state(self):
        nearest = None
        min_dist = float('inf')
        for obs in self.obstacles:
            if obs.x > self.dino.x:
                dist = obs.x - self.dino.x
                if dist < min_dist:
                    min_dist = dist
                    nearest = obs
        if nearest is None:
            return [1.0, 0.5, 0.0, 0.0, 0.0]
        from src.obstacle import Cactus
        return [
            min(min_dist / 500, 1.0),
            0.0 if isinstance(nearest, Cactus) else 1.0,
            (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN),
            min((GROUND_Y - self.dino.y) / 100, 1.0),
            1.0 if self.dino.is_jumping else 0.0,
        ]

    # ── Draw ──────────────────────────────────────────────────

    def _draw_background(self):
        bg = _get_bg(self.bg_index)
        ox = int(self.bg_offset) % SCREEN_WIDTH
        self.screen.blit(bg, (-ox, 0))
        if ox > 0:
            self.screen.blit(bg, (SCREEN_WIDTH - ox, 0))

    def _draw_ground(self):
        tile_h = SCREEN_HEIGHT - GROUND_Y
        tile_w = 64
        tile = _get_tile("Tile_01.png", (tile_w, tile_h))
        if tile:
            offset = int(self.ground_offset) % tile_w
            for x in range(-tile_w, SCREEN_WIDTH + tile_w, tile_w):
                self.screen.blit(tile, (x - offset, GROUND_Y))
        else:
            pygame.draw.rect(self.screen, GROUND_COL,
                             (0, GROUND_Y, SCREEN_WIDTH, tile_h))
            pygame.draw.line(self.screen, GROUND_LINE,
                             (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
            for i in range(-1, SCREEN_WIDTH // 40 + 2):
                x = i * 40 - int(self.ground_offset) % 40
                pygame.draw.line(self.screen, GROUND_LINE,
                                 (x, GROUND_Y + 10), (x + 22, GROUND_Y + 10), 1)

    def _draw_hud(self):
        h = max(self.highscore_ai if self.is_ai_mode else self.highscore_human, self.score)

        hud = pygame.Surface((260, 70), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 110))
        pygame.draw.rect(hud, (255, 200, 50, 160), (0, 0, 260, 70), 2, border_radius=8)
        self.screen.blit(hud, (SCREEN_WIDTH // 2 - 130, 5))

        score_txt = self.font_hud.render(f"SCORE  {self.score:05d}", True, (255, 230, 80))
        hi_txt    = self.font_hud.render(f"HI  {h:05d}", True, (200, 200, 200))
        spd_txt   = self.font_speed.render(f"SPD  {self.game_speed:.1f}", True, (150, 230, 150))
        self.screen.blit(score_txt, (SCREEN_WIDTH // 2 - 118, 12))
        self.screen.blit(hi_txt,    (SCREEN_WIDTH // 2 - 118, 38))
        self.screen.blit(spd_txt,   (SCREEN_WIDTH // 2 + 30,  38))

        # Speed bar
        bar_x, bar_y, bar_w, bar_h = SCREEN_WIDTH // 2 + 30, 14, 90, 10
        ratio = (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
        pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = max(1, int(bar_w * ratio))
        bar_color = (int(80 + 175 * ratio), int(200 - 150 * ratio), 50)
        pygame.draw.rect(self.screen, bar_color,
                         (bar_x, bar_y, fill_w, bar_h), border_radius=4)

    def _draw_pause_btn(self):
        mouse_pos = pygame.mouse.get_pos()
        hover = self.pause_btn.collidepoint(mouse_pos)
        color = (180, 180, 180) if hover else (80, 80, 80)
        pygame.draw.rect(self.screen, color, self.pause_btn, border_radius=8)
        pygame.draw.rect(self.screen, (220, 220, 220), self.pause_btn, 2, border_radius=8)
        if self.paused:
            pygame.draw.polygon(self.screen, TEXT_LIGHT, [
                (self.pause_btn.left + 14, self.pause_btn.top + 11),
                (self.pause_btn.left + 14, self.pause_btn.bottom - 11),
                (self.pause_btn.right - 10, self.pause_btn.centery),
            ])
        else:
            pygame.draw.rect(self.screen, TEXT_LIGHT,
                             (self.pause_btn.left + 11, self.pause_btn.top + 11, 9, 28))
            pygame.draw.rect(self.screen, TEXT_LIGHT,
                             (self.pause_btn.left + 30, self.pause_btn.top + 11, 9, 28))

    def _draw_paused_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))
        txt = self.font_large.render("PAUSED", True, (255, 230, 100))
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        hint = self.font_small.render("Press  P  to continue", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))

    def _draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        for p in self.particles:
            p.draw(self.screen)

        pw, ph = 460, 220
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((15, 10, 5, 235))
        self.screen.blit(panel, (px, py))

        flash = abs(math.sin(self.go_flash_timer * 0.08))
        border_col = (
            int(GO_BORDER[0] * flash + 100 * (1 - flash)),
            int(GO_BORDER[1] * flash + 50  * (1 - flash)),
            int(GO_BORDER[2] * flash),
        )
        pygame.draw.rect(self.screen, border_col, (px, py, pw, ph), 3, border_radius=14)

        go_txt = self.font_large.render("GAME OVER", True, GO_RED)
        self.screen.blit(go_txt, go_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 68)))

        h = max(self.highscore_ai if self.is_ai_mode else self.highscore_human, self.score)
        score_txt = self.font_med.render(f"Score: {self.score}", True, (255, 230, 80))
        hi_txt    = self.font_med.render(f"HI: {h}", True, (200, 200, 200))
        self.screen.blit(score_txt, score_txt.get_rect(center=(SCREEN_WIDTH // 2 - 70, py + 130)))
        self.screen.blit(hi_txt,    hi_txt.get_rect(center=(SCREEN_WIDTH // 2 + 80, py + 130)))

        r_txt = self.font_small.render("R  -  Choi lai", True, GO_GREEN)
        m_txt = self.font_small.render("ESC  -  Menu", True, (180, 180, 255))
        self.screen.blit(r_txt, r_txt.get_rect(center=(SCREEN_WIDTH // 2 - 80, py + 185)))
        self.screen.blit(m_txt, m_txt.get_rect(center=(SCREEN_WIDTH // 2 + 80, py + 185)))

    def draw(self):
        self._draw_background()
        for c in self.clouds:
            c.draw(self.screen)
        self._draw_ground()
        self.dino.draw(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)
        self._draw_hud()
        self._draw_pause_btn()
        if self.paused:
            self._draw_paused_overlay()
        elif self.game_over:
            self._draw_game_over()
        pygame.display.flip()

    def run_human_mode(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not self.game_over and not self.paused:
                            self.dino.jump()
                    if event.key == pygame.K_DOWN:
                        if not self.game_over and not self.paused:
                            self.dino.duck(True)
                    if event.key == pygame.K_p:
                        if not self.game_over:
                            self.toggle_pause()
                    if event.key == pygame.K_r and self.game_over:
                        self.reset()
                    if event.key == pygame.K_ESCAPE and self.game_over:
                        running = False
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN:
                        self.dino.duck(False)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.pause_btn.collidepoint(event.pos) and not self.game_over:
                        self.toggle_pause()
            self.update()
            self.draw()
            self.clock.tick(FPS)
