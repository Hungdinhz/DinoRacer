
import pygame
import random
from src.assets_loader import get_sprite, load_image
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, GROUND_Y,
    COIN_WIDTH, COIN_HEIGHT, ITEM_WIDTH, ITEM_HEIGHT,
    ITSPEED_WIDTH, ITSPEED_HEIGHT, X2COIN_WIDTH, X2COIN_HEIGHT
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
        self.y = GROUND_Y - ITEM_WIDTH - 10
        self.width = ITEM_WIDTH
        self.height = ITEM_HEIGHT
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        
        # SỬ DỤNG load_image và gọi đúng đường dẫn "items/Shield.png"
        sprite = load_image("items/Shield.png", (self.width, self.height))
        
        if sprite:
            # NẾU TÌM THẤY ẢNH: In ảnh ra
            screen.blit(sprite, rect)
        else:
            # NẾU KHÔNG TÌM THẤY ẢNH: Báo lỗi ra terminal và vẽ hình tròn
            print("❌ LỖI: Vẫn không load được ảnh items/Shield.png")
            pygame.draw.circle(screen, (0, 191, 255), rect.center, self.width // 2)
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("S", True, (25, 25, 112))
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

class SpeedItem(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        # Gán kích thước trước
        self.width = ITSPEED_WIDTH
        self.height = ITSPEED_HEIGHT
        
        # Cho chạm đất
        self.y = GROUND_Y - self.height 
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        
        # Gọi hàm lấy ảnh giày bay
        sprite = load_image("items/Speed.png", (self.width, self.height))
        
        if sprite:
            # NẾU CÓ ẢNH: CHỈ in ảnh ra, tuyệt đối không vẽ thêm hình tròn
            screen.blit(sprite, rect)
        else:
            # FALLBACK: Chỉ vẽ hình tròn cam khi bị mất ảnh
            pygame.draw.circle(screen, (255, 69, 0), rect.center, self.width // 2)
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("F", True, (178, 34, 34))
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

class X2Item(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        # 1. Gán kích thước trước
        self.width = X2COIN_WIDTH
        self.height = X2COIN_HEIGHT
        
        # 2. Cho chạm đất (đổi công thức chuẩn để không bị bay lơ lửng)
        self.y = GROUND_Y - self.height
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        
        # 3. Lấy ảnh X2 (Hãy đảm bảo bạn có file x2.png trong thư mục items nhé)
        sprite = load_image("items/x2coin.png", (self.width, self.height))
        
        if sprite:
            # NẾU CÓ ẢNH: Chỉ in ảnh, tuyệt đối không vẽ bong bóng tím
            screen.blit(sprite, rect)
        else:
            # FALLBACK: Chỉ vẽ hình tròn tím khi chưa có ảnh
            pygame.draw.circle(screen, (138, 43, 226), rect.center, self.width // 2)
            font = pygame.font.SysFont('Arial', 20, bold=True)
            text = font.render("x2", True, (75, 0, 130))
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

class SwordItem(Item):
    def __init__(self, x, speed):
        super().__init__(x, speed)
        # 1. Gán kích thước trước
        self.width = X2COIN_WIDTH
        self.height = X2COIN_HEIGHT
        
        # 2. Cho chạm mặt đất chuẩn xác (bỏ -20 đi)
        self.y = GROUND_Y - self.height
        self.bonus_points = 10

    def draw(self, screen):
        rect = self.get_rect()
        
        # 3. Lấy ảnh Kiếm (Đảm bảo có file sword.png trong thư mục assets/images/items/)
        sprite = load_image("items/Sword.png", (self.width, self.height))
        
        if sprite:
            # NẾU CÓ ẢNH: Chỉ in ảnh kiếm ra, tuyệt đối không vẽ vòng tròn bạc phía sau
            screen.blit(sprite, rect)
        else:
            # FALLBACK: Chỉ vẽ vòng tròn bạc khi game không tìm thấy ảnh
            pygame.draw.circle(screen, (192, 192, 192), rect.center, self.width // 2)
            font = pygame.font.SysFont('Arial', 20, bold=True)
            # Mình đổi màu chữ K đậm hơn một chút (100,100,100) để dễ nhìn trên nền bạc
            text = font.render("K", True, (100, 100, 100)) 
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

    

    








