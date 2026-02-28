"""
Game Manager - Quản lý vòng lặp game, tính điểm, va chạm
"""
import pygame
import random
import math
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
    COLLISION_MARGIN,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound, load_image, CLOUD_POSITIONS
from src.achievements import check_achievements
from src.menu import settings as game_settings
from src.utils import (
    get_cached_font, get_gradient_bg, clear_gradient_cache,
    get_hud_bg_surface, PARTICLE_COLORS, GO_RED, GO_GREEN,
)

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


class Particle:
    __slots__ = ('x', 'y', 'vx', 'vy', 'life', 'max_life', 'size', 'color')

    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1, 4)
        self.life = random.randint(20, 45)
        self.max_life = self.life
        self.size = random.randint(4, 10)
        self.color = random.choice(_PARTICLE_COLORS)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.life -= 1

    def draw(self, screen):
        alpha = int(255 * self.life / self.max_life)
        if alpha <= 0:
            return
        r, g, b = self.color
        # Reuse surface if possible - create small surface only when needed
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (r, g, b, alpha), (self.size, self.size), self.size)
        screen.blit(s, (int(self.x) - self.size, int(self.y) - self.size))


class Cloud:
    __slots__ = ('x', 'y', 'speed', 'w', 'h')

    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.randint(SCREEN_WIDTH, SCREEN_WIDTH + 400)
        self.y = y if y is not None else random.randint(20, 150)
        self.speed = random.uniform(0.4, 1.2)
        self.w = random.randint(90, 160)
        self.h = random.randint(28, 50)

    def update(self):
        self.x -= self.speed
        if self.x < -(self.w + 20):
            self.x = SCREEN_WIDTH + random.randint(50, 300)
            self.y = random.randint(20, 150)
            self.w = random.randint(90, 160)
            self.h = random.randint(28, 50)

    def draw(self, screen):
        pygame.draw.ellipse(screen, CLOUD_COL, (self.x, self.y, self.w, self.h))
        pygame.draw.ellipse(screen, CLOUD_COL,
                            (self.x + self.w // 5, self.y - self.h // 2,
                             self.w * 3 // 5, self.h))
        pygame.draw.ellipse(screen, CLOUD_COL,
                            (self.x + self.w // 2, self.y - self.h // 3,
                             self.w // 2, self.h * 4 // 5))


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


class GameManager:
    def __init__(self, screen, is_ai_mode=False):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.is_ai_mode = is_ai_mode
        self.highscore_human, self.highscore_ai = load_highscore()

        # Sử dụng cached fonts thay vì tạo mới
        self.font_hud   = get_cached_font('Arial', 24, bold=True)
        self.font_large = get_cached_font('impact', 68, bold=True)
        self.font_med   = get_cached_font('Arial', 30, bold=True)
        self.font_small = get_cached_font('Arial', 20)
        self.font_speed = get_cached_font('Arial', 18)

        self.pause_btn = pygame.Rect(SCREEN_WIDTH - 70, 10, 50, 50)
        self.clouds = [
            Cloud(random.randint(0, SCREEN_WIDTH), random.randint(20, 150))
            for _ in range(7)
        ]
        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []
        self.go_flash_timer = 0
        self.bg_index = 1

        # Cache dino rect để tránh tạo mới mỗi frame
        self._dino_rect_cache = None

        # Input smoothing
        self._jump_pressed = False
        self._jump_released = True
        self._last_jump_state = False

        self.reset()

    def reset(self):
        skin = getattr(game_settings, 'skin_dino', 'dino') if not self.is_ai_mode else 'ai_dino'
        self.dino = Dino(folder=skin)
        self.obstacles = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        self.game_over = False
        self.paused = False
        self.ground_offset = 0
        self.bg_offset = 0
        self.particles = []
        self.go_flash_timer = 0
        self.bg_index = 1
        # Achievement popup state
        self.pending_achievements = []
        self.ach_popup_timer = 0
        self.ach_popup_item = None
        self._start_ticks = pygame.time.get_ticks()

        # Cache giá trị tính toán thường dùng
        self._half_screen = SCREEN_WIDTH // 2

    def toggle_pause(self):
        self.paused = not self.paused

    def spawn_obstacle(self):
        if self.last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(SCREEN_WIDTH + 50, speed)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x

    def check_collision(self):
        # Early exit nếu không có obstacle
        if not self.obstacles:
            return False

        # Tối ưu: lấy rect một lần, tính margin một lần
        dino_rect = self.dino.get_rect()
        # Sử dụng margin từ settings
        margin = COLLISION_MARGIN
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)

        # Early exit: kiểm tra khoảng cách trước
        dino_x = dino_rect.x
        for obs in self.obstacles:
            # Bỏ qua obstacle ở xa
            if obs.x > dino_x + 100:
                continue
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                return True
        return False

    def update(self, action=None, speed_mult=1.0, jump_held=False):
        """
        Cập nhật game state.
        action    : None (human), hoặc (jump, duck, nothing) từ AI
        speed_mult: hệ số tốc độ obstacle (A=0.5, bình thường=1.0, D=1.5)
        jump_held : True nếu phím nhảy đang được giữ (variable jump height)
        """
        if self.paused:
            return
        if self.game_over:
            self.particles = [p for p in self.particles if p.life > 0]
            for p in self.particles:
                p.update()
            self.go_flash_timer += 1
            return

        # Xử lý input AI
        if action is not None:
            jump, duck, _ = action
            if jump > 0.5:
                self.dino.jump()
            self.dino.duck(duck > 0.5)

        self.dino.update(jump_held=jump_held)
        self.spawn_obstacle()

        self.ground_offset = (self.ground_offset + self.game_speed * speed_mult) % 64
        self.bg_offset = (self.bg_offset + self.game_speed * speed_mult * 0.15) % SCREEN_WIDTH

        prev_score = self.score
        for obs in self.obstacles:
            old_x = obs.x
            actual_speed = obs.speed * speed_mult
            obs.x = old_x - actual_speed
            if obs.x < self.dino.x and not obs.passed:
                obs.passed = True
                self.score += 1
        if self.score // 100 > prev_score // 100 and self.score > 0:
            play_sound("score")

        self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
        if self.obstacles:
            self.last_obstacle_x = max(o.x for o in self.obstacles)

        self.game_speed = OBSTACLE_SPEED_MIN + (self.score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
        self.game_speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
        self.bg_index = min(1 + self.score // 50, 5)

        for c in self.clouds:
            c.update()

        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
            rect = self.dino.get_rect()
            for _ in range(40):
                self.particles.append(Particle(rect.centerx, rect.centery))
            h_cur = self.highscore_ai if self.is_ai_mode else self.highscore_human
            if self.score > h_cur:
                if self.is_ai_mode:
                    self.highscore_ai = self.score
                    save_highscore(ai=self.score)
                else:
                    self.highscore_human = self.score
                    save_highscore(human=self.score)
            # Kiểm tra và trigger achievements
            newly = check_achievements(score=self.score, obstacles=self.score)
            self.pending_achievements.extend(newly)

            # Lưu game session vào DB (non-blocking)
            try:
                from src.database_handler import save_game_session, save_highscore_db
                elapsed_ms = pygame.time.get_ticks() - getattr(self, '_start_ticks', pygame.time.get_ticks())
                game_mode = 'ai_pve' if self.is_ai_mode else 'human'
                player_type = 'ai' if self.is_ai_mode else 'human'
                save_game_session(
                    game_mode=game_mode,
                    player_type=player_type,
                    score=self.score,
                    game_duration=elapsed_ms // 1000,
                    end_reason='collision'
                )
                save_highscore_db(player_type, self.score, game_mode)
            except Exception:
                pass  # DB không có thì bỏ qua

        # Tiến trình hiển thị achievement popup
        if self.ach_popup_item is None and self.pending_achievements:
            self.ach_popup_item = self.pending_achievements.pop(0)
            self.ach_popup_timer = 180  # hiện 3 giây (60fps x 3)
        if self.ach_popup_timer > 0:
            self.ach_popup_timer -= 1
            if self.ach_popup_timer == 0:
                self.ach_popup_item = None

    def get_state(self):
        nearest = None
        min_dist = float('inf')
        for obs in self.obstacles:
            if obs.x > self.dino.x:
                dist = obs.x - self.dino.x
                if dist < min_dist:
                    min_dist = dist
                    nearest = obs
        if nearest is None:
            return [1.0, 0.5, 0.0, 0.0, 0.0]
        from src.obstacle import Cactus
        return [
            min(min_dist / 500, 1.0),
            0.0 if isinstance(nearest, Cactus) else 1.0,
            (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN),
            min((GROUND_Y - self.dino.y) / 100, 1.0),
            1.0 if self.dino.is_jumping else 0.0,
        ]

    # ── Draw ──────────────────────────────────────────────────

    def _draw_background(self):
        bg = _get_bg(self.bg_index)
        ox = int(self.bg_offset) % SCREEN_WIDTH
        self.screen.blit(bg, (-ox, 0))
        if ox > 0:
            self.screen.blit(bg, (SCREEN_WIDTH - ox, 0))

    def _draw_ground(self):
        tile_h = SCREEN_HEIGHT - GROUND_Y
        tile_w = 64
        # Sử dụng cached tile
        tile = _get_cached_tile("Tile_01.png", (tile_w, tile_h))
        if tile:
            offset = int(self.ground_offset) % tile_w
            for x in range(-tile_w, SCREEN_WIDTH + tile_w, tile_w):
                self.screen.blit(tile, (x - offset, GROUND_Y))
        else:
            pygame.draw.rect(self.screen, GROUND_COL,
                             (0, GROUND_Y, SCREEN_WIDTH, tile_h))
            pygame.draw.line(self.screen, GROUND_LINE,
                             (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
            for i in range(-1, SCREEN_WIDTH // 40 + 2):
                x = i * 40 - int(self.ground_offset) % 40
                pygame.draw.line(self.screen, GROUND_LINE,
                                 (x, GROUND_Y + 10), (x + 22, GROUND_Y + 10), 1)

    def _draw_hud(self):
        h = max(self.highscore_ai if self.is_ai_mode else self.highscore_human, self.score)

        # Sử dụng cached HUD background
        self.screen.blit(get_hud_bg_surface(), (self._half_screen - 130, 5))

        score_txt = self.font_hud.render(f"SCORE  {self.score:05d}", True, (255, 230, 80))
        hi_txt    = self.font_hud.render(f"HI  {h:05d}", True, (200, 200, 200))
        spd_txt   = self.font_speed.render(f"SPD  {self.game_speed:.1f}", True, (150, 230, 150))
        self.screen.blit(score_txt, (self._half_screen - 118, 12))
        self.screen.blit(hi_txt,    (self._half_screen - 118, 38))
        self.screen.blit(spd_txt,   (self._half_screen + 30,  38))

        # Speed bar
        bar_x, bar_y, bar_w, bar_h = self._half_screen + 30, 14, 90, 10
        ratio = (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
        pygame.draw.rect(self.screen, (50, 50, 50), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
        fill_w = max(1, int(bar_w * ratio))
        bar_color = (int(80 + 175 * ratio), int(200 - 150 * ratio), 50)
        pygame.draw.rect(self.screen, bar_color,
                         (bar_x, bar_y, fill_w, bar_h), border_radius=4)

    def _draw_pause_btn(self):
        mouse_pos = pygame.mouse.get_pos()
        hover = self.pause_btn.collidepoint(mouse_pos)
        color = (180, 180, 180) if hover else (80, 80, 80)
        pygame.draw.rect(self.screen, color, self.pause_btn, border_radius=8)
        pygame.draw.rect(self.screen, (220, 220, 220), self.pause_btn, 2, border_radius=8)
        if self.paused:
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

    def _draw_paused_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 400, 200
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2

        shadow_surf = pygame.Surface((pw, ph), pygame.SRCALPHA)
        shadow_surf.fill((0, 0, 0, 60))
        self.screen.blit(shadow_surf, (px + 6, py + 6))

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 30, 220))
        self.screen.blit(panel, (px, py))

        pygame.draw.rect(self.screen, (100, 150, 200), (px, py, pw, ph), 2, border_radius=12)

        pause_icon = self.font_large.render("⏸", True, (255, 230, 100))
        self.screen.blit(pause_icon, pause_icon.get_rect(center=(SCREEN_WIDTH // 2, py + 55)))

        txt = self.font_large.render("PAUSED", True, (255, 230, 100))
        self.screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH // 2, py + 100)))

        hint = self.font_small.render("Nhấn  P  để tiếp tục", True, (180, 180, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, py + 145)))

        hint2 = self.font_small.render("ESC - Menu chính", True, (120, 120, 150))
        self.screen.blit(hint2, hint2.get_rect(center=(SCREEN_WIDTH // 2, py + 170)))

    def _draw_game_over(self):
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
        r_txt = self.font_med.render("THỬ LẠI", True, GO_GREEN)
        self.screen.blit(r_symbol, r_symbol.get_rect(center=(r_box.x + 30, r_box.centery)))
        self.screen.blit(r_txt, r_txt.get_rect(center=(r_box.x + 100, r_box.centery)))
        r_hint = self.font_small.render("Phím R", True, (150, 180, 150))
        self.screen.blit(r_hint, r_hint.get_rect(center=(r_box.x + 100, r_box.bottom - 8)))

        m_box = pygame.Rect(px + pw - 220, py + 185, 180, 45)
        pygame.draw.rect(self.screen, (60, 60, 120, 150), m_box, border_radius=8)
        pygame.draw.rect(self.screen, (100, 150, 200), m_box, 2, border_radius=8)

        m_symbol = self.font_med.render("☰", True, (180, 180, 255))
        m_txt = self.font_med.render("MENU", True, (180, 180, 255))
        self.screen.blit(m_symbol, m_symbol.get_rect(center=(m_box.x + 30, m_box.centery)))
        self.screen.blit(m_txt, m_txt.get_rect(center=(m_box.x + 100, m_box.centery)))
        m_hint = self.font_small.render("Phím ESC", True, (150, 150, 200))
        self.screen.blit(m_hint, m_hint.get_rect(center=(m_box.x + 100, m_box.bottom - 8)))

    def _draw_achievement_popup(self):
        """Vẽ popup thành tựu mới mở khóa - slide in từ phải sang."""
        if self.ach_popup_item is None:
            return
        # Tính alpha fade-out ở cuối
        t = self.ach_popup_timer
        if t > 150:
            alpha = 255
        else:
            alpha = int(255 * t / 150)

        pw, ph = 300, 70
        margin = 12
        px = SCREEN_WIDTH - pw - margin
        py = margin

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        panel.fill((20, 20, 30, int(220 * alpha / 255)))
        self.screen.blit(panel, (px, py))
        pygame.draw.rect(self.screen, (255, 200, 50), (px, py, pw, ph), 2, border_radius=8)

        icon = self.ach_popup_item.get('icon', '🏆')
        name = self.ach_popup_item.get('name', 'Achievement')

        header = self.font_small.render("✨ THÀNH TỰU MỚI!", True, (255, 200, 50))
        self.screen.blit(header, (px + 8, py + 6))
        name_surf = self.font_small.render(f"{icon} {name}", True, (255, 255, 255))
        self.screen.blit(name_surf, (px + 8, py + 32))

    def draw(self):
        self._draw_background()
        for c in self.clouds:
            c.draw(self.screen)
        self._draw_ground()
        self.dino.draw(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)
        self._draw_hud()
        self._draw_pause_btn()
        if self.paused:
            self._draw_paused_overlay()
        elif self.game_over:
            self._draw_game_over()
        self._draw_achievement_popup()
        pygame.display.flip()

    def run_human_mode(self):
        """
        Chế độ chơi thủ công.
        - SPACE / ↑ : nhảy
        - ↓         : cúi (giữ phím)
        - A         : obstacle chậm lại 50%
        - D         : obstacle nhanh lên 150%
        - P         : pause/resume
        - R         : restart (khi game over)
        - ESC       : về menu (khi game over)
        """
        running = True
        while running:
            # --- Đọc phím giữ để tính speed_mult ---
            keys = pygame.key.get_pressed()
            speed_mult = 1.0
            jump_held = False
            if not self.paused and not self.game_over:
                if keys[pygame.K_a]:
                    speed_mult = 0.5   # A: chậm 50%
                elif keys[pygame.K_d]:
                    speed_mult = 1.5   # D: nhanh 150%

                # Track trạng thái jump key
                jump_held = keys[pygame.K_SPACE] or keys[pygame.K_UP]

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not self.game_over and not self.paused:
                            self.dino.jump_press()
                    if event.key == pygame.K_DOWN:
                        if not self.game_over and not self.paused:
                            self.dino.duck(True)
                    if event.key == pygame.K_p:
                        if not self.game_over:
                            self.toggle_pause()
                    if event.key == pygame.K_r and self.game_over:
                        self.reset()
                    if event.key == pygame.K_ESCAPE and self.game_over:
                        running = False

                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        self.dino.jump_release()
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        self.dino.duck(False)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.pause_btn.collidepoint(event.pos) and not self.game_over:
                        self.toggle_pause()

            # Update với jump_held để hỗ trợ variable jump height
            self.update(speed_mult=speed_mult, jump_held=jump_held)
            self.draw()
            self.clock.tick(FPS)

    def run_pve_mode(self):
        from src.lane_game import LaneGame, LANE_H
        from src.ai_handler import load_genome, _get_inputs_from_lane
        import neat
        genome, config = load_genome()
        net = neat.nn.FeedForwardNetwork.create(genome, config) if genome else None
        ai_lane     = LaneGame('ai_dino', 'AI',       label_color=(200, 150, 255))
        player_lane = LaneGame('dino',    'PLAYER',   label_color=(255, 230, 80))
        div = pygame.Surface((SCREEN_WIDTH, 4)); div.fill((255, 200, 50))
        font_hint = pygame.font.SysFont('Arial', 16)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not player_lane.game_over: player_lane.dino.jump_press()
                    if event.key == pygame.K_DOWN:
                        if not player_lane.game_over: player_lane.dino.duck(True)
                    if event.key == pygame.K_r: ai_lane.reset(); player_lane.reset()
                    if event.key == pygame.K_ESCAPE: running = False
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        player_lane.dino.jump_release()
                    if event.key == pygame.K_DOWN: player_lane.dino.duck(False)
            if net and not ai_lane.game_over:
                ai_lane.update(action=net.activate(_get_inputs_from_lane(ai_lane)))
            else:
                ai_lane.update()
            player_lane.update()
            ai_lane.draw(); player_lane.draw()
            self.screen.blit(ai_lane.surface, (0, 0))
            self.screen.blit(div, (0, LANE_H))
            self.screen.blit(player_lane.surface, (0, LANE_H + 4))
            if ai_lane.game_over or player_lane.game_over:
                hint = font_hint.render('R - Choi lai  |  ESC - Menu', True, (220, 220, 220))
                self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, LANE_H * 2 + 4 - 12)))
            pygame.display.flip(); self.clock.tick(FPS)

    def run_pvp_mode(self):
        from src.lane_game import LaneGame, LANE_H
        p1 = LaneGame('dino',    'PLAYER 1', label_color=(255, 230, 80),   collect_data=True, player_type="human")
        p2 = LaneGame('ai_dino', 'PLAYER 2', label_color=(200, 150, 255),  collect_data=True, player_type="ai")
        div = pygame.Surface((SCREEN_WIDTH, 4)); div.fill((255, 200, 50))
        font_res  = pygame.font.SysFont('Arial', 22, bold=True)
        font_hint = pygame.font.SysFont('Arial', 16)
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        if not p1.game_over: p1.dino.jump_press()
                    if event.key == pygame.K_DOWN:
                        if not p1.game_over: p1.dino.duck(True)
                    if event.key == pygame.K_w:
                        if not p2.game_over: p2.dino.jump_press()
                    if event.key == pygame.K_s:
                        if not p2.game_over: p2.dino.duck(True)
                    if event.key == pygame.K_r: p1.reset(); p2.reset()
                    if event.key == pygame.K_ESCAPE: running = False
                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        p1.dino.jump_release()
                    if event.key in (pygame.K_w):
                        p2.dino.jump_release()
                    if event.key == pygame.K_DOWN: p1.dino.duck(False)
                    if event.key == pygame.K_s: p2.dino.duck(False)
            p1.update(); p2.update()
            p1.draw(); p2.draw()
            self.screen.blit(p1.surface, (0, 0))
            self.screen.blit(div, (0, LANE_H))
            self.screen.blit(p2.surface, (0, LANE_H + 4))
            if p1.game_over and p2.game_over:
                if p1.score > p2.score: msg, col = f'P1 THẮNG! ({p1.score} vs {p2.score})', (255, 230, 80)
                elif p2.score > p1.score: msg, col = f'P2 THẮNG! ({p2.score} vs {p1.score})', (200, 150, 255)
                else: msg, col = f'HÒA! ({p1.score})', (200, 200, 200)
                res = font_res.render(msg, True, col)
                self.screen.blit(res, res.get_rect(center=(SCREEN_WIDTH // 2, LANE_H + 2)))
            if p1.game_over or p2.game_over:
                hint = font_hint.render('R - Chơi lại  |  ESC - Menu', True, (220, 220, 220))
                self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, LANE_H * 2 + 4 - 12)))
            pygame.display.flip(); self.clock.tick(FPS)
