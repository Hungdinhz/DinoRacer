"""File này sẽ chuyên lo việc vẽ điểm số, vẽ nút bấm, vẽ màn hình"""

import pygame
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT, TEXT_COLOR

# Màu sắc UI
BTN_COLOR = (70, 70, 70)
BTN_HOVER = (100, 100, 100)
BTN_TEXT = (255, 255, 255)

class UILayer:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.SysFont('Arial', 30, bold=True)
        self.font_large = pygame.font.Font(None, 72)
        self.font_huge = pygame.font.Font(None, 100)

        # Nút pause
        self.pause_btn = pygame.Rect(SCREEN_WIDTH - 100, 10, 50, 50)

        #Nut trong menu Pause
        btn_w, btn_h = 200, 50
        gap = 20
        self.items = ["Resume", "Restart", "Quit"]
        self._caculate_pause_menu_positions(btn_w, btn_h, gap)

    def _caculate_pause_menu_positions(self, btn_w, btn_h, gap):
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
        
        txt_surf = self.font.render(text, True, BTN_TEXT)
        txt_rect = txt_surf.get_rect(center=rect.center)
        self.screen.blit(txt_surf, txt_rect)
    
    def draw_pause_menu(self):
        # Vẽ nền mờ
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 128)) # Màu trắng mờ
        self.screen.blit(overlay, (0,0))

        title = self.font_huge.render("PAUSED", True, (255, 255, 255))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 150)))

        for item, rect in self.pause_menu_rects.items():
            self._draw_button(rect, item)

    def draw_game_over(self):
        text_go = self.font_large.render("GAME OVER", True, (200, 0, 0))
        self.screen.blit(text_go, text_go.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        
        text_restart = self.font.render("Press R to restart", True, TEXT_COLOR)
        self.screen.blit(text_restart, text_restart.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))

    def handle_pause_menu_click(self, pos):
        for item, rect in self.pause_menu_rects.items():
            if rect.collidepoint(pos):
                return item
        return None
    
    def is_pause_button_clicked(self, pos):
        return self.pause_btn.collidepoint(pos)






