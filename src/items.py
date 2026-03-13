
import pygame
import random

from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y,
    COIN_WIDTH, COIN_HEIGHT
)

from src.assets_loader import get_sprite



class Item:
    def __init__(self, x, speed):
        self.x = x
        self.y = 0
        self.speed = speed   
        self.width = 0
        self.height = 0
        self.is_collected = False

    def update(self):
        self.x -= self.speed
    
    def draw(self, screen):
        raise NotImplementedError
    
    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
    
    def is_off_screen(self):
        return self.x < self.width * -1
    
class Coin(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.y = GROUND_Y - COIN_HEIGHT - 20  # Đặt coin trên mặt đất, cách một khoảng nhỏ
        self.width = COIN_WIDTH
        self.height = COIN_HEIGHT
        self.bonus_points = 5

    def draw(self, screen):
        rect = self.get_rect()
        pygame.draw.circle(screen, (255, 223, 0), rect.center, self.width // 2)
        sprite = get_sprite("coin", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            # Nếu chưa có ảnh coin.png trong assets, vẽ tạm một hình tròn màu Vàng kim
            pygame.draw.circle(screen, (255, 215, 0), (self.x + self.width//2, self.y + self.height//2), self.width//2)
            # Viết chữ $ ở giữa cho giống đồng xu
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("$", True, (184, 134, 11))
            text_rect = text.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
            screen.blit(text, text_rect)


    

    








