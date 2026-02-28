"""
Class Dino - Xử lý nhảy, cúi, vẽ khủng long với animation từ sprite sheet
Sprite sheets trong assets/images/dino/:
  idle.png  (72x24)  = 3 frames
  move.png  (144x24) = 6 frames
  jump.png  (96x24)  = 4 frames
  bow.png   (144x24) = 6 frames  (cúi)
"""
import pygame
import config.settings as game_settings
from src.assets_loader import get_sheet, play_sound

# Lấy giá trị từ settings
DINO_X = game_settings.DINO_X
DINO_WIDTH = game_settings.DINO_WIDTH
DINO_HEIGHT = game_settings.DINO_HEIGHT
DINO_COLOR = game_settings.DINO_COLOR
GROUND_Y = game_settings.GROUND_Y
GRAVITY = game_settings.GRAVITY
JUMP_VELOCITY = game_settings.JUMP_VELOCITY
DUCK_HEIGHT_RATIO = game_settings.DUCK_HEIGHT_RATIO

# Số frame của mỗi animation
_ANIM_FRAMES = {"idle": 3, "move": 6, "jump": 4, "bow": 6}
# Game-frames mỗi sprite-frame
_ANIM_SPEED  = {"idle": 10, "move": 5, "jump": 8, "bow": 5}


class Dino:
    # Bỏ __slots__ để tránh vấn đề với dynamic attributes

    def __init__(self, x=DINO_X, folder="dino"):
        self.x = x
        self.y = GROUND_Y - DINO_HEIGHT
        self.width = DINO_WIDTH
        self.height = DINO_HEIGHT
        self.vel_y = 0
        self.is_jumping = False
        self.is_ducking = False
        self.color = DINO_COLOR
        self.folder = folder   # "dino" hoặc "ai_dino"
        self.anim_frame = 0
        self.anim_timer = 0
        self._cur_anim = "move"
        # Cache rect để tránh tạo mới mỗi frame
        self._cached_rect = None
        # Ground y cho lane game
        self.ground_y = GROUND_Y

    def _anim_name(self):
        if self.is_jumping:
            return "jump"
        if self.is_ducking:
            return "bow"
        return "move"

    def jump(self):
        if not self.is_jumping and not self.is_ducking:
            # Luôn lấy giá trị mới nhất từ settings
            self.vel_y = game_settings.JUMP_VELOCITY
            self.is_jumping = True
            self.anim_frame = 0
            self.anim_timer = 0
            play_sound("jump")

    def duck(self, is_ducking: bool):
        if not self.is_jumping:
            self.is_ducking = is_ducking
            self._cached_rect = None  # Invalidate cache khi thay đổi trạng thái

    def set_duck(self, should_duck: bool):
        """Đặt trạng thái cúi - AI dùng hàm này thay vì duck()"""
        if not self.is_jumping:
            self.is_ducking = should_duck
            self._cached_rect = None  # Invalidate cache

    def update(self):
        if self.is_jumping:
            self.vel_y += GRAVITY
            self.y += self.vel_y
            ground_level = self.ground_y - self.height
            # Sửa: dùng > thay vì >= để tránh landing ngay lập tức
            if self.y > ground_level:
                self.y = ground_level
                self.vel_y = 0
                self.is_jumping = False

        # Cập nhật animation
        anim = self._anim_name()
        if anim != self._cur_anim:
            self._cur_anim = anim
            self.anim_frame = 0
            self.anim_timer = 0
        else:
            self.anim_timer += 1
            if self.anim_timer >= _ANIM_SPEED.get(anim, 8):
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % _ANIM_FRAMES.get(anim, 1)

    def get_rect(self):
        # Sử dụng cached rect nếu có thể
        if self._cached_rect is not None:
            return self._cached_rect

        h = self.height
        if self.is_ducking:
            h = int(self.height * DUCK_HEIGHT_RATIO)
        self._cached_rect = pygame.Rect(self.x, self.y + (self.height - h), self.width, h)
        return self._cached_rect

    def draw(self, screen):
        rect = self.get_rect()
        anim = self._anim_name()
        num_frames = _ANIM_FRAMES.get(anim, 1)

        frames = get_sheet(
            f"{self.folder}/{anim}.png",
            num_frames,
            self.width,
            self.height
        )

        if frames:
            idx = min(self.anim_frame, len(frames) - 1)
            screen.blit(frames[idx], (rect.x, rect.y))
        else:
            # Fallback vẽ tay
            pygame.draw.rect(screen, self.color, rect)
            eye_x = self.x + self.width - 12
            eye_y = rect.y + 12
            pygame.draw.circle(screen, (255, 255, 255), (eye_x, eye_y), 4)
            pygame.draw.circle(screen, (0, 0, 0), (eye_x + 1, eye_y), 2)
