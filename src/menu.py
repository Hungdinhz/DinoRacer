"""
Menu - Menu chính của game với các lựa chọn
"""
import pygame
import random
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# ==================== GLOBAL CACHES ====================
# Font cache - tránh tạo font mới mỗi lần
_menu_font_cache = {}


def _get_menu_font(name, size, bold=False):
    """Lấy font từ cache cho menu."""
    key = (name, size, bold)
    if key not in _menu_font_cache:
        _menu_font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
    return _menu_font_cache[key]


# Pre-create background gradient surface
_bg_gradient_surface = None


def _get_menu_background():
    """Cache gradient background cho menu."""
    global _bg_gradient_surface
    # Luôn tạo background với kích thước hiện tại của màn hình
    current_w = pygame.display.get_surface().get_width() if pygame.display.get_surface() else SCREEN_WIDTH
    current_h = pygame.display.get_surface().get_height() if pygame.display.get_surface() else SCREEN_HEIGHT
    
    # Nếu kích thước thay đổi, tạo lại background
    if _bg_gradient_surface is None or _bg_gradient_surface.get_size() != (current_w, current_h):
        _bg_gradient_surface = pygame.Surface((current_w, current_h))

        # Draw gradient
        SKY_COLOR_TOP = (60, 30, 70)
        SKY_COLOR_BOTTOM = (200, 100, 50)

        for y in range(current_h):
            t = y / current_h
            r = int(SKY_COLOR_TOP[0] + (SKY_COLOR_BOTTOM[0] - SKY_COLOR_TOP[0]) * t)
            g = int(SKY_COLOR_TOP[1] + (SKY_COLOR_BOTTOM[1] - SKY_COLOR_TOP[1]) * t)
            b = int(SKY_COLOR_TOP[2] + (SKY_COLOR_BOTTOM[2] - SKY_COLOR_TOP[2]) * t)
            pygame.draw.line(_bg_gradient_surface, (r, g, b), (0, y), (current_w, y))

    return _bg_gradient_surface


