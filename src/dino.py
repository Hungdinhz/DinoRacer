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
import math

# Lấy giá trị từ settings
DINO_X = game_settings.DINO_X
DINO_WIDTH = game_settings.DINO_WIDTH
DINO_HEIGHT = game_settings.DINO_HEIGHT
DINO_COLOR = game_settings.DINO_COLOR
GROUND_Y = game_settings.GROUND_Y
GRAVITY = game_settings.GRAVITY
JUMP_VELOCITY = game_settings.JUMP_VELOCITY
JUMP_HOLD_GRAVITY = getattr(game_settings, 'JUMP_HOLD_GRAVITY', GRAVITY)
JUMP_MIN_VELOCITY = getattr(game_settings, 'JUMP_MIN_VELOCITY', -8)
COYOTE_TIME = getattr(game_settings, 'COYOTE_TIME', 6)
JUMP_BUFFER = getattr(game_settings, 'JUMP_BUFFER', 8)
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
        self.base_y = GROUND_Y - DINO_HEIGHT  # Vị trí ground chuẩn
        self.width = DINO_WIDTH
        self.height = DINO_HEIGHT
        self.vel_y = 0
        self.is_jumping = False
        self.is_ducking = False
        self.is_on_ground = True
        self.color = DINO_COLOR
        self.folder = folder   # "dino" hoặc "ai_dino"
        self.anim_frame = 0
        self.anim_timer = 0
        self._cur_anim = "move"
        # Cache rect để tránh tạo mới mỗi frame
        self._cached_rect = None
        # Ground y cho lane game
        self.ground_y = GROUND_Y

        # Smooth physics
        self._coyote_timer = 0        # Đếm thời gian sau khi rời ground
        self._jump_buffer_timer = 0   # Đếm thời gian trước khi chạm ground
        self._was_jumping = False     # Track trạng thái jumping trước đó
        self._jump_held = False       # Track xem phím jump có đang được giữ

        # Squash & stretch
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._target_scale_x = 1.0
        self._target_scale_y = 1.0
        self._scale_lerp_speed = 0.15  # Tốc độ interpolate scale

        # Motion trail - tạo cảm giác mượt khi di chuyển nhanh
        self._trail_positions = []  # Danh sách vị trí cũ
        self._trail_max_length = 5  # Số lượng trail tối đa
        self._trail_color = (200, 200, 200, 80)  # Màu trail (RGBA)
        self._last_x = self.x
        self._last_y = self.y

    def _anim_name(self):
        if self.is_jumping:
            return "jump"
        if self.is_ducking:
            return "bow"
        return "move"

    def jump(self):
        """Bắt đầu nhảy - hỗ trợ jump buffer và coyote time"""
        # Kiểm tra có thể nhang trên ground hoặc trảy: đong coyote time
        can_jump = self.is_on_ground or self._coyote_timer > 0
        if can_jump and not self.is_ducking:
            self.vel_y = JUMP_VELOCITY  # Dùng biến local thay vì gọi game_settings
            self.is_jumping = True
            self.is_on_ground = False
            self._coyote_timer = 0  # Reset coyote time
            self._jump_held = True
            self.anim_frame = 0
            self.anim_timer = 0
            play_sound("jump")

            # Squash effect khi nhảy - tắt để không bị méo
            self._scale_x = 1.0
            self._scale_y = 1.0

    def jump_press(self):
        """Xử lý khi phím jump được nhấn - hỗ trợ jump buffer"""
        # Nếu không thể nhảy ngay, lưu vào buffer
        if not self.is_jumping and not self.is_ducking:
            if self.is_on_ground:
                self.jump()
            else:
                # Jump buffer - lưu ý muốn nhảy khi chạm ground
                self._jump_buffer_timer = JUMP_BUFFER

    def jump_release(self):
        """Xử lý khi phím jump được thả - variable jump height"""
        self._jump_held = False
        # Nếu đang nhảy lên và thả sớm, giảm velocity
        if self.is_jumping and self.vel_y < JUMP_MIN_VELOCITY:
            self.vel_y = JUMP_MIN_VELOCITY

    def duck(self, is_ducking: bool):
        """Đặt trạng thái cúi - chỉ khi không nhảy"""
        if not self.is_jumping:
            was_ducking = self.is_ducking
            self.is_ducking = is_ducking
            if was_ducking != is_ducking:
                self._cached_rect = None  # Invalidate cache khi thay đổi trạng thái

    def set_duck(self, should_duck: bool):
        """Đặt trạng thái cúi - AI dùng hàm này thay vì duck()"""
        if not self.is_jumping:
            self.is_ducking = should_duck
            self._cached_rect = None  # Invalidate cache

    def _update_scale(self):
        """Cập nhật squash & stretch"""
        # Lerp về target scale
        self._scale_x += (1.0 - self._scale_x) * self._scale_lerp_speed
        self._scale_y += (1.0 - self._scale_y) * self._scale_lerp_speed

    def update(self, jump_held=False):
        was_on_ground = self.is_on_ground

        if self.is_jumping:
            # Sử dụng gravity nhẹ hơn khi giữ phím (variable jump height)
            current_gravity = JUMP_HOLD_GRAVITY if jump_held or self._jump_held else GRAVITY
            self.vel_y += current_gravity
            self.y += self.vel_y

            # Tính toán ground level cho dino hiện tại
            ground_level = self.ground_y - self.height
            # Sửa: dùng >= thay vì > để đảm bảo landing đúng
            if self.y >= ground_level:
                self.y = ground_level
                self.vel_y = 0
                self.is_jumping = False
                self.is_on_ground = True
                self._coyote_timer = COYOTE_TIME  # Reset coyote time sau khi land
        else:
            # Trên ground - đảm bảo y đúng vị trí
            self.is_on_ground = True
            ground_level = self.ground_y - self.height
            if self.y < ground_level:
                self.y = ground_level

            # Xử lý coyote time - giảm timer nếu đã rời ground
            if not was_on_ground:
                # Vừa rời ground, bắt đầu đếm coyote time
                self._coyote_timer = COYOTE_TIME
            elif self._coyote_timer > 0:
                self._coyote_timer -= 1

            # Xử lý jump buffer
            if self._jump_buffer_timer > 0:
                self._jump_buffer_timer -= 1
                if self.is_on_ground:
                    self.jump()
                    self._jump_buffer_timer = 0

        # Cập nhật squash & stretch
        self._update_scale()

        # Cập nhật motion trail
        # Chỉ thêm trail khi có sự thay đổi vị trí đáng kể
        if abs(self.x - self._last_x) > 2 or abs(self.y - self._last_y) > 2:
            self._trail_positions.append((self.x, self.y))
            if len(self._trail_positions) > self._trail_max_length:
                self._trail_positions.pop(0)
        self._last_x = self.x
        self._last_y = self.y

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

        # Vẽ motion trail trước (chỉ khi đang nhảy và có sprite)
        if self.is_jumping and len(self._trail_positions) > 0 and frames:
            for i, (tx, ty) in enumerate(self._trail_positions):
                # Tính alpha giảm dần
                alpha = int(40 * (i + 1) / len(self._trail_positions))
                idx = min(self.anim_frame, len(frames) - 1)
                frame_copy = frames[idx].copy()
                # Áp dụng alpha bằng convert + blit với per-pixel alpha
                temp_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                temp_surf.blit(frame_copy, (0, 0))
                temp_surf.set_alpha(alpha)
                screen.blit(temp_surf, (tx, rect.y))

        if frames:
            idx = min(self.anim_frame, len(frames) - 1)
            frame = frames[idx]

            # Áp dụng squash & stretch nếu cần
            if abs(self._scale_x - 1.0) > 0.03 or abs(self._scale_y - 1.0) > 0.03:
                # Tính toán kích thước mới
                new_w = int(self.width * self._scale_x)
                new_h = int(self.height * self._scale_y)

                # Scale frame
                scaled = pygame.transform.scale(frame, (new_w, new_h))

                # Tính toán vị trí để giữ center
                offset_x = (self.width - new_w) // 2
                offset_y = (self.height - new_h) - ((self.height - new_h) // 2)

                screen.blit(scaled, (rect.x + offset_x, rect.y + offset_y))
            else:
                screen.blit(frame, (rect.x, rect.y))
        else:
            # Fallback vẽ tay với squash & stretch
            w = int(rect.width * self._scale_x)
            h = int(rect.height * self._scale_y)
            x = rect.x + (rect.width - w) // 2
            y = rect.y + (rect.height - h)

            scaled_rect = pygame.Rect(x, y, w, h)
            pygame.draw.rect(screen, self.color, scaled_rect)
            eye_x = x + w - 12
            eye_y = y + 12
            pygame.draw.circle(screen, (255, 255, 255), (eye_x, eye_y), 4)
            pygame.draw.circle(screen, (0, 0, 0), (eye_x + 1, eye_y), 2)
