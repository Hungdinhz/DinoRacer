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
        self.shield_buff_timer = 0 # Đếm ngược thời gian khiên

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
        self.ui.bg_index = 1
        self.next_spawn_items_score = 0
        self.speed_buff_timer = 0  # Đếm ngược thời gian chạy nhanh
        self.x2_buff_timer = 0
        self.shield_buff_timer = 0

        # Achievement popup state
        self.pending_achievements = []
        self.ach_popup_timer = 0
        self.ach_popup_item = None
        self._start_ticks = pygame.time.get_ticks()

        # Cache giá trị tính toán thường dùng
        self._half_screen = SCREEN_WIDTH // 2
        self.game_won = False

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
                
            obs_rect = obs.get_rect()
            if shrunk.colliderect(obs_rect.inflate(-margin, -margin)):
                # Lấy mask pixel-perfect
                dino_mask, dx, dy = self.dino.get_mask_info()
                obs_mask, ox, oy = obs.get_mask_info()
                
                is_collide = True
                if dino_mask and obs_mask:
                    offset = (int(ox - dx), int(oy - dy))
                    if not dino_mask.overlap(obs_mask, offset):
                        is_collide = False
                
                if is_collide:
                    if self.dino.has_shield:
                        # Nếu có khiên: Làm vỡ khiên và tha mạng!
                        self.dino.has_shield = False
                        self.shield_buff_timer = 0
                        
                        # QUAN TRỌNG: Bạn phải xóa luôn chướng ngại vật đó đi 
                        self.obstacles.remove(obs) 
                        play_sound("shield_broken")
                    else:
                        # Không có khiên -> Chết như bình thường
                        self.game_over = True
        return False

    def sword_slash(self):
        """Kích hoạt chém kiếm và phá chướng ngại vật ở tầm gần phía trước dino."""
        if self.dino.sword_charges <= 0:
            return False

        from src.obstacle import Bird

        self.dino.start_sword_slash()
        dino_right = self.dino.get_rect().right
        dino_y = self.dino.y
        for obs in self.obstacles:
            if isinstance(obs, Bird) and (dino_y - obs.y) > 50:
                continue
            if 0 < (obs.x - dino_right) < 150:
                self.obstacles.remove(obs)
                self.dino.sword_charges -= 1
                play_sound("sword_slash")
                return True
        return False

    def _create_lane_random_states(self, same_map=True):
        """Tạo state random riêng cho 2 lane, có thể giống nhau hoặc khác nhau."""
        base_seed = int(time.time() * 1000000)
        lane1_rng = random.Random(base_seed)
        lane1_state = lane1_rng.getstate()

        if same_map:
            lane2_state = lane1_state
        else:
            lane2_rng = random.Random(base_seed + 1)
            lane2_state = lane2_rng.getstate()

        return lane1_state, lane2_state

    def _create_lane_with_random_state(self, lane_state, *args, **kwargs):
        """Khởi tạo lane với random state cố định để đồng bộ map."""
        from src.lane_game import LaneGame

        previous_state = random.getstate()
        random.setstate(lane_state)
        lane = LaneGame(*args, **kwargs)
        updated_state = random.getstate()
        random.setstate(previous_state)
        return lane, updated_state

    def _update_lane_with_random_state(self, lane, lane_state, *args, **kwargs):
        """Update lane với random state riêng, tránh 2 lane ảnh hưởng nhau."""
        previous_state = random.getstate()
        random.setstate(lane_state)
        lane.update(*args, **kwargs)
        updated_state = random.getstate()
        random.setstate(previous_state)
        return updated_state

    def update(self, action=None, speed_mult=1.0, jump_held=False):
        """
        Cập nhật game state.
        action    : None (human), hoặc (jump, duck, nothing) từ AI
        speed_mult: hệ số tốc độ obstacle (A=0.5, bình thường=1.0, D=1.5)
        jump_held : True nếu phím nhảy đang được giữ (variable jump height)
        """
        if self.paused:
            return
        if getattr(self, 'game_won', False):
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
        if getattr(self, 'shield_buff_timer', 0) > 0:
            self.shield_buff_timer -= 1
            if self.shield_buff_timer == 0:
                self.dino.has_shield = False

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
        self.bg_index = min(1 + self.score // 200, 5)
        self.ui.bg_index = self.bg_index

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
                
                if isinstance(item, Coin):
                    play_sound("coin")
                else:
                    play_sound("item_pickup")
                
                if isinstance(item, Shield):
                    self.dino.has_shield = True
                    from config.settings import MAX_SHIELD_TIME
                    self.shield_buff_timer = MAX_SHIELD_TIME
                    
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
            # Luôn cộng mốc điểm NGAY KHI đạt ngưỡng — không phụ thuộc item có thực sự spawn được hay không
            self.next_spawn_items_score += 50

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

        for c in self.clouds:
            c.update()
            
        if self.score >= 1500 and not self.is_ai_mode:
            self.game_won = True
            # play_sound("win") # Bỏ comment nếu bạn có file âm thanh win
            return

        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
            rect = self.dino.get_rect()
            for _ in range(40):
                self.particles.append(Particle(rect.centerx, rect.centery))
            h_cur = self.highscore_ai if self.is_ai_mode else self.highscore_human
            if self.score > h_cur:
                if getattr(self, 'is_ai_mode', False):
                    self.highscore_ai = self.score
                    self.ui.highscore = self.score
                    save_highscore(ai=self.score)
                else:
                    self.highscore_human = self.score
                    self.ui.highscore = self.score
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

        score_label = self.font_hud.render("SCORE", True, (255, 230, 80))
        score_val   = self.font_hud.render(f"{self.score:05d}", True, (255, 230, 80))
        hi_label    = self.font_hud.render("HI", True, (200, 200, 200))
        hi_val      = self.font_hud.render(f"{h:05d}", True, (200, 200, 200))
        
        prog_percent = min(100, int((self.score / 1500) * 100))
        prog_txt  = self.font_speed.render(f"DEST {prog_percent}%", True, (0, 200, 255))
        
        self.screen.blit(score_label, (self._half_screen - 118, 12))
        self.screen.blit(score_val,   (self._half_screen - 30, 12))
        self.screen.blit(hi_label,    (self._half_screen - 118, 38))
        self.screen.blit(hi_val,      (self._half_screen - 30, 38))
        self.screen.blit(prog_txt,    (self._half_screen + 30,  38))

        # Progress bar
        bar_x, bar_y, bar_w, bar_h = self._half_screen + 30, 14, 90, 10
        ratio = min(1.0, self.score / 1500)
        pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = max(1, int(bar_w * ratio))
        pygame.draw.rect(self.screen, (0, 200, 255),
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
        if self.paused:
            self.ui.draw_pause_menu()
        elif getattr(self, 'game_won', False):
            self._draw_god_result()  # Nếu thắng thì gọi bảng GOD
        elif self.game_over:
            self.ui.draw_game_over(self.score) # Nếu thua thì gọi bảng Game Over
            
        self._draw_achievement_popup()
        

        for item in self.items:
            item.draw(self.screen)

        sword_key_str = "" if getattr(self, 'is_ai_mode', False) else "T"
        self.ui.draw_buffs(
            self.speed_buff_timer, MAX_SPEED_TIME, 
            self.x2_buff_timer, MAX_X2_TIME, 
            getattr(self, 'shield_buff_timer', 0), getattr(game_settings, 'MAX_SHIELD_TIME', 2400),
            self.dino.sword_charges,
            sword_key_str
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
                    if event.key == pygame.K_t:
                        if not self.game_over and not self.paused:
                            self.sword_slash()
                    if event.key == pygame.K_r and (self.game_over or getattr(self, 'game_won', False)):
                        self.reset()
                    if event.key == pygame.K_ESCAPE and (self.game_over or getattr(self, 'game_won', False)):
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

        same_map = getattr(game_settings, 'two_lane_map_mode', 'same') == 'same'
        ai_state, player_state = self._create_lane_random_states(same_map=same_map)

        ai_lane, ai_state = self._create_lane_with_random_state(
            ai_state,
            'ai_dino', ai_label,
            label_color=(200, 150, 255),
            sword_key='T'
        )
        player_lane, player_state = self._create_lane_with_random_state(
            player_state,
            'dino', 'PLAYER',
            label_color=(255, 230, 80),
            sword_key='T'
        )
        div = pygame.Surface((SCREEN_WIDTH, 4)); div.fill((255, 200, 50))
        font_hint = get_cached_font('Arial', 16)
        running = True
        game_ended = False
        match_result = None
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not player_lane.game_over: player_lane.dino.jump_press()
                    if event.key == pygame.K_DOWN:
                        if not player_lane.game_over: player_lane.dino.duck(True)
                    if event.key == pygame.K_r:
                        game_ended = False
                        match_result = None
                        ai_state, player_state = self._create_lane_random_states(same_map=same_map)
                        ai_lane, ai_state = self._create_lane_with_random_state(
                            ai_state,
                            'ai_dino', ai_label,
                            label_color=(200, 150, 255),
                            sword_key='T'
                        )
                        player_lane, player_state = self._create_lane_with_random_state(
                            player_state,
                            'dino', 'PLAYER',
                            label_color=(255, 230, 80),
                            sword_key='T'
                        ) 
                    if event.key == pygame.K_ESCAPE: running = False
                    if event.key == pygame.K_t:
                        if not player_lane.game_over: player_lane.sword_slash()
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        player_lane.dino.jump_release()
                    if event.key == pygame.K_DOWN: player_lane.dino.duck(False)

            if not ai_lane.game_over:
                # ===== HELPER: Rule-based obstacle dodge override =====
                def _apply_obstacle_dodge(action_list, lane):
                    """Scan tất cả obstacles và override AI action khi cần.
                    
                    Xử lý:
                    - CHIM: Detect chim trên đầu, cúi khi gần, không nhảy vào chim
                    - CACTUS: Safety net — nhảy khi cactus quá gần mà AI chưa phản ứng
                    """
                    from src.obstacle import Bird
                    dino_x = lane.dino.x
                    dino_right = dino_x + lane.dino.width

                    nearest_bird_dist = float('inf')
                    nearest_cactus_dist = float('inf')
                    bird_overhead = False

                    for obs in lane.obstacles:
                        if isinstance(obs, Bird):
                            bird_right = obs.x + obs.width
                            if bird_right > dino_x:
                                dist = max(0, obs.x - dino_x)
                                nearest_bird_dist = min(nearest_bird_dist, dist)
                                if obs.x < dino_right:
                                    bird_overhead = True
                        else:
                            if obs.x > dino_x:
                                dist = obs.x - dino_x
                                nearest_cactus_dist = min(nearest_cactus_dist, dist)

                    has_bird_near = nearest_bird_dist < 400

                    # === BIRD LOGIC ===
                    if bird_overhead:
                        # Chim TRÊN ĐẦU → buộc cúi
                        action_list[0] = 0
                        if len(action_list) > 1:
                            action_list[1] = 1
                        else:
                            action_list.append(1)
                    elif has_bird_near:
                        if nearest_cactus_dist < nearest_bird_dist and nearest_cactus_dist < 150:
                            # Cactus gần hơn chim → nhảy qua cactus
                            action_list[0] = 1
                            if len(action_list) > 1:
                                action_list[1] = 0
                        else:
                            # Chim đang tới → KHÔNG nhảy
                            action_list[0] = 0
                            if nearest_bird_dist < 350:
                                if len(action_list) > 1:
                                    action_list[1] = 1
                                else:
                                    action_list.append(1)
                    else:
                        # === CACTUS SAFETY NET ===
                        # Nếu cactus gần mà AI chưa nhảy → buộc nhảy
                        if nearest_cactus_dist < 200 and not lane.dino.is_jumping and not lane.dino.is_ducking:
                            action_list[0] = 1
                            if len(action_list) > 1:
                                action_list[1] = 0

                    return action_list
                # ===== END HELPER =====

                if ai_type == 'neat' and net:
                    inputs = _get_inputs_from_lane(ai_lane)
                    neat_output = list(net.activate(inputs))
                    neat_output = _apply_obstacle_dodge(neat_output, ai_lane)

                    ai_state = self._update_lane_with_random_state(
                        ai_lane, ai_state, action=neat_output
                    )
                elif ai_type == 'supervised' and jump_model and duck_model:
                    from src.ai_handler import _get_inputs
                    from src.lane_game import LOGIC_Y
                    inputs = _get_inputs(ai_lane.dino, ai_lane.obstacles, ai_lane.game_speed, ground_y=LOGIC_Y)
                    action = list(predict_action(jump_model, jump_scaler, duck_model, duck_scaler, inputs))
                    action = _apply_obstacle_dodge(action, ai_lane)

                    ai_state = self._update_lane_with_random_state(
                        ai_lane, ai_state, action=action[:2]
                    )
                elif ai_type == 'hybrid' and hybrid_ai:
                    from src.ai_handler import _get_inputs
                    from src.lane_game import LOGIC_Y
                    inputs = _get_inputs(ai_lane.dino, ai_lane.obstacles, ai_lane.game_speed, ground_y=LOGIC_Y)
                    action = list(hybrid_ai.predict(inputs))
                    action = _apply_obstacle_dodge(action, ai_lane)

                    ai_state = self._update_lane_with_random_state(ai_lane, ai_state, action=action)
                else:
                    ai_state = self._update_lane_with_random_state(ai_lane, ai_state)
            else:
                ai_state = self._update_lane_with_random_state(ai_lane, ai_state)

            player_state = self._update_lane_with_random_state(player_lane, player_state)
            if not game_ended:
                if ai_lane.game_over and player_lane.game_over:
                    if player_lane.score > ai_lane.score:
                        match_result = "YOU WIN!"
                    elif ai_lane.score > player_lane.score:
                        match_result = "AI WINS!"
                    else:
                        match_result = "DRAW!"
                    game_ended = True
            ai_lane.draw(show_go=False) 
            player_lane.draw(show_go=False)
            self.screen.blit(ai_lane.surface, (0, 0))
            self.screen.blit(div, (0, LANE_H))
            self.screen.blit(player_lane.surface, (0, LANE_H + 4))
            if game_ended:
                # 1. Phủ mờ toàn màn hình
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 180))
                self.screen.blit(ov, (0, 0))

                # 2. Vẽ khung bảng ở giữa
                pw, ph = 420, 220
                px, py = SCREEN_WIDTH // 2 - pw // 2, (LANE_H * 2 + 4) // 2 - ph // 2
                panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
                panel.fill((20, 25, 30, 240))
                self.screen.blit(panel, (px, py))
                pygame.draw.rect(self.screen, (255, 215, 0), (px, py, pw, ph), 3, border_radius=12)

                # 3. Vẽ chữ kết quả
                font_result = get_cached_font('impact', 50)
                font_score = get_cached_font('Arial', 24, bold=True)
                
                # Màu chữ tùy theo kết quả
                title_col = (255, 230, 80) if "YOU" in match_result else (200, 150, 255) if "AI" in match_result else (200, 200, 200)
                
                res_txt = font_result.render(match_result, True, title_col)
                self.screen.blit(res_txt, res_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 50)))

                p_txt = font_score.render(f"Your Score: {player_lane.score:05d}", True, (255, 230, 80))
                self.screen.blit(p_txt, p_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 110)))

                ai_txt = font_score.render(f"AI Score: {ai_lane.score:05d}", True, (200, 150, 255))
                self.screen.blit(ai_txt, ai_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 150)))
            
            hint = font_hint.render('R - Retry  |  ESC - Menu', True, (220, 220, 220))
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, LANE_H * 2 + 4 - 20)))
            pygame.display.flip(); self.clock.tick(FPS)

    def run_pvp_mode(self):
        from src.lane_game import LaneGame, LANE_H
        from src.utils import get_cached_font

        same_map = getattr(game_settings, 'two_lane_map_mode', 'same') == 'same'
        p1_rand_state, p2_rand_state = self._create_lane_random_states(same_map=same_map)

        p1, p1_rand_state = self._create_lane_with_random_state(
            p1_rand_state,
            'dino', 'PLAYER 1',
            label_color=(255, 230, 80),
            collect_data=False,
            player_type="human",
            sword_key='T'
        )
        p2, p2_rand_state = self._create_lane_with_random_state(
            p2_rand_state,
            'ai_dino', 'PLAYER 2',
            label_color=(200, 150, 255),
            collect_data=False,
            player_type="ai",
            sword_key='L'
        )

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
        game_ended = False
        match_result = None

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    # P1: W = Jump, S = Duck
                    if event.key == pygame.K_w and not p1.game_over:
                        if not p1_keys['jump']:
                            p1.dino.jump_press()
                            p1_keys['jump'] = True
                    if event.key == pygame.K_s and not p1.game_over:
                        if not p1_keys['duck']:
                            p1.dino.duck(True)
                            p1_keys['duck'] = True

                    # P2: Up = Jump, Down = Duck
                    if event.key == pygame.K_UP and not p2.game_over:
                        if not p2_keys['jump']:
                            p2.dino.jump_press()
                            p2_keys['jump'] = True
                    if event.key == pygame.K_DOWN and not p2.game_over:
                        if not p2_keys['duck']:
                            p2.dino.duck(True)
                            p2_keys['duck'] = True

                    # Game controls
                    if event.key == pygame.K_r:
                        # Reset trạng thái input để tránh kẹt phím
                        if p1_keys['jump']:
                            p1.dino.jump_release()
                        if p2_keys['jump']:
                            p2.dino.jump_release()
                        if p1_keys['duck']:
                            p1.dino.duck(False)
                        if p2_keys['duck']:
                            p2.dino.duck(False)

                        p1_rand_state, p2_rand_state = self._create_lane_random_states(same_map=same_map)
                        p1, p1_rand_state = self._create_lane_with_random_state(
                            p1_rand_state,
                            'dino', 'PLAYER 1',
                            label_color=(255, 230, 80),
                            collect_data=False,
                            player_type="human",
                            sword_key='T'
                        )
                        p2, p2_rand_state = self._create_lane_with_random_state(
                            p2_rand_state,
                            'ai_dino', 'PLAYER 2',
                            label_color=(200, 150, 255),
                            collect_data=False,
                            player_type="ai",
                            sword_key='L'
                        )
                        p1_keys = {'jump': False, 'duck': False}
                        p2_keys = {'jump': False, 'duck': False}
                        p1_surface_cache = None
                        p2_surface_cache = None
                        both_game_over_drawn = False
                        game_ended = False
                        match_result = None
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    # P1: T = Sword | P2: K_1 = Sword
                    if event.key == pygame.K_t:
                        if not p1.game_over: p1.sword_slash()
                    if event.key == pygame.K_l:
                        if not p2.game_over: p2.sword_slash()

                if event.type == pygame.KEYUP:
                    # P1: nhả W/S
                    if event.key == pygame.K_w:
                        if p1_keys['jump']:
                            p1.dino.jump_release()
                            p1_keys['jump'] = False
                    if event.key == pygame.K_s:
                        if p1_keys['duck']:
                            p1.dino.duck(False)
                            p1_keys['duck'] = False

                    # P2: nhả Up/Down
                    if event.key == pygame.K_UP:
                        if p2_keys['jump']:
                            p2.dino.jump_release()
                            p2_keys['jump'] = False
                    if event.key == pygame.K_DOWN:
                        if p2_keys['duck']:
                            p2.dino.duck(False)
                            p2_keys['duck'] = False

            # --- BƯỚC 2: CẬP NHẬT TÁCH BIỆT "VŨ TRỤ" ---

            # Chỉ update P1 nếu chưa game over
            if not p1.game_over:
                p1_rand_state = self._update_lane_with_random_state(p1, p1_rand_state)
            else:
                # P1 đã chết, vẽ lại surface cuối cùng và cache lại
                if p1_surface_cache is None:
                    p1.draw(show_go=False)
                    p1_surface_cache = p1.surface.copy()

            # Chỉ update P2 nếu chưa game over
            if not p2.game_over:
                p2_rand_state = self._update_lane_with_random_state(p2, p2_rand_state)
            else:
                # P2 đã chết, vẽ lại surface cuối cùng và cache lại
                if p2_surface_cache is None:
                    p2.draw(show_go=False)
                    p2_surface_cache = p2.surface.copy()

            # --- KẾT THÚC BƯỚC 2 ---

            # THÊM ĐOẠN LOGIC PHÂN ĐỊNH THẮNG THUA Ở ĐÂY
            if not game_ended:
                # Trường hợp 2 & 3: Cả 2 cùng chết
                if p1.game_over and p2.game_over:
                    if p1.score > p2.score:
                        match_result = "PLAYER 1 WINS!"
                    elif p2.score > p1.score:
                        match_result = "PLAYER 2 WINS!"
                    else:
                        match_result = "DRAW!"
                    game_ended = True

            # ==========================================

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

            # VẼ BẢNG KẾT QUẢ TỔNG
            if game_ended:
                # 1. Phủ mờ màn hình
                ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 180))
                self.screen.blit(ov, (0, 0))

                # 2. Vẽ khung bảng kết quả ở giữa màn hình
                pw, ph = 420, 220
                px = SCREEN_WIDTH // 2 - pw // 2
                py = SCREEN_HEIGHT // 2 - ph // 2
                panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
                panel.fill((20, 25, 30, 240))
                self.screen.blit(panel, (px, py))
                pygame.draw.rect(self.screen, (255, 215, 0), (px, py, pw, ph), 3, border_radius=12)

                # 3. Vẽ text kết quả
                font_result = get_cached_font('impact', 50)
                font_score = get_cached_font('Arial', 24, bold=True)
                
                # Màu chữ tiêu đề tùy theo ai thắng
                title_col = (255, 230, 80) if "1" in match_result else (200, 150, 255) if "2" in match_result else (200, 200, 200)
                
                res_txt = font_result.render(match_result, True, title_col)
                self.screen.blit(res_txt, res_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 50)))

                p1_txt = font_score.render(f"P1 Score: {p1.score:05d}", True, (255, 230, 80))
                self.screen.blit(p1_txt, p1_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 110)))

                p2_txt = font_score.render(f"P2 Score: {p2.score:05d}", True, (200, 150, 255))
                self.screen.blit(p2_txt, p2_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 150)))
            # ==========================================
            
            # Hiển thị hint điều khiển
            hint = font_hint.render('P1: W=Jump, S=Duck  |  P2: Up=Jump, Down=Duck  |  R=Retry  |  ESC=Menu', True, (220, 220, 220))
            self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 30)))

            pygame.display.flip()
            self.clock.tick(120)  # PVP mode chạy 120 FPS mượt hơn
    def _draw_god_result(self):
        # 1. Phủ màn hình màu vàng nhạt bán trong suốt cho sang trọng
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 215, 0, 100)) 
        self.screen.blit(overlay, (0, 0))

        # 2. Vẽ bảng thông báo
        pw, ph = 500, 250
        px, py = SCREEN_WIDTH // 2 - pw // 2, SCREEN_HEIGHT // 2 - ph // 2
        pygame.draw.rect(self.screen, (20, 20, 20), (px, py, pw, ph), border_radius=15)
        pygame.draw.rect(self.screen, (255, 215, 0), (px, py, pw, ph), 4, border_radius=15)

        # Thử đổi sang "tahoma" hoặc "segoe ui"
        font_god = pygame.font.SysFont("tahoma", 45, bold=True)
        txt_god = font_god.render("BẠN CHÍNH LÀ GOD", True, (245, 205, 0))
        self.screen.blit(txt_god, txt_god.get_rect(center=(SCREEN_WIDTH // 2, py + 70)))

        font_text = pygame.font.SysFont("tahoma", 24)
        
        # Nếu font tahoma vẫn lỗi, hãy sửa text thành: "Diem cua ban:"
        txt_score = font_text.render(f"Điểm của bạn: {self.score}", True, (255, 255, 255))
        self.screen.blit(txt_score, txt_score.get_rect(center=(SCREEN_WIDTH // 2, py + 140)))

        # Tương tự: "Nhan R de choi lai | ESC de thoat"
        txt_hint = font_text.render("Nhấn R để chơi lại | ESC để thoát", True, (200, 200, 200))
        self.screen.blit(txt_hint, txt_hint.get_rect(center=(SCREEN_WIDTH // 2, py + 200)))