def _clear_background_cache():
    """Xóa cache background để tạo lại với kích thước mới"""
    global _bg_gradient_surface
    _bg_gradient_surface = None


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
MENU_TRAIN_AI = "train_ai"

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
            self.skin_dino = get_setting('skin_dino', 'dino')
        except:
            self.sound_enabled = True
            self.music_enabled = True
            self.data_collection_enabled = True
            self.difficulty = 'normal'
            self.ai_difficulty = 'medium'
            self.skin_dino = 'dino'
    
    def save_settings(self):
        """Lưu settings vào database"""
        try:
            from src.database_handler import set_setting
            set_setting('sound_enabled', 'true' if self.sound_enabled else 'false')
            set_setting('music_enabled', 'true' if self.music_enabled else 'false')
            set_setting('data_collection_enabled', 'true' if self.data_collection_enabled else 'false')
            set_setting('difficulty', self.difficulty)
            set_setting('ai_difficulty', self.ai_difficulty)
            set_setting('skin_dino', self.skin_dino)
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

        # Cache stats to avoid querying database every frame
        self.cached_stats = None

        # Sử dụng cached fonts thay vì tạo mới
        available_fonts = pygame.font.get_fonts()
        title_font_name = 'impact' if 'impact' in available_fonts else 'arial'

        self.font_title = _get_menu_font(title_font_name, 80)
        self.font_item = _get_menu_font('Arial', 32, bold=True)
        self.font_small = _get_menu_font('Arial', 20)
        self.font_hint = _get_menu_font('Arial', 16)

        # Menu items - Updated: Added Solo mode
        self.main_items = ["Solo", "PVE(VS AI)", "PVP(VS PLAYER)", "Time Attack", "Endless", "Achievements", "Stats", "Train AI", "Settings", "Quit"]
        self.settings_items = ["Sound: ON", "Music: ON", "Data Collection: ON", "Difficulty: Normal", "AI Level: Medium", "Back"]
        
        self.selected = 0
        self.btn_width = 350
        self.btn_height = 55
        self.btn_gap = 20
        
        self.particles = [Particle() for _ in range(15)]
        
        self.button_rects = []
        self._calculate_button_positions()

    def _calculate_button_positions(self):
        if self.current_menu == MENU_MAIN:
            items = self.main_items
        else:
            items = self.settings_items
        
        # Lấy kích thước màn hình hiện tại
        current_w = self.screen.get_width()
        current_h = self.screen.get_height()
        
        center_x = current_w // 2
        total_height = len(items) * (self.btn_height + self.btn_gap)
        start_y = (current_h - total_height) // 2 + 60
        
        self.button_rects = []
        for i in range(len(items)):
            y = start_y + i * (self.btn_height + self.btn_gap)
            rect = pygame.Rect(0, 0, self.btn_width, self.btn_height)
            rect.center = (center_x, y)
            self.button_rects.append(rect)

    def draw_background(self):
        # Sử dụng cached background thay vì vẽ lại mỗi frame
        self.screen.blit(_get_menu_background(), (0, 0))

        # Chỉ update và vẽ particles
        for p in self.particles:
            p.update()
            p.draw(self.screen)

    def draw_title_with_shadow(self, text, y_pos):
        # Lấy kích thước màn hình hiện tại
        current_w = self.screen.get_width()
        
        shadow_surf = self.font_title.render(text, True, TITLE_SHADOW_COLOR)
        shadow_rect = shadow_surf.get_rect(center=(current_w // 2 + 3, y_pos + 3))
        self.screen.blit(shadow_surf, shadow_rect)
        
        main_surf = self.font_title.render(text, True, TITLE_COLOR)
        main_rect = main_surf.get_rect(center=(current_w // 2, y_pos))
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

    def _get_screen_dims(self):
        """Lấy kích thước màn hình hiện tại"""
        return self.screen.get_width(), self.screen.get_height()
    
    def draw_settings_menu(self):
        self.draw_background()
        self.draw_title_with_shadow("SETTINGS", 80)
        
        # Danh sách skin có sẵn
        SKINS = ['dino', 'dino2', 'dino3']
        skin_label = settings.skin_dino.upper()

        # Cập nhật text
        self.settings_items = [
            f"Sound: {'ON' if settings.sound_enabled else 'OFF'}",
            f"Music: {'ON' if settings.music_enabled else 'OFF'}",
            f"Data Collection: {'ON' if settings.data_collection_enabled else 'OFF'}",
            f"Difficulty: {settings.difficulty.capitalize()}",
            f"AI Level: {settings.ai_difficulty.capitalize()}",
            f"Skin: {skin_label}",
            "Back"
        ]
        self._calculate_button_positions()
        
        mouse_pos = pygame.mouse.get_pos()
        
        for i, (item, rect) in enumerate(zip(self.settings_items, self.button_rects)):
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered: self.selected = i
            self.draw_button(item, rect, i == self.selected)
        
        # Draw instructions
        sw, sh = self._get_screen_dims()
        hint1 = self.font_hint.render("Left/Right arrows to toggle, Up/Down to select", True, (200, 200, 200))
        self.screen.blit(hint1, (sw // 2 - hint1.get_width() // 2, sh - 40))
        
        pygame.display.flip()

    def draw_achievements_menu(self):
        """Hiển thị danh sách thành tựu"""
        from src.achievements import get_achievements
        self.draw_background()
        self.draw_title_with_shadow("ACHIEVEMENTS", 60)

        ach_obj = get_achievements()
        all_ach = ach_obj.get_all_achievements()
        unlocked_count = ach_obj.get_unlocked_count()
        total_count = ach_obj.get_total_count()

        # Tiêu đề phụ
        sw, sh = self._get_screen_dims()
        sub = self.font_small.render(
            f"Mở khóa: {unlocked_count} / {total_count}",
            True, (200, 200, 200)
        )
        self.screen.blit(sub, (sw // 2 - sub.get_width() // 2, 110))

        # Vẽ grid (3 cột)
        cols = 3
        cell_w = 300
        cell_h = 70
        gap_x = 20
        gap_y = 12
        total_w = cols * cell_w + (cols - 1) * gap_x
        start_x = sw // 2 - total_w // 2
        start_y = 145

        for idx, ach in enumerate(all_ach):
            col = idx % cols
            row = idx // cols
            cx = start_x + col * (cell_w + gap_x)
            cy = start_y + row * (cell_h + gap_y)

            # Dừng khi ra ngoài màn hình
            if cy + cell_h > sh - 50:
                break

            if ach['unlocked']:
                bg_col = (40, 60, 40, 200)
                border_col = (100, 200, 100)
                text_col = (255, 255, 255)
                icon_col = (255, 230, 80)
            else:
                bg_col = (30, 30, 40, 180)
                border_col = (80, 80, 100)
                text_col = (120, 120, 140)
                icon_col = (80, 80, 100)

            cell = pygame.Surface((cell_w, cell_h), pygame.SRCALPHA)
            cell.fill(bg_col)
            self.screen.blit(cell, (cx, cy))
            pygame.draw.rect(self.screen, border_col, (cx, cy, cell_w, cell_h), 1, border_radius=6)

            icon_surf = self.font_item.render(ach['icon'] if ach['unlocked'] else '🔒', True, icon_col)
            self.screen.blit(icon_surf, (cx + 8, cy + cell_h // 2 - icon_surf.get_height() // 2))

            name_surf = self.font_small.render(ach['name'], True, text_col)
            self.screen.blit(name_surf, (cx + 50, cy + 8))

            desc_surf = self.font_hint.render(ach['description'], True, text_col)
            self.screen.blit(desc_surf, (cx + 50, cy + 34))

        # Nút back
        back_rect = pygame.Rect(0, 0, 150, 45)
        # Back button
        sw, sh = self._get_screen_dims()
        back_rect.center = (sw // 2, sh - 35)
        self.draw_button("← BACK", back_rect, self.selected == 0)
        self.button_rects = [back_rect]

        pygame.display.flip()

    def draw_train_ai_menu(self):
        """Submenu chọn loại Training AI"""
        self.draw_background()
        self.draw_title_with_shadow("TRAIN AI", 80)

        sw, sh = self._get_screen_dims()
        desc_lines = [
            "Chọn phương pháp huấn luyện AI:",
            "",
            "NEAT: Thuật toán tiến hóa mạng neural (không cần dữ liệu)",
            "Supervised: Học từ dữ liệu chơi của người và AI (PVP mode)",
        ]
        y = 160
        for line in desc_lines:
            s = self.font_small.render(line, True, (200, 200, 200))
            self.screen.blit(s, (sw // 2 - s.get_width() // 2, y))
            y += 28

        items = ["NEAT Training", "Supervised Training", "Back"]
        btn_w, btn_h, gap = 320, 55, 18
        total_h = len(items) * (btn_h + gap)
        start_y = sh // 2 + 30
        self.button_rects = []
        for i, item in enumerate(items):
            rect = pygame.Rect(0, 0, btn_w, btn_h)
            rect.center = (sw // 2, start_y + i * (btn_h + gap))
            self.button_rects.append(rect)

        mouse_pos = pygame.mouse.get_pos()
        for i, (item, rect) in enumerate(zip(items, self.button_rects)):
            if rect.collidepoint(mouse_pos):
                self.selected = i
            self.draw_button(item, rect, i == self.selected)

        pygame.display.flip()

    def draw_stats_menu(self):
        self.draw_background()
        self.draw_title_with_shadow("STATISTICS", 60)

        # Chỉ fetch khi vào menu
        if self.cached_stats is None:
            stats = {}
            try:
                from src.database_handler import get_training_data_count, get_connection
                from src.highscore import load_highscore
                stats['human_samples'] = get_training_data_count('human')
                stats['ai_samples']    = get_training_data_count('ai')
                hs_human, hs_ai = load_highscore()
                stats['hs_human'] = hs_human
                stats['hs_ai']    = hs_ai
                # Lấy data sessions từ DB
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT game_mode, COUNT(*) as total, AVG(score) as avg_score, MAX(score) as top_score
                    FROM game_sessions
                    GROUP BY game_mode
                    ORDER BY total DESC
                """)
                stats['sessions'] = cursor.fetchall()
                cursor.execute("SELECT COUNT(*) FROM game_sessions")
                stats['total_games'] = cursor.fetchone()[0]
                cursor.close(); conn.close()
            except Exception as e:
                stats.setdefault('human_samples', 0)
                stats.setdefault('ai_samples', 0)
                stats.setdefault('hs_human', 0)
                stats.setdefault('hs_ai', 0)
                stats.setdefault('sessions', [])
                stats.setdefault('total_games', 0)
            self.cached_stats = stats

        s = self.cached_stats
        font_h = self.font_small   # header
        font_v = self.font_small   # value

        # ── Panel 1: Training Data ──
        p1x, py, pw, ph = 50, 130, 280, 170
        panel1 = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel1.fill((10, 20, 40, 200))
        self.screen.blit(panel1, (p1x, py))
        pygame.draw.rect(self.screen, (100, 150, 255), (p1x, py, pw, ph), 1, border_radius=8)

        h1 = self.font_small.render("📊 TRAINING DATA", True, (150, 200, 255))
        self.screen.blit(h1, (p1x + 10, py + 8))
        pygame.draw.line(self.screen, (80, 100, 180), (p1x + 10, py + 30), (p1x + pw - 10, py + 30))
        rows1 = [
            ("Human mẫu:", f"{s['human_samples']:,}"),
            ("AI mẫu:",     f"{s['ai_samples']:,}"),
            ("Tổng:",       f"{s['human_samples'] + s['ai_samples']:,}"),
        ]
        for i, (k, v) in enumerate(rows1):
            ks = font_h.render(k, True, (180, 180, 200))
            vs = font_v.render(v, True, (255, 230, 80))
            self.screen.blit(ks, (p1x + 10, py + 40 + i * 38))
            self.screen.blit(vs, (p1x + pw - 10 - vs.get_width(), py + 40 + i * 38))

        # ── Panel 2: Highscores ──
        sw, sh = self._get_screen_dims()
        p2x = sw // 2 - 130
        panel2 = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel2.fill((10, 30, 20, 200))
        self.screen.blit(panel2, (p2x, py))
        pygame.draw.rect(self.screen, (80, 200, 100), (p2x, py, pw, ph), 1, border_radius=8)

        h2 = self.font_small.render("🏆 HIGH SCORES", True, (150, 255, 180))
        self.screen.blit(h2, (p2x + 10, py + 8))
        pygame.draw.line(self.screen, (60, 160, 80), (p2x + 10, py + 30), (p2x + pw - 10, py + 30))
        rows2 = [
            ("Human:",  f"{s['hs_human']:,}"),
            ("AI:",     f"{s['hs_ai']:,}"),
            ("Best:",   f"{max(s['hs_human'], s['hs_ai']):,}"),
        ]
        for i, (k, v) in enumerate(rows2):
            ks = font_h.render(k, True, (180, 200, 180))
            vs = font_v.render(v, True, (255, 230, 80))
            self.screen.blit(ks, (p2x + 10, py + 40 + i * 38))
            self.screen.blit(vs, (p2x + pw - 10 - vs.get_width(), py + 40 + i * 38))

        # ── Panel 3: Sessions ──
        p3x = sw - pw - 50
        panel3 = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel3.fill((30, 15, 40, 200))
        self.screen.blit(panel3, (p3x, py))
        pygame.draw.rect(self.screen, (200, 100, 255), (p3x, py, pw, ph), 1, border_radius=8)

        h3 = self.font_small.render(f"🎮 SESSIONS ({s['total_games']})", True, (210, 160, 255))
        self.screen.blit(h3, (p3x + 10, py + 8))
        pygame.draw.line(self.screen, (150, 80, 200), (p3x + 10, py + 30), (p3x + pw - 10, py + 30))
        sessions = s.get('sessions', [])
        if sessions:
            for i, row in enumerate(sessions[:3]):
                mode_v = str(row[0]).upper()
                total_v = str(row[1])
                avg_v = f"{float(row[2]):.1f}"
                label = font_h.render(f"{mode_v}: {total_v} ván  avg {avg_v}", True, (200, 180, 220))
                self.screen.blit(label, (p3x + 10, py + 40 + i * 38))
        else:
            no_data = font_h.render("Chưa có dữ liệu", True, (140, 120, 160))
            self.screen.blit(no_data, (p3x + 10, py + 60))

        # ── Bảng top scores theo mode ──
        table_y = 325
        th = self.font_hint.render("── Top Sessions theo Mode ──", True, (180, 180, 200))
        self.screen.blit(th, (sw // 2 - th.get_width() // 2, table_y))

        col_labels = ["Mode", "Ván", "Avg Score", "Best"]
        col_xs = [120, 320, 500, 680]
        for ci, (lbl, cx) in enumerate(zip(col_labels, col_xs)):
            ls = self.font_hint.render(lbl, True, (200, 200, 255))
            self.screen.blit(ls, (cx, table_y + 22))

        for ri, row in enumerate(sessions[:5]):
            ry = table_y + 44 + ri * 26
            vals = [str(row[0]), str(row[1]), f"{float(row[2]):.0f}", str(row[3])]
            bg_col = (25, 25, 45, 180) if ri % 2 == 0 else (35, 35, 60, 180)
            bg = pygame.Surface((sw - 200, 24), pygame.SRCALPHA)
            bg.fill(bg_col)
            self.screen.blit(bg, (100, ry))
            for ci, (v, cx) in enumerate(zip(vals, col_xs)):
                c = (255, 230, 80) if ci == 3 else (220, 220, 240)
                vs = self.font_hint.render(v, True, c)
                self.screen.blit(vs, (cx, ry + 2))

        # Back button
        back_rect = pygame.Rect(0, 0, 150, 42)
        # Back button
        sw, sh = self._get_screen_dims()
        back_rect.center = (sw // 2, sh - 30)
        self.draw_button("← BACK", back_rect, self.selected == 0)
        self.button_rects = [back_rect]

        pygame.display.flip()

    def draw(self):
        self.draw_background()
        
        if self.current_menu == MENU_SETTINGS:
            self.draw_settings_menu()
            return
        elif self.current_menu == MENU_STATS:
            self.draw_stats_menu()
            return
        elif self.current_menu == MENU_ACHIEVEMENTS:
            self.draw_achievements_menu()
            return
        elif self.current_menu == MENU_TRAIN_AI:
            self.draw_train_ai_menu()
            return

        # Main menu
        self.draw_title_with_shadow("DINO RACER", 100)

        mouse_pos = pygame.mouse.get_pos()

        for i, (item, rect) in enumerate(zip(self.main_items, self.button_rects)):
            is_hovered = rect.collidepoint(mouse_pos)
            if is_hovered: self.selected = i
            self.draw_button(item, rect, i == self.selected)

        # Version info
        sw, sh = self._get_screen_dims()
        hint = self.font_hint.render("v1.0 - Use Arrows + Enter or Mouse Click", True, (180, 180, 180))
        self.screen.blit(hint, (10, sh - 25))

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
            5: ('skin_dino', ['dino', 'dino2', 'dino3']),
        }

        if index in toggles:
            key, toggle_func = toggles[index]
            setattr(settings, key, toggle_func(settings))
        elif index in cycles:
            key, values = cycles[index]
            current = getattr(settings, key)
            idx = values.index(current) if current in values else 0
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
                
                if self.current_menu == MENU_ACHIEVEMENTS:
                    if event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                        self.current_menu = MENU_MAIN
                        self.selected = 0
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mouse_pos = pygame.mouse.get_pos()
                        for rect in self.button_rects:
                            if rect.collidepoint(mouse_pos):
                                self.current_menu = MENU_MAIN
                                self.selected = 0
                    continue

                if self.current_menu == MENU_TRAIN_AI:
                    train_items = ["NEAT Training", "Supervised Training", "Back"]
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        mouse_pos = pygame.mouse.get_pos()
                        for i, rect in enumerate(self.button_rects):
                            if rect.collidepoint(mouse_pos):
                                if train_items[i] == "Back":
                                    self.current_menu = MENU_MAIN
                                    self.selected = 0
                                else:
                                    return train_items[i]
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.current_menu = MENU_MAIN
                            self.selected = 0
                        elif event.key == pygame.K_RETURN:
                            if self.selected < len(train_items) - 1:
                                return train_items[self.selected]
                            else:
                                self.current_menu = MENU_MAIN
                                self.selected = 0
                        elif event.key == pygame.K_UP:
                            self.selected = (self.selected - 1) % len(train_items)
                        elif event.key == pygame.K_DOWN:
                            self.selected = (self.selected + 1) % len(train_items)
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
                                    self.cached_stats = None
                                elif choice == "Achievements":
                                    self.current_menu = MENU_ACHIEVEMENTS
                                    self.selected = 0
                                elif choice == "Train AI":
                                    self.current_menu = MENU_TRAIN_AI
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
                            self.cached_stats = None
                        elif choice == "Achievements":
                            self.current_menu = MENU_ACHIEVEMENTS
                            self.selected = 0
                        elif choice == "Train AI":
                            self.current_menu = MENU_TRAIN_AI
                            self.selected = 0
                        else:
                            return choice
