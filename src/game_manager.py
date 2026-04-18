"""
Game Manager - Quản lý vòng lặp game, tính điểm, va chạm
"""
import pygame
import random
import math
import  time

# Cache cho AI models - tránh load lai nhieu lan
_AI_CACHE = {
    'neat': {'net': None, 'config': None, 'label': None},
    'supervised': {'jump_model': None, 'duck_model': None, 'jump_scaler': None, 'duck_scaler': None, 'label': None},
    'hybrid': {'ai': None, 'label': None}
}

def clear_ai_cache():
    """Xoa cache AI"""
    global _AI_CACHE
    _AI_CACHE = {
        'neat': {'net': None, 'config': None, 'label': None},
        'supervised': {'jump_model': None, 'duck_model': None, 'jump_scaler': None, 'duck_scaler': None, 'label': None},
        'hybrid': {'ai': None, 'label': None}
    }

from config.settings import (
    MAX_SPEED_TIME, MAX_X2_TIME, SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
    COLLISION_MARGIN, COIN_HEIGHT, COIN_WIDTH, PLUS_COUNT_SWORD
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.items import Coin, Shield, SpeedItem, X2Item, SwordItem
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound, load_image, CLOUD_POSITIONS
from src.achievements import check_achievements
from src.ui import UILayer
from src.menu import settings as game_settings
from src.utils import (
    get_cached_font, get_gradient_bg, clear_gradient_cache,
    get_hud_bg_surface, PARTICLE_COLORS, GO_RED, GO_GREEN,
)

SKY_TOP     = (100, 180, 230)
SKY_BOT     = (255, 210, 120)
GROUND_COL  = (160, 120, 60)
GROUND_LINE = (120, 85, 35)
CLOUD_COL   = (255, 255, 255)
TEXT_LIGHT  = (255, 255, 255)
GO_BORDER   = (255, 200, 50)


# ==================== GLOBAL CACHES ====================
# Tile cache
_tile_cache = {}


def _get_cached_tile(name, size):
    """Cache ground tiles."""
    key = (name, size)
    if key not in _tile_cache:
        _tile_cache[key] = load_image(f"tiles/{name}", size)
    return _tile_cache[key]


def clear_game_cache():
    """Xóa tất cả cache - gọi khi cần reset hoặc thay đổi settings."""
    global _tile_cache
    _tile_cache = {}
    clear_gradient_cache()


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color')

    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1, 4)
        self.life = random.randint(20, 45)
        self.max_life = self.life
        self.size = random.randint(4, 10)
        self.color = random.choice(PARTICLE_COLORS)
    

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.life -= 1

    def draw(self, screen):
        alpha = int(255 * self.life / self.max_life)
        if alpha <= 0:
            return
        r, g, b = self.color
        # Reuse surface if possible - create small surface only when needed
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (self.size, self.size), self.size)
        screen.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


class DustParticle:
    """Bụi khi chạy trên ground - tạo cảm giác chuyển động"""
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color')

    def __init__(self, x, y):
        self.x = x
        self.y = y
        # Bay ngược lại so với hướng di chuyển của dino
        self.vx = random.uniform(-1.5, -0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.life = random.randint(15, 25)
        self.max_life = self.life
        self.size = random.randint(2, 5)
        # Màu bụi - nâu nhạt
        self.color = (180, 160, 130)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.size = max(1, self.size - 0.1)

    def draw(self, screen):
        alpha = int(180 * self.life / self.max_life)
        if alpha <= 0:
            return
        r, g, b = self.color
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (self.size, self.size), self.size)
        screen.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


class Cloud:
    __slots__ = ('x', 'y', 'speed', 'w', 'h')

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


# Background cache - sử dụng assets_loader hoặc fallback gradient
_bg_cache = {}


