"""
LaneGame - Game logic cho 1 lane (nửa màn hình).
Mỗi lane render vào một pygame.Surface riêng, không phụ thuộc nhau.
"""
import pygame
import random
import math
from config.settings import (
    SCREEN_WIDTH, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
    INITIAL_SCORE,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.assets_loader import play_sound, load_image
from src.data_collector import get_collector

# Chiều cao mỗi lane = nửa màn hình
LANE_H = 250
LANE_W = SCREEN_WIDTH
GROUND_Y_LANE = LANE_H - 55   # mặt đất trong lane

SKY_TOP    = (100, 180, 230)
SKY_BOT    = (255, 210, 120)
GROUND_COL = (160, 120, 60)
GROUND_LN  = (120, 85,  35)
CLOUD_COL  = (255, 255, 255)

_bg_cache  = {}
_tile_cache = {}


def _get_bg(idx):
    key = ("lane", idx)
    if key not in _bg_cache:
        img = load_image(f"background/bg{idx}.png", (LANE_W, LANE_H))
        if img is None:
            surf = pygame.Surface((LANE_W, LANE_H))
            for y in range(LANE_H):
                t = y / LANE_H
                r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
                g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
                b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
                pygame.draw.line(surf, (r, g, b), (0, y), (LANE_W, y))
            img = surf
        _bg_cache[key] = img
    return _bg_cache[key]


def _get_tile(size):
    if size not in _tile_cache:
        _tile_cache[size] = load_image("tiles/Tile_01.png", size)
    return _tile_cache[size]


class LaneCloud:
    def __init__(self, x=None):
        self.x = x if x is not None else random.randint(0, LANE_W)
        self.y = random.randint(10, 80)
        self.speed = random.uniform(0.3, 0.9)
        self.w = random.randint(70, 130)
        self.h = random.randint(20, 38)

    def update(self):
        self.x -= self.speed
        if self.x < -(self.w + 10):
            self.x = LANE_W + random.randint(30, 200)
            self.y = random.randint(10, 80)

    def draw(self, surf):
        pygame.draw.ellipse(surf, CLOUD_COL, (self.x, self.y, self.w, self.h))
        pygame.draw.ellipse(surf, CLOUD_COL,
                            (self.x + self.w // 5, self.y - self.h // 2,
                             self.w * 3 // 5, self.h))
        pygame.draw.ellipse(surf, CLOUD_COL,
                            (self.x + self.w // 2, self.y - self.h // 3,
                             self.w // 2, int(self.h * 0.8)))


class LaneGame:
    """
    Một lane game độc lập.
    dino_folder: "dino" (vàng - player) hoặc "ai_dino" (tím - AI)
    label      : tên hiển thị góc trên lane ("PLAYER", "AI", "P1", "P2")
    label_color: màu chữ label
    collect_data: True nếu muốn thu thập dữ liệu training
    player_type: "human" hoặc "ai" - nguồn dữ liệu
    """

    def __init__(self, dino_folder="dino", label="PLAYER",
                 label_color=(255, 230, 80), collect_data=False, player_type="human"):
        self.dino_folder = dino_folder
        self.label = label
        self.label_color = label_color
        self.collect_data = collect_data
        self.player_type = player_type

        self.surface = pygame.Surface((LANE_W, LANE_H))

        self.font_hud   = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_label = pygame.font.SysFont("Arial", 18, bold=True)
        self.font_go    = pygame.font.SysFont(
            "impact" if "impact" in pygame.font.get_fonts() else "arial",
            42, bold=True)
        self.font_small = pygame.font.SysFont("Arial", 16)

        self.clouds = [LaneCloud(random.randint(0, LANE_W)) for _ in range(4)]
        self.ground_offset = 0
        self.bg_offset = 0
        self.bg_index = 1

        self.reset()

    def reset(self):
        self.dino = Dino(x=80, folder=self.dino_folder)
        from config.settings import DINO_HEIGHT
        self.dino.y = GROUND_Y_LANE - DINO_HEIGHT
        self.dino.ground_y = GROUND_Y_LANE

        self.obstacles = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        self.game_over = False
        self.ground_offset = 0
        self.bg_offset = 0
        self.bg_index = 1
        self.go_flash_timer = 0
        
        self.last_action = (0, 0)
        self.frame_count = 0

    def _update_dino_physics(self):
        from config.settings import GRAVITY, DINO_HEIGHT
        d = self.dino
        ground = getattr(d, 'ground_y', GROUND_Y_LANE) - DINO_HEIGHT
        if d.is_jumping:
            d.vel_y += GRAVITY
            d.y += d.vel_y
            if d.y >= ground:
                d.y = ground
                d.vel_y = 0
                d.is_jumping = False
        anim = d._anim_name()
        from src.dino import _ANIM_FRAMES, _ANIM_SPEED
        if anim != d._cur_anim:
            d._cur_anim = anim
            d.anim_frame = 0
            d.anim_timer = 0
        else:
            d.anim_timer += 1
            if d.anim_timer >= _ANIM_SPEED.get(anim, 8):
                d.anim_timer = 0
                d.anim_frame = (d.anim_frame + 1) % _ANIM_FRAMES.get(anim, 1)

    def _spawn_obstacle(self):
        if self.last_obstacle_x - LANE_W < -MIN_OBSTACLE_SPAWN_DISTANCE:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(LANE_W + 50, speed)
            from src.obstacle import Cactus, Bird
            if isinstance(obs, Cactus):
                obs.y = GROUND_Y_LANE - obs.height
            else:
                from config.settings import GROUND_Y
                ratio = GROUND_Y_LANE / GROUND_Y
                obs.y = int(obs.y * ratio)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x

    def check_collision(self):
        from config.settings import DINO_HEIGHT
        d = self.dino
        h = d.height
        if d.is_ducking:
            from config.settings import DUCK_HEIGHT_RATIO
            h = int(d.height * DUCK_HEIGHT_RATIO)
        dino_rect = pygame.Rect(d.x, d.y + (d.height - h), d.width, h)
        margin = 6
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)
        for obs in self.obstacles:
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                return True
        return False

    def get_dino_rect(self):
        from config.settings import DUCK_HEIGHT_RATIO
        d = self.dino
        h = d.height
        if d.is_ducking:
            h = int(d.height * DUCK_HEIGHT_RATIO)
        return pygame.Rect(d.x, d.y + (d.height - h), d.width, h)

    def _collect_data(self, action):
        if not self.collect_data:
            return
        
        if action == self.last_action and self.frame_count % 10 != 0:
            return
        
        collector = get_collector()
        
        # Sử dụng record_sample để lưu dữ liệu đúng format
        collector.record_sample(
            dino=self.dino,
            obstacles=self.obstacles,
            game_speed=self.game_speed,
            action=action,
            source=self.player_type,
            ground_y=GROUND_Y_LANE,
            score=self.score
        )
        
        self.last_action = action
    
    def _get_inputs_for_collector(self):
        nearest = None
        min_dist = float("inf")
        for obs in self.obstacles:
            if obs.x > self.dino.x:
                dist = obs.x - self.dino.x
                if dist < min_dist:
                    min_dist = dist
                    nearest = obs
        
        if nearest is None:
            return [1.0, 0.5, 0.0, 0.0, 0.0, 0.0]
        
        from src.obstacle import Cactus
        
        dist_normalized = min(min_dist / 500, 1.0)
        obs_type = 0.0 if isinstance(nearest, Cactus) else 1.0
        speed_normalized = (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
        height_normalized = min((GROUND_Y_LANE - self.dino.y) / 100, 1.0)
        is_jumping = 1.0 if self.dino.is_jumping else 0.0
        is_ducking = 1.0 if self.dino.is_ducking else 0.0
        
        return [dist_normalized, obs_type, speed_normalized, height_normalized, is_jumping, is_ducking]

    def update(self, action=None, player_action=None):
        if self.game_over:
            self.go_flash_timer += 1
            if self.collect_data and len(get_collector().current_session_data) > 0:
                get_collector().save_session_data()
            return

        actual_action = (0, 0)
        
        if action is not None:
            jump, duck, _ = action
            if jump > 0.5:
                self.dino.jump()
                actual_action = (1, 0)
            self.dino.set_duck(duck > 0.5)
            if duck > 0.5 and not self.dino.is_jumping:
                actual_action = (actual_action[0], 1)
        elif player_action is not None:
            jump, duck = player_action
            if jump > 0.5 and not self.dino.is_jumping:
                self.dino.jump()
                actual_action = (1, 0)
            self.dino.duck(duck > 0.5)
            if duck > 0.5 and not self.dino.is_jumping:
                actual_action = (actual_action[0], 1)

        self._update_dino_physics()
        self._spawn_obstacle()

        self.ground_offset = (self.ground_offset + self.game_speed) % 64
        self.bg_offset = (self.bg_offset + self.game_speed * 0.15) % LANE_W

        prev = self.score
        for obs in self.obstacles:
            obs.update()
            if obs.x < self.dino.x and not obs.passed:
                obs.passed = True
                self.score += 1
        if self.score // 100 > prev // 100 and self.score > 0:
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
            if self.collect_data:
                get_collector().save_session_data()
        
        self.frame_count += 1
        self._collect_data(actual_action)

    def get_state(self):
        nearest = None
        min_dist = float("inf")
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
            min((GROUND_Y_LANE - self.dino.y) / 100, 1.0),
            1.0 if self.dino.is_jumping else 0.0,
        ]

    def draw(self, show_go=True):
        surf = self.surface

        bg = _get_bg(self.bg_index)
        ox = int(self.bg_offset) % LANE_W
        surf.blit(bg, (-ox, 0))
        if ox > 0:
            surf.blit(bg, (LANE_W - ox, 0))

        for c in self.clouds:
            c.draw(surf)

        tile_h = LANE_H - GROUND_Y_LANE
        tile_w = 64
        tile = _get_tile((tile_w, tile_h))
        if tile:
            off = int(self.ground_offset) % tile_w
            for x in range(-tile_w, LANE_W + tile_w, tile_w):
                surf.blit(tile, (x - off, GROUND_Y_LANE))
        else:
            pygame.draw.rect(surf, GROUND_COL, (0, GROUND_Y_LANE, LANE_W, tile_h))
            pygame.draw.line(surf, GROUND_LN, (0, GROUND_Y_LANE), (LANE_W, GROUND_Y_LANE), 2)

        self.dino.draw(surf)

        for obs in self.obstacles:
            obs.draw(surf)

        lbl = self.font_label.render(self.label, True, self.label_color)
        surf.blit(lbl, (8, 6))

        score_txt = self.font_hud.render(f"SCORE {self.score:05d}", True, (255, 255, 255))
        surf.blit(score_txt, (LANE_W // 2 - score_txt.get_width() // 2, 6))

        spd_txt = self.font_small.render(f"SPD {self.game_speed:.1f}", True, (180, 255, 180))
        surf.blit(spd_txt, (LANE_W - spd_txt.get_width() - 8, 6))

        if self.collect_data:
            data_icon = self.font_small.render("●", True, (0, 255, 0))
            surf.blit(data_icon, (LANE_W - 25, 28))

        if self.game_over and show_go:
            fade_progress = min(1.0, self.go_flash_timer / 20)

            ov = pygame.Surface((LANE_W, LANE_H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, int(160 * fade_progress)))
            surf.blit(ov, (0, 0))

            pw, ph = 300, 140
            px = LANE_W // 2 - pw // 2
            py = LANE_H // 2 - ph // 2

            panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
            panel.fill((15, 10, 5, int(220 * fade_progress)))
            surf.blit(panel, (px, py))

            flash = abs(math.sin(self.go_flash_timer * 0.1))
            border_col = (
                int(255 * fade_progress),
                int(180 * fade_progress + 50 * (1 - fade_progress)),
                int(50 * fade_progress)
            )
            pygame.draw.rect(surf, border_col, (px, py, pw, ph), 2, border_radius=10)

            go_shadow = self.font_go.render("GAME OVER", True, (80, 20, 10))
            surf.blit(go_shadow, go_shadow.get_rect(center=(LANE_W // 2 + 2, py + 42)))

            go = self.font_go.render("GAME OVER", True, (220, 50, 30))
            surf.blit(go, go.get_rect(center=(LANE_W // 2, py + 40)))

            score_txt = self.font_label.render(f"Diem: {self.score:05d}", True, (255, 230, 80))
            surf.blit(score_txt, score_txt.get_rect(center=(LANE_W // 2, py + 80)))

            hint = self.font_small.render("R - Thu lai  |  ESC - Menu", True, (200, 200, 200))
            surf.blit(hint, hint.get_rect(center=(LANE_W // 2, py + 115)))
