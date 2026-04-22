"""File này sẽ chuyên lo việc vẽ điểm số, vẽ nút bấm, vẽ màn hình"""

import pygame
import math


from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR, INITIAL_SCORE
from src.dino import GROUND_Y
from src.utils import GO_GREEN, GO_RED
from src.obstacle import create_obstacle
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound, load_image, CLOUD_POSITIONS
from src.achievements import check_achievements
from src.menu import settings as game_settings
from src.utils import (
    get_cached_font, get_gradient_bg, clear_gradient_cache,
    get_hud_bg_surface, PARTICLE_COLORS, GO_RED, GO_GREEN,
)

# Màu sắc UI
BTN_COLOR = (70, 70, 70)
BTN_HOVER = (100, 100, 100)
BTN_TEXT = (255, 255, 255)
SKY_TOP     = (100, 180, 230)
SKY_BOT     = (255, 210, 120)
GROUND_COL  = (160, 120, 60)
GROUND_LINE = (120, 85, 35)
CLOUD_COL   = (255, 255, 255)
TEXT_LIGHT  = (255, 255, 255)
GO_BORDER   = (255, 200, 50)

# ==================== GLOBAL CACHES ====================
# Tile cache
_tile_cache = {}


def _get_cached_tile(name, size):
    """Cache ground tiles."""
    key = (name, size)
    if key not in _tile_cache:
        _tile_cache[key] = load_image(f"tiles/{name}", size)
    return _tile_cache[key]


def clear_game_cache():
    """Xóa tất cả cache - gọi khi cần reset hoặc thay đổi settings."""
    global _tile_cache
    _tile_cache = {}
    clear_gradient_cache()


# Background cache - sử dụng assets_loader hoặc fallback gradient
_bg_cache = {}

def _get_bg(bg_index):
    if bg_index not in _bg_cache:
        img = load_image(f"background/bg{bg_index}.png", (SCREEN_WIDTH, SCREEN_HEIGHT))
        if img is None:
            img = get_gradient_bg(SCREEN_WIDTH, SCREEN_HEIGHT, bg_index, SKY_TOP, SKY_BOT)
        _bg_cache[bg_index] = img
    return _bg_cache[bg_index]


def clear_game_cache():
    """Xóa tất cả cache - gọi khi cần reset hoặc thay đổi settings."""
    global _bg_cache, _tile_cache
    _bg_cache = {}
    _tile_cache = {}
    clear_gradient_cache()

