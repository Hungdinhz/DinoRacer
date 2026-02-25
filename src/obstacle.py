"""
Class Chướng ngại vật - Cactus (xương rồng), Bird (chim)
"""
import pygame
import random
from src.assets_loader import get_sprite
from config.settings import (
    SCREEN_WIDTH, GROUND_Y,
    CACTUS_WIDTH, CACTUS_HEIGHT_SMALL, CACTUS_HEIGHT_LARGE, CACTUS_COLOR,
    BIRD_WIDTH, BIRD_HEIGHT, BIRD_COLOR,
    OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX
)


class Obstacle:
    """Base class cho chướng ngại vật"""
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
    """Xương rồng - có thể cao hoặc thấp"""
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
        sprite = get_sprite("cactus", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            pygame.draw.rect(screen, CACTUS_COLOR, rect)
            for i in range(3):
                pygame.draw.line(screen, (0, 100, 0),
                                 (self.x + 5 + i * 12, self.y),
                                 (self.x + 5 + i * 12, self.y + 20), 2)


class Bird(Obstacle):
    """Chim - bay ở độ cao ngẫu nhiên"""
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.width = BIRD_WIDTH
        self.height = BIRD_HEIGHT
        # Chim bay ở độ cao 250-350 (trên mặt đất)
        self.y = random.randint(250, 350)
        self.anim_offset = 0

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

    def draw(self, screen):
        rect = self.get_rect()
        sprite = get_sprite("bird", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            pygame.draw.ellipse(screen, BIRD_COLOR, rect)
            pygame.draw.circle(screen, (255, 255, 255), (self.x + 35, self.y + 15), 5)
            pygame.draw.circle(screen, (0, 0, 0), (self.x + 36, self.y + 15), 2)


def create_obstacle(x, speed):
    """Tạo chướng ngại vật ngẫu nhiên"""
    if random.random() < 0.7:
        return Cactus(x, speed)
    return Bird(x, speed)
