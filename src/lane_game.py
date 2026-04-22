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
    INITIAL_SCORE, COLLISION_MARGIN, LANE_HEIGHT,
    MAX_SPEED_TIME, MAX_X2_TIME, PLUS_COUNT_SWORD,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.assets_loader import play_sound, load_image
from src.data_collector import get_collector
from src.items import Coin, Shield, SpeedItem, X2Item, SwordItem
from src.utils import get_cached_font
from src.ui import UILayer

# Chiều cao mỗi lane
LANE_H = LANE_HEIGHT
LANE_W = SCREEN_WIDTH
GROUND_Y_LANE = LANE_H - 55   # mặt đất trong lane
LOGIC_Y = GROUND_Y_LANE + 20  # Tọa độ vật lý: cộng 20px để hạ thấp toàn bộ vật thể
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
        _tile_cache[size] = load_image("tiles/Tile_02.png", size)
    return _tile_cache[size]


class LaneCloud:
    """Cloud với __slots__ để tối ưu memory"""
    __slots__ = ('x', 'y', 'speed', 'w', 'h')

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
                 label_color=(255, 230, 80), collect_data=False, player_type="human",
                 sword_key="T"):
        self.dino_folder = dino_folder
        self.label = label
        self.label_color = label_color
        self.collect_data = collect_data
        self.player_type = player_type
        self.sword_key = sword_key

        self.surface = pygame.Surface((LANE_W, LANE_H))

        self.ui = UILayer(self.surface)

        # Sử dụng cached fonts thay vì tạo mới
        self.font_hud   = get_cached_font("Arial", 20, bold=True)
        self.font_label = get_cached_font("Arial", 18, bold=True)
        self.font_go    = get_cached_font(
            "impact" if "impact" in pygame.font.get_fonts() else "arial",
            42, bold=True)
        self.font_small = get_cached_font("Arial", 16)

        self.clouds = [LaneCloud(random.randint(0, LANE_W)) for _ in range(4)]
        self.ground_offset = 0
        self.bg_offset = 0
        self.bg_index = 1

        self.reset()

    def reset(self):
        self.dino = Dino(x=80, folder=self.dino_folder)
        from config.settings import DINO_HEIGHT
        # Set ground_y BEFORE setting y position
        self.dino.ground_y = GROUND_Y_LANE
        self.dino.ground_y = LOGIC_Y
        self.dino.y = LOGIC_Y - DINO_HEIGHT
        # Debug: Invalidate cached rect
        self.dino._cached_rect = None

        self.obstacles = []
        self.items = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        self.last_item_x = 0
        self.last_coin_x = 0
        self.next_spawn_distance = 0
        self.next_spawn_items_score = 0
        self.speed_buff_timer = 0
        self.x2_buff_timer = 0
        self.shield_buff_timer = 0
        self.game_over = False
        self.ground_offset = 0

        # Notification system
        self.notifications = []
        self.bg_offset = 0
        self.bg_index = 1
        self.go_flash_timer = 0
        self._data_saved = False  # Reset data saved flag

        self.last_action = (0, 0)
        self.frame_count = 0

    def _update_dino_physics(self):
        import config.settings as game_settings
        d = self.dino
        # Sử dụng d.height thay vì DINO_HEIGHT cố định
        ground = d.ground_y - d.height

        # Sử dụng các biến physics từ settings
        from src.dino import GRAVITY, JUMP_HOLD_GRAVITY, JUMP_MIN_VELOCITY

        if d.is_jumping:
            # Sử dụng gravity nhẹ hơn khi giữ phím
            current_gravity = GRAVITY
            d.vel_y += current_gravity
            d.y += d.vel_y
            # Sửa: dùng >= thay vì > để đảm bảo landing đúng
            if d.y >= ground:
                d.y = ground
                d.vel_y = 0
                d.is_jumping = False
                d.is_on_ground = True
                d._coyote_timer = 8  # Reset coyote time
        else:
            # Trên ground - đảm bảo y đúng vị trí
            d.is_on_ground = True
            if d.y < ground:
                d.y = ground

        # Update animation
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
        target_distance = getattr(self, 'next_spawn_distance', 600)

        last_coin_x = max([i.x for i in self.items]) if self.items else 0
        dist_to_last_coin = (LANE_W + 50) - last_coin_x
        last_special_x = max([i.x for i in self.items if not isinstance(i, Coin)], default=0)
        dist_to_last_item = float('inf') if last_special_x == 0 else (LANE_W + 50) - last_special_x

        if (LANE_W - self.last_obstacle_x) > target_distance and dist_to_last_coin > 150 and dist_to_last_item > 150:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(LANE_W + 50, speed)
            from src.obstacle import Cactus, Bird
            if isinstance(obs, Cactus):
                # Xương rồng lún xuống chạm mặt cỏ
                obs.y = LOGIC_Y - obs.height
                
            elif isinstance(obs, Bird):
                # CÁCH A: Trả chim về lại đúng độ cao cũ (Dùng GROUND_Y_LANE)
                from config.settings import GROUND_Y
                ratio = GROUND_Y_LANE / GROUND_Y 
                obs.y = int(obs.y * ratio)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x
            self.next_spawn_distance = random.randint(500, 1000)

    def check_collision(self):
        from config.settings import DINO_HEIGHT, DUCK_HEIGHT_RATIO, COLLISION_MARGIN
        d = self.dino
        h = d.height
        if d.is_ducking:
            h = int(d.height * DUCK_HEIGHT_RATIO)
        dino_rect = pygame.Rect(d.x, d.y + (d.height - h), d.width, h)
        # Sử dụng margin từ settings
        margin = COLLISION_MARGIN
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)
        for obs in self.obstacles:
            obs_rect = obs.get_rect()
            if shrunk.colliderect(obs_rect.inflate(-margin, -margin)):
                dino_mask, dx, dy = self.dino.get_mask_info()
                obs_mask, ox, oy = obs.get_mask_info()
                
                is_collide = True
                if dino_mask and obs_mask:
                    offset = (int(ox - dx), int(oy - dy))
                    if not dino_mask.overlap(obs_mask, offset):
                        is_collide = False
                
                if is_collide:
                    if self.dino.has_shield:
                        self.dino.has_shield = False
                        self.shield_buff_timer = 0
                        self.obstacles.remove(obs)
                        play_sound("shield_broken")
                        return False
                    return True
        return False

    def sword_slash(self):
        """Chém chướng ngại vật phía trước mặt dino (tầm 150px)."""
        if self.dino.sword_charges <= 0:
            return

        from src.obstacle import Bird

        self.dino.start_sword_slash()
        dino_right = self.dino.x + self.dino.width
        dino_y = self.dino.y
        for obs in self.obstacles:
            if isinstance(obs, Bird) and (dino_y - obs.y) > 50:
                continue
            if 0 < (obs.x - dino_right) < 150:
                self.obstacles.remove(obs)
                self.dino.sword_charges -= 1
                self.add_notification("SLASH!", (255, 80, 80))
                play_sound("sword_slash")
                break

    def add_notification(self, text, color=(255, 255, 255), duration=90):
        """Thêm thông báo hiệu ứng item."""
        self.notifications.append({
            "text": text,
            "color": color,
            "timer": duration,
            "max_timer": duration,
            "y_offset": 0.0,
        })

    def update_notifications(self):
        """Cập nhật notification: giảm timer, xóa hết."""
        alive = []
        for n in self.notifications:
            n["timer"] -= 1
            n["y_offset"] -= 1.0
            if n["timer"] > 0:
                alive.append(n)
        self.notifications = alive

    def draw_notifications(self, surf):
        """Vẽ notifications lên surface."""
        for i, n in enumerate(self.notifications):
            alpha = int(255 * (n["timer"] / n["max_timer"]))
            if alpha <= 0:
                continue
            text_surf = self.font_small.render(n["text"], True, n["color"])
            text_surf.set_alpha(alpha)
            y = LANE_H // 2 - 60 + i * 28 + int(n["y_offset"])
            x = LANE_W // 2 - text_surf.get_width() // 2
            surf.blit(text_surf, (x, y))

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
            self.update_notifications()
            # Chỉ save data một lần khi mới game over
            if self.collect_data and hasattr(self, '_data_saved') and not self._data_saved:
                if len(get_collector().current_session_data) > 0:
                    get_collector().save_session_data()
                self._data_saved = True
            return

        actual_action = (0, 0)

        # Handle AI action
        if action is not None:
            jump, duck = action[0], action[1] if len(action) > 1 else (0, 0)
            if jump > 0.5:
                self.dino.jump()
                actual_action = (1, 0)
            self.dino.set_duck(duck > 0.5)
            if duck > 0.5 and not self.dino.is_jumping:
                actual_action = (actual_action[0], 1)
        # Handle player action (from keyboard)
        elif player_action is not None:
            jump, duck = player_action
            if jump > 0.5:
                self.dino.jump_press()
                actual_action = (1, 0)
            self.dino.duck(duck > 0.5)
            if duck > 0.5 and not self.dino.is_jumping:
                actual_action = (actual_action[0], 1)

        # Update dino physics using proper update method
        self.dino.update(jump_held=False)

        if self.speed_buff_timer > 0:
            self.speed_buff_timer -= 1
        if self.x2_buff_timer > 0:
            self.x2_buff_timer -= 1
        if getattr(self, 'shield_buff_timer', 0) > 0:
            self.shield_buff_timer -= 1
            if self.shield_buff_timer == 0:
                self.dino.has_shield = False

        current_speed_multiplier = 1.1 if self.speed_buff_timer > 0 else 1.0

        self._spawn_obstacle()

        self.ground_offset = (self.ground_offset + self.game_speed * current_speed_multiplier) % 64
        self.bg_offset = (self.bg_offset + self.game_speed * 0.03 * current_speed_multiplier) % LANE_W

        prev = self.score
        for obs in self.obstacles:
            obs.x -= obs.speed * current_speed_multiplier
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
        self.bg_index = min(1 + self.score // 200, 5)

        # 1. Spawn coins if enough space
        start_coin_x = LANE_W + 50
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
                if len(self.items) < 5:
                    coin_x = start_coin_x + i * 50
                    coin_speed = self.game_speed
                    coin = Coin(coin_x, coin_speed)
                    coin.y = LOGIC_Y - coin.height - 20
                    self.items.append(coin)

        # 2. Update items and collect
        dino_rect = self.get_dino_rect()
        for item in self.items:
            old_x = item.x
            item.update()
            item.x = old_x - item.speed * current_speed_multiplier
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
                    self.add_notification("SHIELD!", (0, 191, 255))
                elif isinstance(item, SpeedItem):
                    self.speed_buff_timer = MAX_SPEED_TIME
                    self.add_notification("SPEED UP!", (0, 255, 255))
                elif isinstance(item, X2Item):
                    self.x2_buff_timer = MAX_X2_TIME
                    self.add_notification("x2 GOLD!", (255, 215, 0))
                elif isinstance(item, SwordItem):
                    self.dino.sword_charges += PLUS_COUNT_SWORD
                    self.add_notification(f"+{PLUS_COUNT_SWORD} SWORD!", (255, 100, 100))
                else:
                    multiplier = 2 if self.x2_buff_timer > 0 else 1
                    bonus = getattr(item, 'bonus_points', 10) * multiplier
                    self.score += bonus
                    self.add_notification(f"+{bonus}", (255, 230, 80), duration=45)


        self.items = [i for i in self.items if not i.is_off_screen() and not i.is_collected]
        self.last_item_x = max([i.x for i in self.items if not isinstance(i, Coin)], default=0)

        if self.score > self.next_spawn_items_score and self.score > 0:
            item_x = LANE_W + 50
            dist_to_last_obs = item_x - getattr(self, 'last_obstacle_x', 0)
            if dist_to_last_obs > 200:
                item_type = random.choice(['shield', 'speed', 'x2', 'sword'])
                if item_type == 'shield':
                    item = Shield(item_x, self.game_speed)
                elif item_type == 'speed':
                    item = SpeedItem(item_x, self.game_speed)
                elif item_type == 'x2':
                    item = X2Item(item_x, self.game_speed)
                else:
                    item = SwordItem(item_x, self.game_speed)
                item.y = LOGIC_Y - item.height
                self.items.append(item)
                self.last_item_x = item_x
                self.next_spawn_items_score += 50

        for c in self.clouds:
            c.update()

        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
            if self.collect_data:
                get_collector().save_session_data()

        self.update_notifications()
        
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

        fog = pygame.Surface((LANE_W, LANE_H), pygame.SRCALPHA)
        # Số cuối cùng là độ mờ (0-255). Càng cao thì BG càng bị che mờ!
        fog.fill((200, 220, 240, 150)) 
        surf.blit(fog, (0, 0))
        
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

        for item in self.items:
            item.draw(surf)

        self.draw_notifications(surf)

        from config.settings import MAX_SHIELD_TIME
        self.ui.draw_buffs(
            self.speed_buff_timer, MAX_SPEED_TIME,
            self.x2_buff_timer, MAX_X2_TIME,
            getattr(self, 'shield_buff_timer', 0), MAX_SHIELD_TIME,
            self.dino.sword_charges,
            self.sword_key,
        )

        lbl = self.font_label.render(self.label, True, self.label_color)
        surf.blit(lbl, (8, 6))

        score_txt = self.font_hud.render(f"SCORE {self.score:05d}", True, (255, 255, 255))
        surf.blit(score_txt, (LANE_W // 2 - score_txt.get_width() // 2, 6))

        spd_txt = self.font_small.render(f"SPD {self.game_speed:.1f}", True, (180, 255, 180))
        surf.blit(spd_txt, (LANE_W - spd_txt.get_width() - 8, 6))

        if self.collect_data:
            data_icon = self.font_small.render("●", True, (0, 255, 0))
            surf.blit(data_icon, (LANE_W - 25, 28))

        if self.game_over:
            # Tạo bề mặt phủ đen
            dark_overlay = pygame.Surface((LANE_W, LANE_H), pygame.SRCALPHA)
            
            # Đặt độ tối CỐ ĐỊNH ở mức 150 (không dùng go_flash_timer nữa)
            # Bạn có thể tăng lên 180 hoặc 200 nếu muốn tối đen hơn
            dark_overlay.fill((0, 0, 0, 150))
            
            surf.blit(dark_overlay, (0, 0))
        
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

            go = self.font_go.render("GAME OVER", True, (255, 215, 0))  # Yellow/Gold
            surf.blit(go, go.get_rect(center=(LANE_W // 2, py + 40)))

            score_txt = self.font_label.render(f"Score: {self.score:05d}", True, (255, 230, 80))
            surf.blit(score_txt, score_txt.get_rect(center=(LANE_W // 2, py + 80)))

            hint = self.font_small.render("R - Retry  |  ESC - Menu", True, (200, 200, 200))
            surf.blit(hint, hint.get_rect(center=(LANE_W // 2, py + 115)))
