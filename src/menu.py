"""
Menu - Menu chính của game với các lựa chọn
"""
import pygame
import random
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# --- CẤU HÌNH MÀU SẮC ---
SKY_COLOR_TOP = (60, 30, 70)
SKY_COLOR_BOTTOM = (200, 100, 50)
PARTICLE_COLOR = (220, 180, 100)

TITLE_COLOR = (255, 215, 0)
TITLE_SHADOW_COLOR = (30, 30, 30)

BTN_NORMAL_COLOR = (80, 50, 90)
BTN_HOVER_COLOR = (120, 70, 130)
BTN_TEXT_COLOR = (255, 240, 200)
BTN_BORDER_HOVER = (255, 215, 0)

# --- CONSTANTS ---
MENU_MAIN = "main"
MENU_SETTINGS = "settings"
MENU_STATS = "stats"
MENU_ACHIEVEMENTS = "achievements"

class Particle:
    def __init__(self):
        self.x = random.randint(0, SCREEN_WIDTH)
        self.y = random.randint(0, SCREEN_HEIGHT)
        self.size = random.randint(2, 5)
        self.speed_x = random.uniform(-0.5, 0.5)
        self.speed_y = random.uniform(0.2, 0.8)
        self.alpha = random.randint(50, 150)

    def update(self):
        self.y += self.speed_y
        self.x += self.speed_x
        if self.y > SCREEN_HEIGHT:
            self.y = -10
            self.x = random.randint(0, SCREEN_WIDTH)

    def draw(self, screen):
        s = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(s, (*PARTICLE_COLOR, self.alpha), (self.size//2, self.size//2), self.size//2)
        screen.blit(s, (self.x, self.y))

class GameSettings:
    """Lưu trữ cấu hình game"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.load_settings()
    
    def load_settings(self):
        """Load settings từ database hoặc mặc định"""
        try:
            from src.database_handler import get_setting
            self.sound_enabled = get_setting('sound_enabled', 'true') == 'true'
            self.music_enabled = get_setting('music_enabled', 'true') == 'true'
            self.data_collection_enabled = get_setting('data_collection_enabled', 'true') == 'true'
            self.difficulty = get_setting('difficulty', 'normal')
            self.ai_difficulty = get_setting('ai_difficulty', 'medium')
        except:
            self.sound_enabled = True
            self.music_enabled = True
            self.data_collection_enabled = True
            self.difficulty = 'normal'
            self.ai_difficulty = 'medium'
    
    def save_settings(self):
        """Lưu settings vào database"""
        try:
            from src.database_handler import set_setting
            set_setting('sound_enabled', 'true' if self.sound_enabled else 'false')
            set_setting('music_enabled', 'true' if self.music_enabled else 'false')
            set_setting('data_collection_enabled', 'true' if self.data_collection_enabled else 'false')
            set_setting('difficulty', self.difficulty)
            set_setting('ai_difficulty', self.ai_difficulty)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_difficulty_multiplier(self):
        """Lấy multiplier cho độ khó"""
        multipliers = {'easy': 0.7, 'normal': 1.0, 'hard': 1.3}
        return multipliers.get(self.difficulty, 1.0)

# Singleton
settings = GameSettings()

class Menu:
    def __init__(self, screen):
        if not pygame.font.get_init(): pygame.font.init()
        self.screen = screen
        self.current_menu = MENU_MAIN
        
        available_fonts = pygame.font.get_fonts()
        title_font_name = 'impact' if 'impact' in available_fonts else 'arial'
        
        self.font_title = pygame.font.SysFont(title_font_name, 80)
        self.font_item = pygame.font.SysFont('Arial', 32, bold=True)
        self.font_small = pygame.font.SysFont('Arial', 20)
        self.font_hint = pygame.font.SysFont('Arial', 16)
        
        # Menu items
        self.main_items = ["PVE(VS AI)", "PVP(VS PLAYER)", "Time Attack", "Endless", "Stats", "Settings", "Quit"]
        self.settings_items = ["Sound: ON", "Music: ON", "Data Collection: ON", "Difficulty: Normal", "AI Level: Medium", "Back"]
        
        self.selected = 0
        self.btn_width = 350
        self.btn_height = 55
        self.btn_gap = 20
        
        self.particles = [Particle() for _ in range(50)]
        
        self.button_rects = []
        self._calculate_button_positions()

    def _calculate_button_positions(self):
        if self.current_menu == MENU_MAIN:
            items = self.main_items
        else:
            items = self.settings_items
        
        center_x = SCREEN_WIDTH // 2
        total_height = len(items) * (self.btn_height + self.btn_gap)
        start_y = (SCREEN_HEIGHT - total_height) // 2 + 60
        
        self.button_rects = []
        for i in range(len(items)):
            y = start_y + i * (self.btn_height + self.btn_gap)
            rect = pygame.Rect(0, 0, self.btn_width, self.btn_height)
            rect.center = (center_x, y)
            self.button_rects.append(rect)

    def draw_background(self):
        pygame.draw.rect(self.screen, SKY_COLOR_TOP, (0, 0, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
        pygame.draw.rect(self.screen, SKY_COLOR_BOTTOM, (0, SCREEN_HEIGHT // 2, SCREEN_WIDTH, SCREEN_HEIGHT // 2))
        
        for i in range(50):
            alpha = 255 - (i * 5)
            color = (*SKY_COLOR_TOP, alpha)
            s = pygame.Surface((SCREEN_WIDTH, 1), pygame.SRCALPHA)
            s.fill(color)
            self.screen.blit(s, (0, SCREEN_HEIGHT // 2 - 25 + i))

        for p in self.particles:
            p.update()
            p.draw(self.screen)

    def draw_title_with_shadow(self, text, y_pos):
        shadow_surf = self.font_title.render(text, True, TITLE_SHADOW_COLOR)
        shadow_rect = shadow_surf.get_rect(center=(SCREEN_WIDTH // 2 + 3, y_pos + 3))
        self.screen.blit(shadow_surf, shadow_rect)
        
        main_surf = self.font_title.render(text, True, TITLE_COLOR)
        main_rect = main_surf.get_rect(center=(SCREEN_WIDTH // 2, y_pos))
        self.screen.blit(main_surf, main_rect)

    def draw_button(self, text, rect, is_selected):
        bg_color = BTN_HOVER_COLOR if is_selected else BTN_NORMAL_COLOR
        
        shadow_rect = rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(self.screen, (30, 20, 40, 150), shadow_rect, border_radius=12)

        pygame.draw.rect(self.screen, bg_color, rect, border_radius=12)
        
        if is_selected:
            pygame.draw.rect(self.screen, BTN_BORDER_HOVER, rect, 3, border_radius=12)
        else:
            pygame.draw.rect(self.screen, (50, 30, 60), rect, 2, border_radius=12)

        text_surf = self.font_item.render(text, True, BTN_TEXT_COLOR)
        text_rect = text_surf.get_rect(center=rect.center)
        self.screen.blit(text_surf, text_rect)

    def draw_settings_menu(self):
        self.draw_background()
        self.draw_title_with_shadow("SETTINGS", 80)
        
        # Update settings text based on current values
        self.settings_items = [
            f"Sound: {'ON' if settings.sound_enabled else 'OFF'}",
            f"Music: {'ON' if settings.music_enabled else 'OFF'}",
            f"Data Collection: {'ON' if settings.data_collection_enabled else 'OFF'}",
            f"Difficulty: {settings.difficulty.capitalize()}",
            f"AI Level: {settings.ai_difficulty.capitalize()}",
            "Back"
        ]
        self._calculate_button_positions()
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, (item, rect) in enumerate(zip(self.settings_items, self.button_rects)):
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered: self.selected = i
            self.draw_button(item, rect, i == self.selected)
        
        # Draw instructions
        hint1 = self.font_hint.render("Left/Right arrows to toggle, Up/Down to select", True, (200, 200, 200))
        self.screen.blit(hint1, (SCREEN_WIDTH // 2 - hint1.get_width() // 2, SCREEN_HEIGHT - 40))
        
        pygame.display.flip()

    def draw_stats_menu(self):
        self.draw_background()
        self.draw_title_with_shadow("STATISTICS", 60)
        
        # Get stats from database
        try:
            from src.database_handler import get_training_data_count
            from src.highscore import load_highscore
            
            human_samples = get_training_data_count("human")
            ai_samples = get_training_data_count("ai")
            total_samples = human_samples + ai_samples
            
            hs_human, hs_ai = load_highscore()
        except:
            total_samples = human_samples = ai_samples = 0
            hs_human = hs_ai = 0
        
        # Draw stats
        stats = [
            f"Training Data: {total_samples} samples",
            f"  - From Human: {human_samples}",
            f"  - From AI: {ai_samples}",
            "",
            f"High Score (Human): {hs_human}",
            f"High Score (AI): {hs_ai}",
        ]
        
        y_offset = 180
        for stat in stats:
            surf = self.font_small.render(stat, True, BTN_TEXT_COLOR)
            rect = surf.get_rect(center=(SCREEN_WIDTH // 2, y_offset))
            self.screen.blit(surf, rect)
            y_offset += 35
        
        # Back button
        back_rect = pygame.Rect(0, 0, 150, 45)
        back_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 80)
        self.draw_button("Back", back_rect, self.selected == 0)
        self.button_rects = [back_rect]
        
        hint = self.font_hint.render("Press ENTER or Click to go back", True, (200, 200, 200))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 30))
        
        pygame.display.flip()

    def draw(self):
        self.draw_background()
        
        if self.current_menu == MENU_SETTINGS:
            self.draw_settings_menu()
            return
        elif self.current_menu == MENU_STATS:
            self.draw_stats_menu()
            return
        
        # Main menu
        self.draw_title_with_shadow("DINO RACER", 100)

        mouse_pos = pygame.mouse.get_pos()

        for i, (item, rect) in enumerate(zip(self.main_items, self.button_rects)):
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered: self.selected = i
            self.draw_button(item, rect, i == self.selected)

        # Version info
        hint = self.font_hint.render("v1.0 - Use Arrows + Enter or Mouse Click", True, (180, 180, 180))
        self.screen.blit(hint, (10, SCREEN_HEIGHT - 25))

        pygame.display.flip()

    def handle_settings_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.settings_items)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.settings_items)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_RIGHT:
                self._toggle_setting(self.selected)
            elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                if self.selected == len(self.settings_items) - 1:
                    self.current_menu = MENU_MAIN
                    self.selected = 0
    
    def _toggle_setting(self, index):
        toggles = {
            0: ('sound_enabled', lambda s: not s.sound_enabled),
            1: ('music_enabled', lambda s: not s.music_enabled),
            2: ('data_collection_enabled', lambda s: not s.data_collection_enabled),
        }
        
        cycles = {
            3: ('difficulty', ['easy', 'normal', 'hard']),
            4: ('ai_difficulty', ['easy', 'medium', 'hard']),
        }
        
        if index in toggles:
            key, toggle_func = toggles[index]
            setattr(settings, key, toggle_func(settings))
        elif index in cycles:
            key, values = cycles[index]
            current = getattr(settings, key)
            idx = values.index(current) if current in values else 1
            next_idx = (idx + 1) % len(values)
            setattr(settings, key, values[next_idx])
        
        settings.save_settings()

    def run(self):
        running = True
        clock = pygame.time.Clock()
        
        while running:
            self.draw()
            clock.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "Quit"
                
                if self.current_menu == MENU_SETTINGS:
                    self.handle_settings_input(event)
                    # Also handle mouse click in settings
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mouse_pos = pygame.mouse.get_pos()
                        for i, rect in enumerate(self.button_rects):
                            if rect.collidepoint(mouse_pos):
                                if i == len(self.settings_items) - 1:  # Back button
                                    self.current_menu = MENU_MAIN
                                    self.selected = 0
                                else:
                                    self._toggle_setting(i)
                    continue
                
                if self.current_menu == MENU_STATS:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                        self.current_menu = MENU_MAIN
                        self.selected = 0
                    # Also handle mouse click in stats
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mouse_pos = pygame.mouse.get_pos()
                        for rect in self.button_rects:
                            if rect.collidepoint(mouse_pos):
                                self.current_menu = MENU_MAIN
                                self.selected = 0
                    continue
                
                # Main menu handling
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        mouse_pos = pygame.mouse.get_pos()
                        for i, rect in enumerate(self.button_rects):
                            if rect.collidepoint(mouse_pos):
                                choice = self.main_items[i]
                                if choice == "Settings":
                                    self.current_menu = MENU_SETTINGS
                                    self.selected = 0
                                    self._calculate_button_positions()
                                elif choice == "Stats":
                                    self.current_menu = MENU_STATS
                                    self.selected = 0
                                else:
                                    return choice

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.selected = (self.selected - 1) % len(self.main_items)
                    elif event.key == pygame.K_DOWN:
                        self.selected = (self.selected + 1) % len(self.main_items)
                    elif event.key == pygame.K_RETURN:
                        choice = self.main_items[self.selected]
                        if choice == "Settings":
                            self.current_menu = MENU_SETTINGS
                            self.selected = 0
                            self._calculate_button_positions()
                        elif choice == "Stats":
                            self.current_menu = MENU_STATS
                            self.selected = 0
                        else:
                            return choice
