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
# ==========================================
# CACHE CHO CHƯỚNG NGẠI VẬT DƯỚI ĐẤT
# ==========================================
_obstacle_cache = {}
_OBSTACLE_CACHE_MAX_SIZE = 20

def _get_obstacle_sprite(filename, w, h):
    """Load ảnh chướng ngại vật linh hoạt theo tên file"""
    key = (filename, w, h)
    if key not in _obstacle_cache:
        # Xóa cache cũ nếu quá lớn
        if len(_obstacle_cache) >= _OBSTACLE_CACHE_MAX_SIZE:
            _obstacle_cache.clear()
        
        # Load ảnh từ đường dẫn truyền vào
        img = load_image(filename, (w, h))
        _obstacle_cache[key] = img
        
    return _obstacle_cache[key]

# ==========================================
# CLASS CHƯỚNG NGẠI VẬT DƯỚI ĐẤT (Giữ tên Cactus để không hỏng code cũ)
# ==========================================
class Cactus(Obstacle):
    """Chướng ngại vật đa dạng (Cây, đá, bụi rậm...) với __slots__"""
    
    # Thêm 'image_path' vào __slots__ để lưu đường dẫn ảnh
    __slots__ = ('is_large', 'width', 'height', 'y', 'image_path')

    def __init__(self, x, speed):
        super().__init__(x, speed)
        self.is_large = random.choice([True, False])
        self.width = CACTUS_WIDTH
        self.height = CACTUS_HEIGHT_LARGE if self.is_large else CACTUS_HEIGHT_SMALL
        self.y = GROUND_Y - self.height
    # ==========================================
        # CHỈNH KÍCH THƯỚC TO HƠN Ở ĐÂY
        # ==========================================
        scale_factor = 1.5  # Phóng to gấp rưỡi (1.5). Bạn có thể đổi thành 1.8 hoặc 2.0 tùy ý
        base_width = CACTUS_WIDTH
        base_height = CACTUS_HEIGHT_LARGE if self.is_large else CACTUS_HEIGHT_SMALL
        
        # Ép kiểu int để kích thước không bị lẻ
        self.width = int(base_width * scale_factor)
        self.height = int(base_height * scale_factor)
        
        # Tính toán lại tọa độ y để gốc cây/đá vẫn nằm sát mặt đất
        self.y = GROUND_Y - self.height
        # --- DANH SÁCH ẢNH RANDOM ---
        # Bạn có thể THÊM hoặc XÓA tên các file ảnh bạn có trong thư mục assets/images vào đây
        obstacle_list = [
            "willows/1.png",
            "willows/2.png", 
            "willows/3.png",
            "trees/1.png",
            "trees/2.png",
            "trees/3.png",
            "stones/1.png",
            "stones/3.png",
            "stones/4.png",
            "stones/5.png"
        ]
        # Bốc ngẫu nhiên 1 ảnh cho chướng ngại vật này
        self.image_path = random.choice(obstacle_list)

    def get_rect(self):
        # Tạo khung va chạm (có thể gọt bớt viền bằng .inflate() nếu ảnh có viền tàng hình)
        rect = pygame.Rect(self.x, self.y, self.width, self.height)
        # Ví dụ gọt viền: rect = rect.inflate(-10, -10)
        return rect

    def draw(self, screen):
        rect = self.get_rect()
        
        # Gọi hàm lấy ảnh, truyền vào image_path đã random ở trên
        sprite = _get_obstacle_sprite(self.image_path, self.width, self.height)
        
        if sprite:
            # Nếu load thành công thì in ảnh ra
            # Chú ý: Dùng self.x và self.y để in ảnh gốc, không bị lệch do gọt hitbox (giống vụ Dino)
            screen.blit(sprite, (self.x, self.y))
        else:
            # Fallback nếu tên file bị gõ sai hoặc ảnh bị xóa mất
            pygame.draw.rect(screen, (0, 150, 50), rect, border_radius=5)


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
        self.y = random.choice([GROUND_Y - 150, GROUND_Y - 110])
        self.anim_frame = 0
        self.anim_timer = 0
        play_sound("bird", volume=0.08)

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
