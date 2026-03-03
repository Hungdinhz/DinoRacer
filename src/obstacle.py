"""
Class Chướng ngại vật - Cactus (xương rồng), Bird (chim)
Bird dùng sprite sheet ai_dino với animation vỗ cánh.
Cactus dùng tile sprite hoặc fallback vẽ tay.
"""
import pygame
import random
from src.assets_loader import get_sheet, load_image, play_sound
from config.settings import (
    GROUND_Y,
    CACTUS_WIDTH, CACTUS_HEIGHT_SMALL, CACTUS_HEIGHT_LARGE, CACTUS_COLOR,
    BIRD_WIDTH, BIRD_HEIGHT, BIRD_COLOR,
)

# Số frame bird animation (ai_dino/move.png = 6 frames, idle.png = 3 frames)
_BIRD_ANIM_FRAMES = {"move": 6, "idle": 3}
_BIRD_ANIM_SPEED  = 6   # game-frames mỗi sprite-frame

# Enhanced cactus cache với LRU
_cactus_cache = {}
_CACTUS_CACHE_MAX_SIZE = 10


def _get_cactus_sprite(w, h):
    key = (w, h)
    if key not in _cactus_cache:
        # Xóa cache cũ nếu quá lớn
        if len(_cactus_cache) >= _CACTUS_CACHE_MAX_SIZE:
            _cactus_cache.clear()
        img = load_image("willow/3.png", (w, h))
        if img is None:
            img = load_image("willows/1.png", (w, h))
        _cactus_cache[key] = img
    return _cactus_cache[key]


class Obstacle:
    """Base class với __slots__ để tối ưu memory"""
    __slots__ = ('x', 'speed', 'passed')

    def __init__(self, x, speed):
        self.x = x
        self.speed = speed
        self.passed = False

    def update(self):
        self.x -= self.speed

    def draw(self, screen):
        raise NotImplementedError

    def get_rect(self):
        raise NotImplementedError

    def is_off_screen(self):
        return self.x < -100


class Cactus(Obstacle):
    """Cactus với __slots__"""
    __slots__ = ('is_large', 'width', 'height', 'y')

    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.is_large = random.choice([True, False])
        self.width = CACTUS_WIDTH
        self.height = CACTUS_HEIGHT_LARGE if self.is_large else CACTUS_HEIGHT_SMALL
        self.y = GROUND_Y - self.height

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, screen):
        rect = self.get_rect()
        sprite = _get_cactus_sprite(self.width, self.height)
        if sprite:
            screen.blit(sprite, rect)
        else:
            # Fallback vẽ tay xương rồng
            mid = self.x + self.width // 2
            pygame.draw.rect(screen, (0, 120, 0), (mid - 5, self.y, 10, self.height))
            arm_y = self.y + self.height // 3
            pygame.draw.rect(screen, (0, 120, 0), (self.x, arm_y, mid - self.x, 7))
            pygame.draw.rect(screen, (0, 120, 0), (self.x, arm_y - 12, 7, 18))
            pygame.draw.rect(screen, (0, 120, 0), (mid, arm_y + 10, self.x + self.width - mid, 7))
            pygame.draw.rect(screen, (0, 120, 0), (self.x + self.width - 7, arm_y - 2, 7, 18))

# Cache cho animation của chim bay, dùng tuple (width, height) làm key
_bird_cache = {}

def _get_bird_frames(w, h):
    """Load 7 frame ảnh của chim theo kích thước yêu cầu."""
    key = (w, h)
    if key not in _bird_cache:
        frames = []
        for i in range(1, 8):
            img = load_image(f"bird/{i}.png", (w, h))
            if img:
                frames.append(img)
        _bird_cache[key] = frames
    return _bird_cache[key] 
class Bird(Obstacle):
    """Chim với animation đập cánh dùng hình ảnh thực từ thư mục"""
    __slots__ = ('width', 'height', 'y', 'anim_frame', 'anim_timer')

    def __init__(self, x, speed):
        super().__init__(x, speed)
        
        # --- TĂNG KÍCH THƯỚC Ở ĐÂY ---
        scale_factor = 1.8  # Tăng lên 1.8 lần (bạn có thể đổi thành 2.0 hoặc 1.5 tùy ý)
        self.width = int(BIRD_WIDTH * scale_factor)
        self.height = int(BIRD_HEIGHT * scale_factor)
        
        # Điều chỉnh lại độ cao bay để chim to không bị quệt bụng xuống đất
        self.y = random.choice([GROUND_Y - 140, GROUND_Y - 95, GROUND_Y - 60])
        self.anim_frame = 0
        self.anim_timer = 0
        play_sound("bird")

    def get_rect(self):
        # Lấy rect tổng thể bao quanh bức ảnh (cái ô màu đỏ khổng lồ bạn đang thấy)
        collide_rect = pygame.Rect(self.x, self.y, self.width, self.height)

        # Bây giờ, chúng ta sẽ "gọt" nó cho nhỏ lại.
        # Bạn có thể tăng giảm hai con số này để cái khung khớp nhất với con chim.
        # Chúng ta sẽ thu nhỏ 60 pixel chiều ngang (mỗi bên 30)
        # Và thu nhỏ 50 pixel chiều dọc (mỗi bên 25)
        trimmed_rect = collide_rect.inflate(-60, -50)
        
        return trimmed_rect

    def draw(self, screen):
        rect = self.get_rect()
        frames = _get_bird_frames(self.width, self.height)
        
        # --- LOGIC ANIMATION CHUYỂN VÀO ĐÂY ---
        # Do game_manager không gọi hàm update(), ta ép nó chạy ở đây
        self.anim_timer += 1
        if frames and self.anim_timer >= _BIRD_ANIM_SPEED:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % len(frames)
        
        # Ưu tiên vẽ ảnh thật
        if frames and self.anim_frame < len(frames):
            # Vẽ ảnh tại tọa độ thực của chim (không tính margin của hitbox)
            screen.blit(frames[self.anim_frame], (self.x, self.y))
        else:
            # Fallback (Vẽ tay) nếu lỗi ảnh
            pygame.draw.ellipse(screen, BIRD_COLOR,
                                (self.x, self.y, self.width, self.height))
            
def create_obstacle(x, speed):
    if random.random() < 0.7:
        return Cactus(x, speed)
    return Bird(x, speed)
