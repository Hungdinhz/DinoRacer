"""File này sẽ chuyên lo việc vẽ điểm số, vẽ nút bấm, vẽ màn hình"""

import pygame
import math


from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR, INITIAL_SCORE
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

class UILayer:
    def __init__(self, screen):
        self.screen = screen

        # Sử dụng cached fonts thay vì tạo mới
        self.font_hud   = get_cached_font('Arial', 24, bold=True)
        self.font_large = get_cached_font('impact', 68, bold=True)
        self.font_med   = get_cached_font('Arial', 30, bold=True)
        self.font_small = get_cached_font('Arial', 20)
        self.font_speed = get_cached_font('Arial', 18)
        self.score = INITIAL_SCORE
        self.highscore_human, self.highscore_ai = load_highscore()
        self.is_ai_mode = False

        # Nút pause
        self.pause_btn = pygame.Rect(SCREEN_WIDTH - 100, 10, 50, 50)

        #Nut trong menu Pause
        btn_w, btn_h = 200, 50
        gap = 20
        self.items = ["Resume", "Restart", "Quit"]
        self._calculate_pause_menu_positions(btn_w, btn_h, gap)

        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []  # Particles khi chết
        self.dust_particles = []  # Bụi khi chạy
        self._dust_spawn_timer = 0  # Timer để spawn bụi
        self.go_flash_timer = 0
        self.bg_index = 1

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

    def draw_pause_icon(self, is_paused):
        mouse_pos = pygame.mouse.get_pos()
        color = (150, 150, 150) if self.pause_btn.collidepoint(mouse_pos) else (100, 100, 100)
        pygame.draw.rect(self.screen, color, self.pause_btn, border_radius=5)
        
        if is_paused:
            pygame.draw.polygon(self.screen, (255, 255, 255), [
                (self.pause_btn.left + 12, self.pause_btn.top + 10),
                (self.pause_btn.left + 12, self.pause_btn.bottom - 10),
                (self.pause_btn.right - 10, self.pause_btn.centery)
            ])
        else:
            pygame.draw.rect(self.screen, (255, 255, 255), (self.pause_btn.left + 10, self.pause_btn.top + 10, 10, 30))
            pygame.draw.rect(self.screen, (255, 255, 255), (self.pause_btn.left + 30, self.pause_btn.top + 10, 10, 30))

    def _draw_button(self, rect, text):
        mouse_pos = pygame.mouse.get_pos()
        color = BTN_HOVER if rect.collidepoint(mouse_pos) else BTN_COLOR
        pygame.draw.rect(self.screen, color, rect, border_radius=10)
        pygame.draw.rect(self.screen, (200, 200, 200), rect, 2, border_radius=10)
        
        txt_surf = self.font_hud.render(text, True, BTN_TEXT)
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)
    
    def draw_pause_menu(self):
        # Vẽ nền mờ
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 128)) # Màu trắng mờ
        self.screen.blit(overlay, (0,0))

        title = self.font_hud.render("PAUSED", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 150)))

        for item, rect in self.pause_menu_rects.items():
            self._draw_button(rect, item)

    def draw_game_over(self):
        fade_progress = min(1.0, self.go_flash_timer / 30)
        overlay_alpha = int(170 * fade_progress)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, overlay_alpha))
        self.screen.blit(overlay, (0, 0))

        for p in self.particles:
            p.draw(self.screen)

        pw, ph = 500, 280
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2 - 20

        shadow_offset = 8
        shadow_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, int(80 * fade_progress)))
        self.screen.blit(shadow_surf, (px + shadow_offset, py + shadow_offset))

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 15, 10, 230))

        flash = abs(math.sin(self.go_flash_timer * 0.08))
        border_col = (
            int(255 * fade_progress),
            int(200 * fade_progress),
            int(50 * fade_progress),
        )

        self.screen.blit(panel, (px, py))
        pygame.draw.rect(self.screen, border_col, (px, py, pw, ph), 3, border_radius=14)
        pygame.draw.rect(self.screen, (60, 50, 40), (px + 8, py + 8, pw - 16, ph - 16), 1, border_radius=10)

        go_shadow = self.font_large.render("GAME OVER", True, (80, 20, 10))
        self.screen.blit(go_shadow, go_shadow.get_rect(center=(SCREEN_WIDTH // 2 + 3, py + 58 + 3)))

        go_color = GO_RED  # Yellow/Gold color
        go_txt = self.font_large.render("GAME OVER", True, go_color)
        self.screen.blit(go_txt, go_txt.get_rect(center=(SCREEN_WIDTH // 2, py + 58)))

        score_bg_rect = pygame.Rect(px + 30, py + 95, pw - 60, 70)
        pygame.draw.rect(self.screen, (30, 25, 20, 180), score_bg_rect, border_radius=10)
        pygame.draw.rect(self.screen, (80, 70, 50), score_bg_rect, 1, border_radius=10)

        h = max(self.highscore_ai if self.is_ai_mode else self.highscore_human, self.score)

        score_label = self.font_small.render("SCORE", True, (180, 180, 180))
        self.screen.blit(score_label, score_label.get_rect(center=(SCREEN_WIDTH // 2 - 100, py + 115)))

        score_value = self.font_large.render(f"{self.score:05d}", True, (255, 230, 80))
        self.screen.blit(score_value, score_value.get_rect(center=(SCREEN_WIDTH // 2 - 100, py + 145)))

        hi_label = self.font_small.render("HIGH SCORE", True, (180, 180, 180))
        self.screen.blit(hi_label, hi_label.get_rect(center=(SCREEN_WIDTH // 2 + 100, py + 115)))

        hi_value = self.font_large.render(f"{h:05d}", True, (255, 100, 100))
        self.screen.blit(hi_value, hi_value.get_rect(center=(SCREEN_WIDTH // 2 + 100, py + 145)))

        r_box = pygame.Rect(px + 40, py + 185, 180, 45)
        pygame.draw.rect(self.screen, (60, 120, 60, 150), r_box, border_radius=8)
        pygame.draw.rect(self.screen, (100, 200, 100), r_box, 2, border_radius=8)

        r_symbol = self.font_med.render("⟳", True, GO_GREEN)
        r_txt = self.font_med.render("RETRY", True, GO_GREEN)
        self.screen.blit(r_symbol, r_symbol.get_rect(center=(r_box.x + 30, r_box.centery)))
        self.screen.blit(r_txt, r_txt.get_rect(center=(r_box.x + 100, r_box.centery)))
        r_hint = self.font_small.render("Press R", True, (150, 180, 150))
        self.screen.blit(r_hint, r_hint.get_rect(center=(r_box.x + 100, r_box.bottom - 8)))

        m_box = pygame.Rect(px + pw - 220, py + 185, 180, 45)
        pygame.draw.rect(self.screen, (60, 60, 120, 150), m_box, border_radius=8)
        pygame.draw.rect(self.screen, (100, 150, 200), m_box, 2, border_radius=8)

        m_symbol = self.font_med.render("☰", True, (180, 180, 255))
        m_txt = self.font_med.render("MENU", True, (180, 180, 255))
        m_hint = self.font_small.render("Press ESC", True, (150, 150, 200))
        self.screen.blit(m_symbol, m_symbol.get_rect(center=(m_box.x + 30, m_box.centery)))
        self.screen.blit(m_txt, m_txt.get_rect(center=(m_box.x + 100, m_box.centery)))
        self.screen.blit(m_hint, m_hint.get_rect(center=(m_box.x + 100, m_box.bottom - 8)))

    def handle_pause_menu_click(self, pos):
        for item, rect in self.pause_menu_rects.items():
            if rect.collidepoint(pos):
                return item
        return None
    
    def is_pause_button_clicked(self, pos):
        return self.pause_btn.collidepoint(pos)
    






