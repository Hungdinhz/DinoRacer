"""
Class Chướng ngại vật - Cactus (xương rồng), Bird (chim)
Bird dùng sprite sheet ai_dino với animation vỗ cánh.
Cactus dùng tile sprite hoặc fallback vẽ tay.
"""
import pygame
import random
from src.assets_loader import get_sheet, load_image
from config.settings import (
    GROUND_Y,
    CACTUS_WIDTH, CACTUS_HEIGHT_SMALL, CACTUS_HEIGHT_LARGE, CACTUS_COLOR,
    BIRD_WIDTH, BIRD_HEIGHT, BIRD_COLOR,
)

# Số frame bird animation (ai_dino/move.png = 6 frames, idle.png = 3 frames)
_BIRD_ANIM_FRAMES = {"move": 6, "idle": 3}
_BIRD_ANIM_SPEED  = 6   # game-frames mỗi sprite-frame

_cactus_cache = {}


def _get_cactus_sprite(w, h):
    key = (w, h)
    if key not in _cactus_cache:
        img = load_image("tiles/Tile_02.png", (w, h))
        if img is None:
            img = load_image("tiles/Tile_03.png", (w, h))
        _cactus_cache[key] = img
    return _cactus_cache[key]


class Obstacle:
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


class Bird(Obstacle):
    """Chim dùng sprite sheet ai_dino/move.png để tạo animation vỗ cánh."""
    HEIGHTS = [GROUND_Y - 130, GROUND_Y - 85, GROUND_Y - 50]

    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.width = BIRD_WIDTH
        self.height = BIRD_HEIGHT
        self.y = random.choice(self.HEIGHTS)
        self.anim_frame = 0
        self.anim_timer = 0
        self._anim = "move"   # dùng move.png làm animation chính

    def update(self):
        super().update()
        self.anim_timer += 1
        if self.anim_timer >= _BIRD_ANIM_SPEED:
            self.anim_timer = 0
            num = _BIRD_ANIM_FRAMES.get(self._anim, 6)
            self.anim_frame = (self.anim_frame + 1) % num

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, screen):
        rect = self.get_rect()
        # Bird vẽ thủ công (fallback) vì không có sprite chim riêng
        # Không dùng ai_dino vì sẽ bị nhầm với khủng long AI
        pygame.draw.ellipse(screen, BIRD_COLOR,
                            (self.x + 5, self.y + 8, self.width - 10, self.height - 12))
        wing_y = self.y if self.anim_frame % 2 == 0 else self.y + self.height - 10
        pygame.draw.ellipse(screen, (80, 80, 180), (self.x, wing_y, self.width, 12))
        pygame.draw.circle(screen, (255, 255, 255),
                           (self.x + self.width - 12, self.y + 12), 5)
        pygame.draw.circle(screen, (0, 0, 0),
                           (self.x + self.width - 11, self.y + 12), 2)


def create_obstacle(x, speed):
    if random.random() < 0.7:
        return Cactus(x, speed)
    return Bird(x, speed)