class UILayer:
    def __init__(self, screen):
        self.screen = screen

        # Sử dụng cached fonts thay vì tạo mới
        self.font_hud   = get_cached_font('Arial', 24, bold=True)
        self.font_large = get_cached_font('impact', 68, bold=True)
        self.font_med   = get_cached_font('Arial', 30, bold=True)
        self.font_small = get_cached_font('Arial', 20)
        self.font_speed = get_cached_font('Arial', 18)
        self.font_title = get_cached_font('Arial', 60, bold=True)
        self.score = INITIAL_SCORE
        self.highscore_human, self.highscore_ai = load_highscore()
        self.highscore = self.highscore_human  # Hiển thị highscore của người chơi
        self.is_ai_mode = False

        # Nút pause
        self.pause_btn = pygame.Rect(SCREEN_WIDTH - 100, 10, 50, 50)

        #Nut trong menu Pause
        btn_w, btn_h = 200, 50
        gap = 20
        self.items = ["Resume", "Restart", "Quit"]
        self._calculate_pause_menu_positions(btn_w, btn_h, gap)

        self.bg_offset = 0
        self.particles = []  # Particles khi chết
        self.dust_particles = []  # Bụi khi chạy
        self._dust_spawn_timer = 0  # Timer để spawn bụi
        self.go_flash_timer = 0
        self.bg_index = 1

        # Notification system
        self.notifications = []  # list of {"text", "color", "timer", "max_timer", "y_offset"}

    def add_notification(self, text, color=(255, 255, 255), duration=90):
        """Thêm thông báo hiệu ứng item."""
        self.notifications.append({
            "text": text,
            "color": color,
            "timer": duration,
            "max_timer": duration,
            "y_offset": 0.0,
        })

    def update_notifications(self):
        """Cập nhật notification: giảm timer, xóa hết."""
        alive = []
        for n in self.notifications:
            n["timer"] -= 1
            n["y_offset"] -= 1.0  # trôi lên
            if n["timer"] > 0:
                alive.append(n)
        self.notifications = alive

    def draw_notifications(self):
        """Vẽ các notification đang active."""
        for i, n in enumerate(self.notifications):
            # Fade: alpha giảm dần
            alpha = int(255 * (n["timer"] / n["max_timer"]))
            if alpha <= 0:
                continue
            text_surf = self.font_med.render(n["text"], True, n["color"])
            text_surf.set_alpha(alpha)
            # Vẽ ở giữa màn hình, mỗi cái cách nhau 40px
            y = SCREEN_HEIGHT // 2 - 80 + i * 40 + n["y_offset"]
            x = SCREEN_WIDTH // 2 - text_surf.get_width() // 2
            self.screen.blit(text_surf, (x, y))

    def _calculate_pause_menu_positions(self, btn_w, btn_h, gap):
        """Tính vị trí các nút trong menu Pause"""
        cx = SCREEN_WIDTH // 2
        total_h = len(self.items) * btn_h + (len(self.items) - 1) * gap
        start_y = SCREEN_HEIGHT // 2 - total_h // 2 + 80
        self.pause_menu_rects = {}
        for i, item in enumerate(self.items):
            rect = pygame.Rect(cx - btn_w // 2, start_y + i * (btn_h + gap), btn_w, btn_h)
            self.pause_menu_rects[item] = rect
    
    def draw_score(self, score, highscore):
        """Vẽ điểm số và high score ở góc trên"""
        text = self.font.render(f"Score: {score}", True, TEXT_COLOR)
        self.screen.blit(text, (SCREEN_WIDTH // 2 - 50, 10))

        text = self.font.render(f"High Score: {highscore}", True, TEXT_COLOR)
        self.screen.blit(text, (SCREEN_WIDTH // 2 - 80, 50))

    def _draw_pause_btn(self, is_paused):
        mouse_pos = pygame.mouse.get_pos()
        hover = self.pause_btn.collidepoint(mouse_pos)
        color = (180, 180, 180) if hover else (80, 80, 80)
        pygame.draw.rect(self.screen, color, self.pause_btn, border_radius=8)
        pygame.draw.rect(self.screen, (220, 220, 220), self.pause_btn, 2, border_radius=8)
        if is_paused:
            pygame.draw.polygon(self.screen, TEXT_LIGHT, [
                (self.pause_btn.left + 14, self.pause_btn.top + 11),
                (self.pause_btn.left + 14, self.pause_btn.bottom - 11),
                (self.pause_btn.right - 10, self.pause_btn.centery),
            ])
        else:
            pygame.draw.rect(self.screen, TEXT_LIGHT,
                             (self.pause_btn.left + 11, self.pause_btn.top + 11, 9, 28))
            pygame.draw.rect(self.screen, TEXT_LIGHT,
                             (self.pause_btn.left + 30, self.pause_btn.top + 11, 9, 28))

    def _draw_button(self, rect, text):
        mouse_pos = pygame.mouse.get_pos()
        color = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=10)
        
        txt_surf = self.font_hud.render(text, True, BTN_TEXT)
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)

    def _draw_background(self, current_bg_offset):
        bg = _get_bg(self.bg_index)
        ox = int(current_bg_offset) % SCREEN_WIDTH
        self.screen.blit(bg, (-ox, 0))
        if ox > 0:
            self.screen.blit(bg, (SCREEN_WIDTH - ox, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        # (255, 255, 255, 70) là màu trắng với độ mờ 70/255. 
        # Nếu bạn muốn không gian u ám/tối hơn, hãy đổi thành màu đen: (0, 0, 0, 80)
        overlay.fill((255, 255, 255, 100)) 
        self.screen.blit(overlay, (0, 0))
    
    def draw_pause_menu(self):
        # Vẽ nền mờ
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 128)) # Màu trắng mờ
        self.screen.blit(overlay, (0,0))

        title = self.font_hud.render("PAUSED", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 150)))

        for item, rect in self.pause_menu_rects.items():
            self._draw_button(rect, item)

    def _draw_ground(self, current_ground_offset):
        tile_h = SCREEN_HEIGHT - GROUND_Y
        tile_w = 64
        y_offset = 30
        # Sử dụng cached tile
        tile = _get_cached_tile("Tile_02.png", (tile_w, tile_h))
        if tile:
            offset = int(current_ground_offset) % tile_w
            for x in range(-tile_w, SCREEN_WIDTH + tile_w, tile_w):
                self.screen.blit(tile, (x - offset, GROUND_Y- y_offset))
        else:
            pygame.draw.rect(self.screen, GROUND_COL,
                             (0, GROUND_Y, SCREEN_WIDTH, tile_h))
            pygame.draw.line(self.screen, GROUND_LINE,
                             (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
            for i in range(-1, SCREEN_WIDTH // 40 + 2):
                x = i * 40 - int(current_ground_offset) % 40
                pygame.draw.line(self.screen, GROUND_LINE,
                                 (x, GROUND_Y + 10), (x + 22, GROUND_Y + 10), 1)


    def draw_game_over(self, score):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        pw, ph = 400, 280
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        
        pygame.draw.rect(self.screen, (20, 20, 30), (px, py, pw, ph), border_radius=15)
        pygame.draw.rect(self.screen, (255, 80, 80), (px, py, pw, ph), 3, border_radius=15)
        
        title = self.font_title.render("GAME OVER", True, (255, 215, 0))  # Yellow/Gold
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, py + 50)))
        
        score_label = self.font_small.render("SCORE", True, (180, 180, 180))
        self.screen.blit(score_label, score_label.get_rect(center=(SCREEN_WIDTH // 2, py + 110)))
        
        score_value = self.font_hud.render(f"{score:05d}", True, (255, 230, 80))
        self.screen.blit(score_value, score_value.get_rect(center=(SCREEN_WIDTH // 2, py + 140)))
        
        if score >= self.highscore:
            new_hi = self.font_small.render("NEW HIGH SCORE!", True, (255, 200, 50))
            self.screen.blit(new_hi, new_hi.get_rect(center=(SCREEN_WIDTH // 2, py + 170)))
        
        hint = self.font_small.render("Press R to Restart  |  ESC for Menu", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, py + 230)))

    def handle_pause_menu_click(self, pos):
        for item, rect in self.pause_menu_rects.items():
            if rect.collidepoint(pos):
                return item
        return None
    
    def is_pause_button_clicked(self, pos):
        return self.pause_btn.collidepoint(pos)
    
    def draw_buffs(self, speed_timer, max_speed, x2_timer, max_x2, shield_timer, max_shield, sword_charges, sword_key="T"):
        """Vẽ thanh thời gian cho các buff đang kích hoạt"""
        start_x = 20  # Vẽ ở góc trên bên trái màn hình
        start_y = 20
        bar_width = 150
        bar_height = 15
        spacing = 25  # Khoảng cách giữa các thanh bar

        current_y = start_y

        # 1. Vẽ thanh Buff Tốc Độ (Màu Cyan)
        if speed_timer > 0:
            # Tính chiều dài còn lại của thanh bar (tỉ lệ thuận với thời gian)
            fill_width = int((speed_timer / max_speed) * bar_width)
            
            # Vẽ chữ "Speed" nhỏ xíu
            text = self.font_small.render("Speed", True, (0, 255, 255))
            self.screen.blit(text, (start_x, current_y - 2))
            
            # Vẽ viền ngoài màu xám tối
            pygame.draw.rect(self.screen, (50, 50, 50), (start_x + 60, current_y, bar_width, bar_height), border_radius=4)
            # Vẽ thanh bên trong màu xanh 
            pygame.draw.rect(self.screen, (0, 200, 255), (start_x + 60, current_y, fill_width, bar_height), border_radius=4)
            
            current_y += spacing # Đẩy tọa độ Y xuống cho buff tiếp theo

        # 2. Vẽ thanh Buff X2 Vàng (Màu Vàng)
        if x2_timer > 0:
            fill_width = int((x2_timer / max_x2) * bar_width)
            
            text = self.font_small.render("x2 Gold", True, (255, 215, 0))
            self.screen.blit(text, (start_x, current_y - 2))
            
            pygame.draw.rect(self.screen, (50, 50, 50), (start_x + 60, current_y, bar_width, bar_height), border_radius=4)
            pygame.draw.rect(self.screen, (255, 215, 0), (start_x + 60, current_y, fill_width, bar_height), border_radius=4)
            
            current_y += spacing

        # 3. Vẽ thanh Buff Khiên (Màu Xanh Biển)
        if shield_timer > 0:
            fill_width = int((shield_timer / max_shield) * bar_width)
            
            text = self.font_small.render("Shield", True, (0, 191, 255))
            self.screen.blit(text, (start_x, current_y - 2))
            
            pygame.draw.rect(self.screen, (50, 50, 50), (start_x + 60, current_y, bar_width, bar_height), border_radius=4)
            pygame.draw.rect(self.screen, (0, 191, 255), (start_x + 60, current_y, fill_width, bar_height), border_radius=4)
            
            current_y += spacing

        # 4. Vẽ Số lần chém Kiếm
        if sword_charges > 0:
            from src.assets_loader import get_item_sprite
            sword_sprite = get_item_sprite('sword')
            
            if sword_key:
                text_str = f"x {sword_charges} (press {sword_key} to use)"
            else:
                text_str = f"x {sword_charges}"
                
            sword_text = self.font_med.render(text_str, True, (255, 100, 100))
            
            if sword_sprite:
                sword_sprite = pygame.transform.scale(sword_sprite, (40, 40))
                self.screen.blit(sword_sprite, (start_x, current_y - 2))
                self.screen.blit(sword_text, (start_x + sword_sprite.get_width() + 5, current_y))
            else:
                if sword_key:
                    fallback_str = f"Swords: {sword_charges} (press {sword_key} to use)"
                else:
                    fallback_str = f"Swords: {sword_charges}"
                fallback_text = self.font_med.render(fallback_str, True, (255, 100, 100))
                self.screen.blit(fallback_text, (start_x, current_y))
        







