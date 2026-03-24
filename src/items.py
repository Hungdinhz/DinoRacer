
import pygame
import random

from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y,
    COIN_WIDTH, COIN_HEIGHT, ITEM_WIDTH, ITEM_HEIGHT
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

class Shield(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.y = GROUND_Y - ITEM_WIDTH - 20  # Đặt shield trên mặt đất, cách một khoảng nhỏ
        self.width = ITEM_WIDTH
        self.height = ITEM_HEIGHT
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        pygame.draw.circle(screen, (0, 191, 255), rect.center, self.width // 2)
        sprite = get_sprite("shield", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            # Nếu chưa có ảnh shield.png trong assets, vẽ tạm một hình tròn màu Xanh dương
            pygame.draw.circle(screen, (0, 191, 255), (self.x + self.width//2, self.y + self.height//2), self.width//2)
            # Viết chữ S ở giữa cho giống khiên
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("S", True, (25, 25, 112))
            text_rect = text.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
            screen.blit(text, text_rect)

class SpeedItem(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.y = GROUND_Y - ITEM_WIDTH - 20  # Đặt speed item trên mặt đất, cách một khoảng nhỏ
        self.width = ITEM_WIDTH
        self.height = ITEM_HEIGHT
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        pygame.draw.circle(screen, (255, 69, 0), rect.center, self.width // 2)
        sprite = get_sprite("speed", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            # Nếu chưa có ảnh speed.png trong assets, vẽ tạm một hình tròn màu Đỏ cam
            pygame.draw.circle(screen, (255, 69, 0), (self.x + self.width//2, self.y + self.height//2), self.width//2)
            # Viết chữ F ở giữa cho giống biểu tượng tốc độ
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("F", True, (178, 34, 34))
            text_rect = text.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
            screen.blit(text, text_rect)

class X2Item(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.y = GROUND_Y - ITEM_WIDTH - 20  # Đặt x2 item trên mặt đất, cách một khoảng nhỏ
        self.width = ITEM_WIDTH
        self.height = ITEM_HEIGHT
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        pygame.draw.circle(screen, (138, 43, 226), rect.center, self.width // 2)
        sprite = get_sprite("x2", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            # Nếu chưa có ảnh x2.png trong assets, vẽ tạm một hình tròn màu Tím
            pygame.draw.circle(screen, (138, 43, 226), (self.x + self.width//2, self.y + self.height//2), self.width//2)
            # Viết chữ x2 ở giữa cho giống biểu tượng nhân đôi
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("x2", True, (75, 0, 130))
            text_rect = text.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
            screen.blit(text, text_rect)

class SwordItem(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.y = GROUND_Y - ITEM_WIDTH - 20  # Đặt sword item trên mặt đất, cách một khoảng nhỏ
        self.width = ITEM_WIDTH
        self.height = ITEM_HEIGHT
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        pygame.draw.circle(screen, (192, 192, 192), rect.center, self.width // 2)
        sprite = get_sprite("sword", (self.width, self.height))
        if sprite:
            screen.blit(sprite, rect)
        else:
            # Nếu chưa có ảnh sword.png trong assets, vẽ tạm một hình tròn màu Bạc
            pygame.draw.circle(screen, (192, 192, 192), (self.x + self.width//2, self.y + self.height//2), self.width//2)
            # Viết chữ K ở giữa cho giống biểu tượng kiếm
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("K", True, (169, 169, 169))
            text_rect = text.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
            screen.blit(text, text_rect)

    

    








