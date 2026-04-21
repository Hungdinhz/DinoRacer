
import pygame
import random
from src.assets_loader import (
    get_sheet, get_sprite, get_cached_font_item, get_item_sprite
)
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y,
    COIN_WIDTH, COIN_HEIGHT, ITEM_WIDTH, ITEM_HEIGHT,
    ITSPEED_WIDTH, ITSPEED_HEIGHT, X2COIN_WIDTH, X2COIN_HEIGHT
)


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
        self.y = GROUND_Y - COIN_HEIGHT - 20
        self.width = COIN_WIDTH
        self.height = COIN_HEIGHT
        self.bonus_points = 5
        self._font = get_cached_font_item('Arial', 20, bold=True)
        
        # --- THIẾT LẬP ANIMATION ---
        self.current_frame = 0
        self.animation_speed = 0.15
        
        # Dùng hàm get_sheet đã có sẵn trong assets_loader.py
        # Truyền đường dẫn tương đối 'items/Coin.png', số frame = 4
        self.frames = get_sheet('items/Coin.png', 4, self.width, self.height)

    def update(self):
        super().update()
        
        # Cập nhật animation nếu đã tải frames thành công
        if self.frames:
            self.current_frame += self.animation_speed
            if self.current_frame >= len(self.frames):
                self.current_frame = 0

    def draw(self, screen):
        if self.frames:
            # Ép kiểu current_frame về số nguyên (0, 1, 2, 3)
            image_to_draw = self.frames[int(self.current_frame)]
            screen.blit(image_to_draw, (self.x, self.y))
        else:
            # Fallback nếu đường dẫn ảnh vẫn sai
            center = (int(self.x + self.width // 2), int(self.y + self.height // 2))
            pygame.draw.circle(screen, (255, 215, 0), center, self.width // 2)
            text = self._font.render("$", True, (184, 134, 11))
            screen.blit(text, text.get_rect(center=center))

class Shield(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.y = GROUND_Y - ITEM_WIDTH - 10
        self.width = ITEM_WIDTH
        self.height = ITEM_HEIGHT
        self.bonus_points = 10
        self._font = get_cached_font_item('Arial', 20, bold=True)

    def draw(self, screen):
        sprite = get_item_sprite('shield')
        if sprite:
            screen.blit(sprite, (self.x, self.y))
        else:
            # Fallback
            center = (self.x + self.width // 2, self.y + self.height // 2)
            pygame.draw.circle(screen, (0, 191, 255), center, self.width // 2)
            text = self._font.render("S", True, (25, 25, 112))
            screen.blit(text, text.get_rect(center=center))


class SpeedItem(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.width = ITSPEED_WIDTH
        self.height = ITSPEED_HEIGHT
        self.y = GROUND_Y - self.height
        self.bonus_points = 10
        self._font = get_cached_font_item('Arial', 20, bold=True)

    def draw(self, screen):
        sprite = get_item_sprite('speed')
        if sprite:
            screen.blit(sprite, (self.x, self.y))
        else:
            center = (self.x + self.width // 2, self.y + self.height // 2)
            pygame.draw.circle(screen, (255, 69, 0), center, self.width // 2)
            text = self._font.render("F", True, (178, 34, 34))
            screen.blit(text, text.get_rect(center=center))


class X2Item(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.width = X2COIN_WIDTH
        self.height = X2COIN_HEIGHT
        self.y = GROUND_Y - self.height
        self.bonus_points = 10
        self._font = get_cached_font_item('Arial', 20, bold=True)

    def draw(self, screen):
        sprite = get_item_sprite('x2')
        if sprite:
            screen.blit(sprite, (self.x, self.y))
        else:
            center = (self.x + self.width // 2, self.y + self.height // 2)
            pygame.draw.circle(screen, (138, 43, 226), center, self.width // 2)
            text = self._font.render("x2", True, (75, 0, 130))
            screen.blit(text, text.get_rect(center=center))


class SwordItem(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.width = X2COIN_WIDTH
        self.height = X2COIN_HEIGHT
        self.y = GROUND_Y - self.height
        self.bonus_points = 10
        self._font = get_cached_font_item('Arial', 20, bold=True)

    def draw(self, screen):
        sprite = get_item_sprite('sword')
        if sprite:
            screen.blit(sprite, (self.x, self.y))
        else:
            center = (self.x + self.width // 2, self.y + self.height // 2)
            pygame.draw.circle(screen, (192, 192, 192), center, self.width // 2)
            text = self._font.render("K", True, (100, 100, 100))
            screen.blit(text, text.get_rect(center=center))
