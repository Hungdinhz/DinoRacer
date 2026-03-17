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
    