def _get_bg(bg_index):
    if bg_index not in _bg_cache:
        img = load_image(f"background/bg{bg_index}.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        if img is None:
            img = get_gradient_bg(SCREEN_WIDTH, SCREEN_HEIGHT, bg_index, SKY_TOP, SKY_BOT)
        _bg_cache[bg_index] = img
    return _bg_cache[bg_index]


def clear_game_cache():
    """Xóa tất cả cache - gọi khi cần reset hoặc thay đổi settings."""
    global _bg_cache, _tile_cache
    _bg_cache = {}
    _tile_cache = {}
    clear_gradient_cache()


class GameManager:
    def __init__(self, screen, is_ai_mode=False):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.is_ai_mode = is_ai_mode
        self.highscore_human, self.highscore_ai = load_highscore()

        # Sử dụng cached fonts thay vì tạo mới
        self.font_hud   = get_cached_font('Arial', 24, bold=True)
        self.font_large = get_cached_font('impact', 68, bold=True)
        self.font_med   = get_cached_font('Arial', 30, bold=True)
        self.font_small = get_cached_font('Arial', 20)
        self.font_speed = get_cached_font('Arial', 18)

        self.pause_btn = pygame.Rect(SCREEN_WIDTH - 70, 10, 50, 50)
        self.clouds = [
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(20, 150))
            for _ in range(7)
        ]
        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []  # Particles khi chết
        self.dust_particles = []  # Bụi khi chạy
        self._dust_spawn_timer = 0  # Timer để spawn bụi
        self.go_flash_timer = 0
        self.bg_index = 1
        self.last_coin_x = 0  # Cache vị trí coin cuối cùng để spawn hợp lý
        self.last_item_x = 0  # Cache vị trí item cuối cùng để spawn hợp lý
        self.next_spawn_items_score = 0  # Điểm để spawn item tiếp theo

        # UILayer để vẽ 
        self.ui = UILayer(screen)

        # Cache dino rect để tránh tạo mới mỗi frame
        self._dino_rect_cache = None

        # Input smoothing
        self._jump_pressed = False
        self._jump_released = True
        self._last_jump_state = False

        # Bien đếm thời gian buff item
        self.speed_buff_timer = 0  # Đếm ngược thời gian chạy nhanh
        self.x2_buff_timer = 0     # Đếm ngược thời gian x2 vàng

        self.reset()

    def reset(self):
        skin = getattr(game_settings, 'skin_dino', 'dino') if not self.is_ai_mode else 'ai_dino'
        self.dino = Dino(folder=skin)
        self.obstacles = []
        self.items = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        self.game_over = False
        self.paused = False
        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []
        self.dust_particles = []
        self._dust_spawn_timer = 0
        self.go_flash_timer = 0
        self.bg_index = 1
        self.next_spawn_items_score = 0
        self.speed_buff_timer = 0  # Đếm ngược thời gian chạy nhanh
        self.x2_buff_timer = 0

        # Achievement popup state
        self.pending_achievements = []
        self.ach_popup_timer = 0
        self.ach_popup_item = None
        self._start_ticks = pygame.time.get_ticks()

        # Cache giá trị tính toán thường dùng
        self._half_screen = SCREEN_WIDTH // 2

    def toggle_pause(self):
        self.paused = not self.paused

    def spawn_obstacle(self):
        # Lấy khoảng cách mục tiêu, nếu chưa có thì lấy số mặc định là 600
        target_distance = getattr(self, 'next_spawn_distance', 600)
        
        # TÌM XU CỦA ĐỒNG XU CUỐI CÙNG (Nếu có)
        last_coin_x = max([i.x for i in getattr(self, 'items', [])]) if getattr(self, 'items', []) else 0
        dist_to_last_coin = (SCREEN_WIDTH + 50) - last_coin_x

        dist_to_last_item = (SCREEN_WIDTH + 50) - self.last_item_x if getattr(self, 'last_item_x', 0) else float('inf')
        
        # KIỂM TRA: Đủ khoảng cách với cây cũ VÀ đủ khoảng cách với đồng xu mới nhất va item mới nhất không (để tránh spawn chồng lên nhau)
        if (SCREEN_WIDTH - self.last_obstacle_x) > target_distance and dist_to_last_coin > 150 and dist_to_last_item > 150:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            
            # Khởi tạo chướng ngại vật mới ở tít ngoài mép phải màn hình
            spawn_x = SCREEN_WIDTH + 50
            obs = create_obstacle(spawn_x, speed)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x
        
            # Bốc thăm khoảng cách cho cây tiếp theo
            self.next_spawn_distance = random.randint(500, 1000)

    def check_collision(self):
        # Early exit nếu không có obstacle
        if not self.obstacles:
            return False

        # Tối ưu: lấy rect một lần, tính margin một lần
        dino_rect = self.dino.get_rect()
        # Sử dụng margin từ settings
        margin = COLLISION_MARGIN
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)

        # Early exit: kiểm tra khoảng cách trước
        dino_x = dino_rect.x
        for obs in self.obstacles:
            # Bỏ qua obstacle ở xa
            if obs.x > dino_x + 100:
                continue
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                if self.dino.has_shield:
                    # Nếu có khiên: Làm vỡ khiên và tha mạng!
                    self.dino.has_shield = False
                    
                    # QUAN TRỌNG: Bạn phải xóa luôn chướng ngại vật đó đi 
                    # Nếu không frame tiếp theo (1/60 giây sau) nó lại cạ vào Dino báo Game over đấy
                    self.obstacles.remove(obs) 
                    #play_sound("shield_break") # Phát tiếng vỡ khiên
                else:
                    # Không có khiên -> Chết như bình thường
                    self.game_over = True
        return False

    def update(self, action=None, speed_mult=1.0, jump_held=False):
        """
        Cập nhật game state.
        action    : None (human), hoặc (jump, duck, nothing) từ AI
        speed_mult: hệ số tốc độ obstacle (A=0.5, bình thường=1.0, D=1.5)
        jump_held : True nếu phím nhảy đang được giữ (variable jump height)
        """
        if self.paused:
            return
        if self.game_over:
            self.particles = [p for p in self.particles if p.life > 0]
            for p in self.particles:
                p.update()
            self.go_flash_timer += 1
            return
        
        # Cập nhật thời gian buff
        if self.speed_buff_timer > 0:
            self.speed_buff_timer -= 1
        if self.x2_buff_timer > 0:
            self.x2_buff_timer -= 1

        # Tính tốc độ chạy của ván game hiện tại
        # Nếu đang có buff tốc độ, cho mọi thứ trôi nhanh gấp rưỡi (1.1)
        current_speed_multiplier = 1.1 if self.speed_buff_timer > 0 else 1.0

        # Khi update chướng ngại vật, nền, item, nhớ nhân với hệ số này
        actual_speed = self.game_speed * current_speed_multiplier

        # Xử lý input AI
        if action is not None:
            jump, duck = action[0], action[1] if len(action) > 1 else (0, 0)
            if jump > 0.5:
                self.dino.jump()
            self.dino.duck(duck > 0.5)

        self.dino.update(jump_held=jump_held)

        # Spawn dust particles khi đang chạy trên ground
        if not self.game_over and not self.paused:
            if self.dino.is_on_ground and not self.dino.is_jumping:
                self._dust_spawn_timer += 1
                # Spawn bụi mỗi 3-5 frames tùy tốc độ
                spawn_rate = max(3, 8 - int(self.game_speed / 3))
                if self._dust_spawn_timer >= spawn_rate:
                    self._dust_spawn_timer = 0
                    # Spawn bụi ở vị trí chân dino
                    dino_rect = self.dino.get_rect()
                    for _ in range(2):  # Spawn 2 particles mỗi lần
                        dust = DustParticle(
                            dino_rect.right - 5,
                            dino_rect.bottom - 2
                        )
                        self.dust_particles.append(dust)

        # Update dust particles
        self.dust_particles = [p for p in self.dust_particles if p.life > 0]
        for p in self.dust_particles:
            p.update()

        self.spawn_obstacle()

        # self.ground_offset = (self.ground_offset + self.game_speed * speed_mult) % 64
        # self.bg_offset = (self.bg_offset + self.game_speed * speed_mult * 0.05) % SCREEN_WIDTH
        self.ground_offset = (self.ground_offset + actual_speed) % 64
        self.bg_offset = (self.bg_offset + actual_speed * 0.05) % SCREEN_WIDTH  

        prev_score = self.score
        for obs in self.obstacles:
            old_x = obs.x
            # Tốc độ thực tế = tốc độ cơ bản của obs * hệ số của human/AI (speed_mult) * buff tốc độ
            obs_actual_speed = obs.speed * speed_mult * current_speed_multiplier 
            obs.x = old_x - obs_actual_speed
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

        # 1. Sinh ra Coin ngẫu nhiên nếu đủ điều kiện
        start_coin_x = SCREEN_WIDTH + 50
        dist_to_last_obs = start_coin_x - self.last_obstacle_x

        expected_next_obs_x = self.last_obstacle_x + getattr(self, 'next_spawn_distance', 500)
        dist_to_next_obs = expected_next_obs_x - start_coin_x

        self.last_coin_x = max(i.x for i in self.items) if self.items else 0
        dist_to_last_coin = start_coin_x - self.last_coin_x

        if (len(self.items) < 5 and random.random() < 0.03 and 
            dist_to_last_obs > 250 and 
            dist_to_next_obs > 250 and 
            dist_to_last_coin > 350):
                count_coins = random.randint(1, 4)
                for i in range(count_coins):
                    if len(self.items) < 5 :
                        coin_x = start_coin_x + i * 50
                        coin_speed = self.game_speed
                        self.items.append(Coin(coin_x, coin_speed))

        # 2. Cập nhật và kiểm tra ăn Item
        dino_rect = self.dino.get_rect()
        for item in self.items:    
            old_x = item.x
            item.update()
            # Áp dụng buff tốc độ cho item
            item_actual_speed = item.speed * speed_mult * current_speed_multiplier
            item.x = old_x - item_actual_speed  
           
            if dino_rect.colliderect(item.get_rect()) and not item.is_collected:
                item.is_collected = True
                
                if isinstance(item, Shield):
                    self.dino.has_shield = True
                    
                elif isinstance(item, SpeedItem):
                    self.speed_buff_timer = MAX_SPEED_TIME # Ví dụ game chạy 60 FPS -> 300 frame = 5 giây
                    
                elif isinstance(item, X2Item):
                    self.x2_buff_timer = MAX_X2_TIME # x2 vàng trong 10 giây
                    
                elif isinstance(item, SwordItem):
                    self.dino.sword_charges += PLUS_COUNT_SWORD # Cho phép chém 2 lần
                    
                else: # Mặc định là Coin
                    # Nếu đang có buff x2 thì nhân đôi điểm, không thì nhân 1
                    multiplier = 2 if self.x2_buff_timer > 0 else 1
                    self.score += getattr(item, 'bonus_points', 10) * multiplier

        # 3. Lọc bỏ các Coin đã bay ra khỏi màn hình hoặc ĐÃ BỊ ĂN
        self.items = [i for i in self.items if not i.is_off_screen() and not i.is_collected]

        # Create items every 50 points
        if self.score > self.next_spawn_items_score and self.score > 0:
            item_x = SCREEN_WIDTH + 50
            
            # THÊM ĐOẠN NÀY: Kiểm tra khoảng cách với chướng ngại vật gần nhất
            dist_to_last_obs = item_x - getattr(self, 'last_obstacle_x', 0)
            
            # Chỉ sinh item nếu cách chướng ngại vật ít nhất 200 pixel
            if dist_to_last_obs > 200:
                item_speed = self.game_speed
                item_type = random.choice(['shield', 'speed', 'x2', 'sword'])
                
                if item_type == 'shield':
                    self.items.append(Shield(item_x, item_speed))
                elif item_type == 'speed':
                    self.items.append(SpeedItem(item_x, item_speed))
                elif item_type == 'x2':
                    self.items.append(X2Item(item_x, item_speed))
                elif item_type == 'sword':
                    self.items.append(SwordItem(item_x, item_speed))

                # Chỉ cộng mốc điểm khi item THỰC SỰ đã được sinh ra
                self.next_spawn_items_score += 50

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
            # Kiểm tra và trigger achievements
            newly = check_achievements(score=self.score, obstacles=self.score)
            self.pending_achievements.extend(newly)

            # Lưu game session vào DB (non-blocking)
            try:
                from src.database_handler import save_game_session, save_highscore_db
                elapsed_ms = pygame.time.get_ticks() - getattr(self, '_start_ticks', pygame.time.get_ticks())
                game_mode = 'ai_pve' if self.is_ai_mode else 'human'
                player_type = 'ai' if self.is_ai_mode else 'human'
                save_game_session(
                    game_mode=game_mode,
                    player_type=player_type,
                    score=self.score,
                    game_duration=elapsed_ms // 1000,
                    end_reason='collision'
                )
                save_highscore_db(player_type, self.score, game_mode)
            except Exception:
                pass  # DB không có thì bỏ qua

        # Tiến trình hiển thị achievement popup
        if self.ach_popup_item is None and self.pending_achievements:
            self.ach_popup_item = self.pending_achievements.pop(0)
            self.ach_popup_timer = 180  # hiện 3 giây (60fps x 3)
        if self.ach_popup_timer > 0:
            self.ach_popup_timer -= 1
            if self.ach_popup_timer == 0:
                self.ach_popup_item = None

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

    def _draw_hud(self):
        h = max(self.highscore_ai if self.is_ai_mode else self.highscore_human, self.score)

        # Sử dụng cached HUD background
        self.screen.blit(get_hud_bg_surface(), (self._half_screen - 130, 5))

        score_txt = self.font_hud.render(f"SCORE  {self.score:05d}", True, (255, 230, 80))
        hi_txt    = self.font_hud.render(f"HI  {h:05d}", True, (200, 200, 200))
        spd_txt   = self.font_speed.render(f"SPD  {self.game_speed:.1f}", True, (150, 230, 150))
        self.screen.blit(score_txt, (self._half_screen - 118, 12))
        self.screen.blit(hi_txt,    (self._half_screen - 118, 38))
        self.screen.blit(spd_txt,   (self._half_screen + 30,  38))

        # Speed bar
        bar_x, bar_y, bar_w, bar_h = self._half_screen + 30, 14, 90, 10
        ratio = (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
        pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = max(1, int(bar_w * ratio))
        bar_color = (int(80 + 175 * ratio), int(200 - 150 * ratio), 50)
        pygame.draw.rect(self.screen, bar_color,
                         (bar_x, bar_y, fill_w, bar_h), border_radius=4)
    
    def _draw_achievement_popup(self):
        """Vẽ popup thành tựu mới mở khóa - slide in từ phải sang."""
        if self.ach_popup_item is None:
            return
        # Tính alpha fade-out ở cuối
        t = self.ach_popup_timer
        if t > 150:
            alpha = 255
        else:
            alpha = int(255 * t / 150)

        pw, ph = 300, 70
        margin = 12
        px = SCREEN_WIDTH - pw - margin
        py = margin

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 30, int(220 * alpha / 255)))
        self.screen.blit(panel, (px, py))
        pygame.draw.rect(self.screen, (255, 200, 50), (px, py, pw, ph), 2, border_radius=8)

        icon = self.ach_popup_item.get('icon', '🏆')
        name = self.ach_popup_item.get('name', 'Achievement')

        header = self.font_small.render("NEW ACHIEVEMENT!", True, (255, 200, 50))
        self.screen.blit(header, (px + 8, py + 6))
        name_surf = self.font_small.render(f"{icon} {name}", True, (255, 255, 255))
        self.screen.blit(name_surf, (px + 8, py + 32))

    def draw(self):
        self.ui._draw_background(self.bg_offset)
        for c in self.clouds:
            c.draw(self.screen)
        self.ui._draw_ground(self.ground_offset)

        # Vẽ dust particles TRƯỚC dino (để dino đè lên)
        for p in self.dust_particles:
            p.draw(self.screen)

        self.dino.draw(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)
        self._draw_hud()
        #self._draw_pause_btn()
        self.ui._draw_pause_btn(self.paused)
        if self.paused:
            # self._draw_paused_overlay()
            self.ui.draw_pause_menu()
        elif self.game_over:
            self.ui.draw_game_over(self.score)
        self._draw_achievement_popup()
        
        pygame.draw.rect(self.screen, (0, 255, 0), self.dino.get_rect(), 2)
        for obs in self.obstacles:
            pygame.draw.rect(self.screen, (255, 0, 0), obs.get_rect(), 2)

        for item in self.items:
            item.draw(self.screen)

        self.ui.draw_buffs(
            self.speed_buff_timer, MAX_SPEED_TIME, 
            self.x2_buff_timer, MAX_X2_TIME, 
            self.dino.sword_charges,
            self.dino.has_shield
        )

        pygame.display.flip()

    def run_human_mode(self):
        """
        Chế độ chơi thủ công.
        - SPACE / ↑ : nhảy
        - ↓         : cúi (giữ phím)
        - A         : obstacle chậm lại 50%
        - D         : obstacle nhanh lên 150%
        - P         : pause/resume
        - R         : restart (khi game over)
        - ESC       : về menu (khi game over)
        """
        running = True
        while running:
            # --- Đọc phím giữ để tính speed_mult ---
            keys = pygame.key.get_pressed()
            speed_mult = 1.0
            jump_held = False
            if not self.paused and not self.game_over:
                if keys[pygame.K_a]:
                    speed_mult = 0.5   # A: chậm 50%
                elif keys[pygame.K_d]:
                    speed_mult = 1.5   # D: nhanh 150%
                # Nếu bấm T VÀ còn lượt dùng kiếm
                elif keys[pygame.K_t] and self.dino.sword_charges > 0:
                    
                    # Tìm xem có chướng ngại vật nào đang ở TRƯỚC MẶT khủng long không (khoảng cách tầm 150 pixel)
                    for obs in self.obstacles:
                        # Nếu khoảng cách từ khủng long đến chướng ngại vật nằm trong tầm chém
                        if 0 < (obs.x - self.dino.get_rect().right) < 150:
                            # Tiêu diệt chướng ngại vật đó!
                            self.obstacles.remove(obs)
                            self.dino.sword_charges -= 1 # Trừ 1 lần chém
                            
                            # (Tùy chọn) Thêm âm thanh chém kiếm hoặc sinh ra tia lửa ở vị trí obs.x
                            # play_sound("sword_slash")
                            break # Chém trúng 1 cái là dừng vòng lặp, chờ bấm T lần sau mới chém tiếp

                # Track trạng thái jump key
                jump_held = keys[pygame.K_SPACE] or keys[pygame.K_UP]

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not self.game_over and not self.paused:
                            self.dino.jump_press()
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
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        self.dino.jump_release()
                    if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.dino.duck(False)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.ui.is_pause_button_clicked(event.pos) and not self.game_over:
                        self.toggle_pause()
                    if  self.paused :
                        action = self.ui.handle_pause_menu_click(event.pos)
                        if action == "Resume":
                            self.paused = False
                        elif action == "Restart":
                            self.reset()
                        elif action == "Quit":
                            running = False

            # Update với jump_held để hỗ trợ variable jump height
            self.update(speed_mult=speed_mult, jump_held=jump_held)
            self.draw()
            self.clock.tick(FPS)

    def run_pve_mode(self, ai_type='neat'):
        """
        Chạy chế độ PVE.
        ai_type: 'neat', 'supervised', hoặc 'hybrid'
        """
        from src.lane_game import LaneGame, LANE_H
        from src.ai_handler import load_genome, _get_inputs_from_lane
        import neat

        # Load AI (su dung cache)
        net = None
        jump_model, duck_model = None, None
        jump_scaler, duck_scaler = None, None
        hybrid_ai = None
        cache = _AI_CACHE.get(ai_type)

        if ai_type == 'neat':
            if cache and cache.get('net') is not None:
                net = cache['net']
                config = cache['config']
                ai_label = cache.get('label', "AI (NEAT)")
                print("Su dung cache NEAT AI")
            else:
                genome, config = load_genome()
                net = neat.nn.FeedForwardNetwork.create(genome, config) if genome else None
                ai_label = "AI (NEAT)"
                _AI_CACHE['neat'] = {'net': net, 'config': config, 'label': ai_label}
                print("Da cache NEAT AI")

        elif ai_type == 'supervised':
            if cache and cache.get('jump_model') is not None:
                jump_model = cache['jump_model']
                duck_model = cache['duck_model']
                jump_scaler = cache['jump_scaler']
                duck_scaler = cache['duck_scaler']
                ai_label = cache.get('label', "AI (Supervised)")
                print("Su dung cache Supervised AI")
            else:
                try:
                    from src.supervised_trainer import load_models, predict_action
                    jump_data, duck_data = load_models()
                    if jump_data and duck_data:
                        jump_model, jump_scaler = jump_data['model'], jump_data['scaler']
                        duck_model, duck_scaler = duck_data['model'], duck_data['scaler']
                        ai_label = "AI (Supervised)"
                        _AI_CACHE['supervised'] = {
                            'jump_model': jump_model, 'duck_model': duck_model,
                            'jump_scaler': jump_scaler, 'duck_scaler': duck_scaler,
                            'label': ai_label
                        }
                        print("Da cache Supervised AI")
                    else:
                        print("Khong load duoc supervised model! Dung NEAT...")
                        genome, config = load_genome()
                        net = neat.nn.FeedForwardNetwork.create(genome, config) if genome else None
                        ai_label = "AI (NEAT)"
                except Exception as e:
                    print(f"Loi load supervised: {e}. Dung NEAT...")
                    genome, config = load_genome()
                    net = neat.nn.FeedForwardNetwork.create(genome, config) if genome else None
                    ai_label = "AI (NEAT)"

        elif ai_type == 'hybrid':
            if cache and cache.get('ai') is not None:
                hybrid_ai = cache['ai']
                ai_label = cache.get('label', "AI (Hybrid)")
                print("Su dung cache Hybrid AI")
            else:
                try:
                    from src.ai_handler import get_hybrid_ai
                    hybrid_ai = get_hybrid_ai()
                    ai_label = "AI (Hybrid)"
                    _AI_CACHE['hybrid'] = {'ai': hybrid_ai, 'label': ai_label}
                    print("Da cache Hybrid AI")
                except Exception as e:
                    print(f"Loi load hybrid: {e}. Dung NEAT...")
                    genome, config = load_genome()
                    net = neat.nn.FeedForwardNetwork.create(genome, config) if genome else None
                    ai_label = "AI (NEAT)"

        ai_lane     = LaneGame('ai_dino', ai_label, label_color=(200, 150, 255))
        player_lane = LaneGame('dino',    'PLAYER',   label_color=(255, 230, 80))
        div = pygame.Surface((SCREEN_WIDTH, 4)); div.fill((255, 200, 50))
        font_hint = get_cached_font('Arial', 16)
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not player_lane.game_over: player_lane.dino.jump_press()
                    if event.key == pygame.K_DOWN:
                        if not player_lane.game_over: player_lane.dino.duck(True)
                    if event.key == pygame.K_r: ai_lane.reset(); player_lane.reset()
                    if event.key == pygame.K_ESCAPE: running = False
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        player_lane.dino.jump_release()
                    if event.key == pygame.K_DOWN: player_lane.dino.duck(False)

            if not ai_lane.game_over:
                if ai_type == 'neat' and net:
                    ai_lane.update(action=net.activate(_get_inputs_from_lane(ai_lane)))
                elif ai_type == 'supervised' and jump_model and duck_model:
                    # Get inputs for supervised model
                    from src.ai_handler import _get_inputs
                    inputs = _get_inputs(ai_lane.dino, ai_lane.obstacles, ai_lane.game_speed)
                    action = predict_action(jump_model, jump_scaler, duck_model, duck_scaler, inputs)
                    ai_lane.update(action=action[:2])  # Take first 2 values (jump, duck)
                elif ai_type == 'hybrid' and hybrid_ai:
                    # Hybrid AI prediction
                    from src.ai_handler import _get_inputs
                    inputs = _get_inputs(ai_lane.dino, ai_lane.obstacles, ai_lane.game_speed)
                    action = hybrid_ai.predict(inputs)
                    ai_lane.update(action=action)
                else:
                    ai_lane.update()
            else:
                ai_lane.update()

            player_lane.update()
            ai_lane.draw(); player_lane.draw()
            self.screen.blit(ai_lane.surface, (0, 0))
            self.screen.blit(div, (0, LANE_H))
            self.screen.blit(player_lane.surface, (0, LANE_H + 4))
            if ai_lane.game_over or player_lane.game_over:
                hint = font_hint.render('R - Retry  |  ESC - Menu', True, (220, 220, 220))
                self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, LANE_H * 2 + 4 - 12)))
            pygame.display.flip(); self.clock.tick(FPS)

    def run_pvp_mode(self):
        from src.lane_game import LaneGame, LANE_H
        from src.utils import get_cached_font

        # --- BƯỚC 1: TẠO MAP GIỐNG HỆT NHAU ---
        # Tạo một hạt giống (seed) ngẫu nhiên cho ván đấu này
        random.seed(time.time())

        # Lưu lại trạng thái của cỗ bài
        shared_initial_state = random.getstate()

        # Khởi tạo P1 (P1 sẽ rút vài lá bài để tạo mây)
        p1 = LaneGame('dino', 'PLAYER 1', label_color=(255, 230, 80), collect_data=False, player_type="human")  # Tắt data collection để tăng FPS
        p1_rand_state = random.getstate()  # Cất cỗ bài của P1 đi

        # Reset cỗ bài về trạng thái ban đầu cho P2
        random.setstate(shared_initial_state)

        # Khởi tạo P2 (Lúc này P2 sẽ rút được các lá bài tạo mây GIỐNG HỆT P1)
        p2 = LaneGame('ai_dino', 'PLAYER 2', label_color=(200, 150, 255), collect_data=False, player_type="ai")  # Tắt data collection để tăng FPS
        p2_rand_state = random.getstate()  # Cất cỗ bài của P2 đi
        # ---------------------------------------

        div = pygame.Surface((SCREEN_WIDTH, 4))
        div.fill((255, 200, 50))

        font_res = get_cached_font('Arial', 22, bold=True)
        font_hint = get_cached_font('Arial', 16)

        running = True

        # Track keys đang được nhấn
        p1_keys = {'jump': False, 'duck': False}
        p2_keys = {'jump': False, 'duck': False}

        # Cache surfaces để không vẽ lại khi đã game over
        p1_surface_cache = None
        p2_surface_cache = None
        both_game_over_drawn = False

        while running:
            # Đọc phím liên tục mỗi frame
            keys = pygame.key.get_pressed()

            # P1: W = Jump, S = Duck (chỉ xử lý nếu chưa game over)
            if not p1.game_over:
                if keys[pygame.K_w]:
                    if not p1_keys['jump']:
                        p1.dino.jump_press()
                        p1_keys['jump'] = True
                else:
                    if p1_keys['jump']:
                        p1.dino.jump_release()
                        p1_keys['jump'] = False

                if keys[pygame.K_s]:
                    p1.dino.duck(True)
                    p1_keys['duck'] = True
                else:
                    if p1_keys['duck']:
                        p1.dino.duck(False)
                        p1_keys['duck'] = False

            # P2: Up = Jump, Down = Duck (chỉ xử lý nếu chưa game over)
            if not p2.game_over:
                if keys[pygame.K_UP]:
                    if not p2_keys['jump']:
                        p2.dino.jump_press()
                        p2_keys['jump'] = True
                else:
                    if p2_keys['jump']:
                        p2.dino.jump_release()
                        p2_keys['jump'] = False

                if keys[pygame.K_DOWN]:
                    p2.dino.duck(True)
                    p2_keys['duck'] = True
                else:
                    if p2_keys['duck']:
                        p2.dino.duck(False)
                        p2_keys['duck'] = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    # Game controls
                    if event.key == pygame.K_r:
                        p1.reset()
                        p2.reset()
                        p1_keys = {'jump': False, 'duck': False}
                        p2_keys = {'jump': False, 'duck': False}
                        p1_surface_cache = None
                        p2_surface_cache = None
                        both_game_over_drawn = False
                    if event.key == pygame.K_ESCAPE:
                        running = False

            # --- BƯỚC 2: CẬP NHẬT TÁCH BIỆT "VŨ TRỤ" ---

            # Chỉ update P1 nếu chưa game over
            if not p1.game_over:
                random.setstate(p1_rand_state)
                p1.update()
                p1_rand_state = random.getstate()
            else:
                # P1 đã chết, vẽ lại surface cuối cùng và cache lại
                if p1_surface_cache is None:
                    p1.draw()
                    p1_surface_cache = p1.surface.copy()

            # Chỉ update P2 nếu chưa game over
            if not p2.game_over:
                random.setstate(p2_rand_state)
                p2.update()
                p2_rand_state = random.getstate()
            else:
                # P2 đã chết, vẽ lại surface cuối cùng và cache lại
                if p2_surface_cache is None:
                    p2.draw()
                    p2_surface_cache = p2.surface.copy()

            # --- KẾT THÚC BƯỚC 2 ---

            # Draw - sử dụng cache nếu đã game over
            if p1_surface_cache is not None:
                self.screen.blit(p1_surface_cache, (0, 0))
            else:
                p1.draw()
                self.screen.blit(p1.surface, (0, 0))

            self.screen.blit(div, (0, LANE_H))

            if p2_surface_cache is not None:
                self.screen.blit(p2_surface_cache, (0, LANE_H + 4))
            else:
                p2.draw()
                self.screen.blit(p2.surface, (0, LANE_H + 4))

            # Hiển thị kết quả khi cả hai game over
            if p1.game_over and p2.game_over:
                if not both_game_over_drawn:
                    if p1.score > p2.score:
                        msg, col = f'P1 THẮNG! ({p1.score} vs {p2.score})', (255, 230, 80)
                    elif p2.score > p1.score:
                        msg, col = f'P2 THẮNG! ({p2.score} vs {p1.score})', (200, 150, 255)
                    else:
                        msg, col = f'HÒA! ({p1.score})', (200, 200, 200)
                    res = font_res.render(msg, True, col)
                    self.screen.blit(res, res.get_rect(center=(SCREEN_WIDTH // 2, LANE_H + 2)))
                    both_game_over_drawn = True
                else:
                    # Vẽ lại kết quả đã cache
                    if p1.score > p2.score:
                        msg, col = f'P1 THẮNG! ({p1.score} vs {p2.score})', (255, 230, 80)
                    elif p2.score > p1.score:
                        msg, col = f'P2 THẮNG! ({p2.score} vs {p1.score})', (200, 150, 255)
                    else:
                        msg, col = f'HÒA! ({p1.score})', (200, 200, 200)
                    res = font_res.render(msg, True, col)
                    self.screen.blit(res, res.get_rect(center=(SCREEN_WIDTH // 2, LANE_H + 2)))

            # Hiển thị hint điều khiển
            hint = font_hint.render('P1: W=Jump, S=Duck  |  P2: Up=Jump, Down=Duck  |  R=Retry  |  ESC=Menu', True, (220, 220, 220))
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)))

            pygame.display.flip()
            self.clock.tick(120)  # PVP mode chạy 120 FPS mượt hơn
