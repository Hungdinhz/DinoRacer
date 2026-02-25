"""
Class Dino - Xử lý nhảy, cúi, vẽ khủng long
"""
import pygame
from config.settings import (
    DINO_X, DINO_WIDTH, DINO_HEIGHT, DINO_COLOR,
    GROUND_Y, GRAVITY, JUMP_VELOCITY, DUCK_HEIGHT_RATIO
)
from src.assets_loader import get_sprite, play_sound


class Dino:
    def __init__(self, x=DINO_X):
        self.x = x
        self.y = GROUND_Y - DINO_HEIGHT
        self.width = DINO_WIDTH
        self.height = DINO_HEIGHT
        self.vel_y = 0
        self.is_jumping = False
        self.is_ducking = False
        self.color = DINO_COLOR

    def jump(self):
        """Nhảy lên nếu đang đứng trên mặt đất"""
        if not self.is_jumping and not self.is_ducking:
            self.vel_y = JUMP_VELOCITY
            self.is_jumping = True
            play_sound("jump")

    def duck(self, is_ducking: bool):
        """Cúi xuống hoặc đứng dậy"""
        if not self.is_jumping:
            self.is_ducking = is_ducking

    def update(self):
        """Cập nhật vị trí theo trọng lực"""
        if self.is_jumping:
            self.vel_y += GRAVITY
            self.y += self.vel_y

            ground_level = GROUND_Y - self.height
            if self.y >= ground_level:
                self.y = ground_level
                self.vel_y = 0
                self.is_jumping = False

    def get_rect(self):
        """Trả về rect để kiểm tra va chạm"""
        h = self.height
        if self.is_ducking:
            h = int(self.height * DUCK_HEIGHT_RATIO)
        return pygame.Rect(self.x, self.y + (self.height - h), self.width, h)

    def draw(self, screen):
        """Vẽ khủng long lên màn hình (sprite hoặc fallback vẽ tay)"""
        rect = self.get_rect()
        sprite = get_sprite("dino_duck" if self.is_ducking else "dino", (self.width, rect.height))
        if sprite:
            screen.blit(sprite, (rect.x, rect.y))
        else:
            pygame.draw.rect(screen, self.color, rect)
            eye_x = self.x + self.width - 12
            eye_y = self.y + 12 if not self.is_ducking else self.y + 8
            pygame.draw.circle(screen, (255, 255, 255), (eye_x, eye_y), 4)
            pygame.draw.circle(screen, (0, 0, 0), (eye_x + 1, eye_y), 2)
