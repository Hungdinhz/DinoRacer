"""
Utils - Các hàm dùng chung cho toàn bộ game
Font caching, background generation, và shared utilities
"""
import pygame

# ==================== FONT CACHE ====================
_font_cache = {}


def get_cached_font(name, size, bold=False):
    """Lấy font từ cache, tạo mới nếu chưa có."""
    key = (name, size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
    return _font_cache[key]


def clear_font_cache():
    """Xóa font cache - gọi khi cần giải phóng bộ nhớ."""
    global _font_cache
    _font_cache = {}


# ==================== BACKGROUND CACHE ====================
_gradient_cache = {}


def get_gradient_bg(width, height, bg_index=0, top_color=None, bottom_color=None):
    """
    Tạo/cached gradient background.
    width, height: kích thước surface
    bg_index: index để phân biệt các loại background khác nhau
    top_color, bottom_color: màu gradient (None = dùng mặc định)
    """
    # Màu mặc định cho game
    if top_color is None:
        top_color = (100, 180, 230)
    if bottom_color is None:
        bottom_color = (255, 210, 120)

    key = (width, height, bg_index, top_color, bottom_color)
    if key not in _gradient_cache:
        surf = pygame.Surface((width, height))
        for y in range(height):
            t = y / height
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (width, y))
        _gradient_cache[key] = surf
    return _gradient_cache[key]


def clear_gradient_cache():
    """Xóa gradient cache - gọi khi resize màn hình."""
    global _gradient_cache
    _gradient_cache = {}


# ==================== MENU BACKGROUND ====================
_menu_bg_cache = None
_menu_bg_size = (0, 0)


def get_menu_background(screen_width, screen_height):
    """Tạo/cached gradient background cho menu."""
    global _menu_bg_cache, _menu_bg_size

    if _menu_bg_cache is None or _menu_bg_size != (screen_width, screen_height):
        _menu_bg_size = (screen_width, screen_height)
        _menu_bg_cache = pygame.Surface((screen_width, screen_height))

        SKY_COLOR_TOP = (60, 30, 70)
        SKY_COLOR_BOTTOM = (200, 100, 50)

        for y in range(screen_height):
            t = y / screen_height
            r = int(SKY_COLOR_TOP[0] + (SKY_COLOR_BOTTOM[0] - SKY_COLOR_TOP[0]) * t)
            g = int(SKY_COLOR_TOP[1] + (SKY_COLOR_BOTTOM[1] - SKY_COLOR_TOP[1]) * t)
            b = int(SKY_COLOR_TOP[2] + (SKY_COLOR_BOTTOM[2] - SKY_COLOR_TOP[2]) * t)
            pygame.draw.line(_menu_bg_cache, (r, g, b), (0, y), (screen_width, y))

    return _menu_bg_cache


def clear_menu_background_cache():
    """Xóa menu background cache."""
    global _menu_bg_cache, _menu_bg_size
    _menu_bg_cache = None
    _menu_bg_size = (0, 0)


# ==================== SHARED CONSTANTS ====================
# Game over colors
GO_RED = (255, 215, 0)  # Gold/Yellow
GO_GREEN = (80, 200, 80)

# Particle colors
PARTICLE_COLORS = [
    (255, 80, 30), (255, 180, 0), (255, 230, 80), (200, 50, 20)
]

# HUD background preset
HUD_BG_WIDTH = 260
HUD_BG_HEIGHT = 70
HUD_BG_ALPHA = 110
HUD_BG_BORDER_COLOR = (255, 200, 50)
HUD_BG_BORDER_ALPHA = 160


def get_hud_bg_surface():
    """Tạo cached HUD background surface."""
    surf = pygame.Surface((HUD_BG_WIDTH, HUD_BG_HEIGHT), pygame.SRCALPHA)
    surf.fill((0, 0, 0, HUD_BG_ALPHA))
    pygame.draw.rect(surf, (HUD_BG_BORDER_COLOR[0], HUD_BG_BORDER_COLOR[1],
                           HUD_BG_BORDER_COLOR[2], HUD_BG_BORDER_ALPHA),
                   (0, 0, HUD_BG_WIDTH, HUD_BG_HEIGHT), 2, border_radius=8)
    return surf
