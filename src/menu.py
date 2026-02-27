"""
Menu - Menu chính của game với các lựa chọn: PVE, PVP, Train AI, Quit
"""
import pygame
import random
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# --- CẤU HÌNH MÀU SẮC MỚI (Tông màu hoàng hôn sa mạc) ---
SKY_COLOR_TOP = (60, 30, 70)      # Tím than
SKY_COLOR_BOTTOM = (200, 100, 50) # Cam đất
PARTICLE_COLOR = (220, 180, 100)  # Màu cát

TITLE_COLOR = (255, 215, 0)       # Vàng kim
TITLE_SHADOW_COLOR = (30, 30, 30) # Bóng đen

BTN_NORMAL_COLOR = (80, 50, 90)   # Nút tím tối
BTN_HOVER_COLOR = (120, 70, 130)  # Nút tím sáng hơn khi hover
BTN_TEXT_COLOR = (255, 240, 200)  # Chữ trắng kem
BTN_BORDER_HOVER = (255, 215, 0)  # Viền vàng khi hover

class Particle:
    """Lớp nhỏ để tạo hiệu ứng hạt bụi bay nền"""
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.randint(2, 5)
        self.speed_x = random.uniform(-0.5, 0.5)
        self.speed_y = random.uniform(0.2, 0.8)
        self.alpha = random.randint(50, 150) # Độ trong suốt

    def update(self):
        self.y += self.speed_y
        self.x += self.speed_x
        # Nếu bay ra khỏi màn hình thì reset lại lên trên
        if self.y > SCREEN_HEIGHT:
            self.y = -10
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, screen):
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(s, (*PARTICLE_COLOR, self.alpha), (self.size//2, self.size//2), self.size//2)
        screen.blit(s, (self.x, self.y))

class Menu:
    def __init__(self, screen):
        if not pygame.font.get_init(): pygame.font.init()
        self.screen = screen
        
        # Thử dùng font Impact cho tiêu đề mạnh mẽ hơn (nếu có), không thì dùng Arial đậm
        available_fonts = pygame.font.get_fonts()
        title_font_name = 'impact' if 'impact' in available_fonts else 'arial'
        
        self.font_title = pygame.font.SysFont(title_font_name, 100)
        self.font_item = pygame.font.SysFont('Arial', 35, bold=True)
        self.font_hint = pygame.font.SysFont('Arial', 18)
        
        self.items = ["PVE(VS AI)", "PVP(VS PLAYER)", "Train AI", "Quit"]
        self.selected = 0
        
        # Cấu hình nút
        self.btn_width = 350
        self.btn_height = 55
        self.btn_gap = 25
        
        # Tạo hệ thống hạt (khoảng 50 hạt)
        self.particles = [Particle() for _ in range(50)]
        
        self.button_rects = []
        self._calculate_button_positions()

    def _calculate_button_positions(self):
        center_x = SCREEN_WIDTH // 2
        total_height = len(self.items) * (self.btn_height + self.btn_gap)
        start_y = (SCREEN_HEIGHT - total_height) // 2 + 80 # Dịch xuống một chút
        
        self.button_rects = []
        for i in range(len(self.items)):
            y = start_y + i * (self.btn_height + self.btn_gap)
            rect = pygame.Rect(0, 0, self.btn_width, self.btn_height)
            rect.center = (center_x, y)
            self.button_rects.append(rect)

    def draw_background(self):
        # Vẽ nền gradient giả (chia màn hình làm 2 phần màu)
        pygame.draw.rect(self.screen, SKY_COLOR_TOP, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
        pygame.draw.rect(self.screen, SKY_COLOR_BOTTOM, (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
        # Vẽ một đường mờ ở giữa để chuyển màu mịn hơn
        for i in range(50):
            alpha = 255 - (i * 5)
            color = (*SKY_COLOR_TOP, alpha)
            s = pygame.Surface((SCREEN_WIDTH, 1), pygame.SRCALPHA)
            s.fill(color)
            self.screen.blit(s, (0, SCREEN_HEIGHT // 2 - 25 + i))

        # Vẽ và cập nhật các hạt bụi
        for p in self.particles:
            p.update()
            p.draw(self.screen)

    def draw_title_with_shadow(self, text, y_pos):
        # Vẽ bóng trước (màu tối, dịch lệch một chút)
        shadow_surf = self.font_title.render(text, True, TITLE_SHADOW_COLOR)
        shadow_rect = shadow_surf.get_rect(center=(SCREEN_WIDTH // 2 + 4, y_pos + 4))
        self.screen.blit(shadow_surf, shadow_rect)
        
        # Vẽ chữ chính lên trên
        main_surf = self.font_title.render(text, True, TITLE_COLOR)
        main_rect = main_surf.get_rect(center=(SCREEN_WIDTH // 2, y_pos))
        self.screen.blit(main_surf, main_rect)

    def draw(self):
        self.draw_background()
        self.draw_title_with_shadow("DINO RACER", 120)

        mouse_pos = pygame.mouse.get_pos()

        for i, (item, rect) in enumerate(zip(self.items, self.button_rects)):
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered: self.selected = i
            
            # Chọn màu nền nút
            bg_color = BTN_HOVER_COLOR if i == self.selected else BTN_NORMAL_COLOR
            
            # 1. Vẽ bóng đổ nhẹ cho nút
            shadow_rect = rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(self.screen, (30, 20, 40, 150), shadow_rect, border_radius=15)

            # 2. Vẽ nút chính
            pygame.draw.rect(self.screen, bg_color, rect, border_radius=15)
            
            # 3. Vẽ viền (Nếu hover thì viền vàng sáng, không thì viền tối)
            if i == self.selected:
                pygame.draw.rect(self.screen, BTN_BORDER_HOVER, rect, 3, border_radius=15)
            else:
                 pygame.draw.rect(self.screen, (50, 30, 60), rect, 2, border_radius=15)

            # 4. Vẽ chữ
            text_surf = self.font_item.render(item, True, BTN_TEXT_COLOR)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

        # Hướng dẫn ở góc dưới
        hint = self.font_hint.render("Mouse Click or Arrows + Enter", True, (200, 200, 200))
        self.screen.blit(hint, (10, SCREEN_HEIGHT - 25))

        pygame.display.flip()

    def run(self):
        running = True
        clock = pygame.time.Clock() # Thêm clock để giới hạn FPS cho menu
        while running:
            self.draw()
            clock.tick(60) # Giữ menu chạy mượt ở 60 FPS
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "Quit"
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mouse_pos = pygame.mouse.get_pos()
                        for i, rect in enumerate(self.button_rects):
                            if rect.collidepoint(mouse_pos):
                                return self.items[i]

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.selected = (self.selected - 1) % len(self.items)
                    elif event.key == pygame.K_DOWN:
                        self.selected = (self.selected + 1) % len(self.items)
                    elif event.key == pygame.K_RETURN:
                        return self.items[self.selected]
