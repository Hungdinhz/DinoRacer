"""
Time Attack Mode - Vượt qua nhiều obstacle trong thời gian giới hạn
"""
import pygame
import random
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.assets_loader import play_sound
from src.data_collector import get_collector

# ==================== GLOBAL CACHES ====================
# Pre-create gradient background surface
_gradient_bg_surface = None


def _get_gradient_bg():
    """Cache gradient background surface."""
    global _gradient_bg_surface
    if _gradient_bg_surface is None:
        _gradient_bg_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        SKY_TOP = (100, 180, 230)
        SKY_BOT = (255, 210, 120)
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
            pygame.draw.line(_gradient_bg_surface, (r, g, b), (0, y), (SCREEN_WIDTH, y))
    return _gradient_bg_surface


# Font cache
_time_attack_font_cache = {}


def _get_time_attack_font(name, size, bold=False):
    """Lấy font từ cache."""
    key = (name, size, bold)
    if key not in _time_attack_font_cache:
        _time_attack_font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
    return _time_attack_font_cache[key]


SKY_TOP = (100, 180, 230)
SKY_BOT = (255, 210, 120)
GROUND_COL = (160, 120, 60)
GROUND_LINE = (120, 85, 35)


class TimeAttackGame:
    """Chế độ Time Attack - vượt obstacle trong thời gian giới hạn"""
    
    TIME_LIMITS = {
        'easy': 120,    # 2 phút
        'normal': 90,   # 1.5 phút
        'hard': 60,     # 1 phút
    }
    
    def __init__(self, screen, difficulty='normal'):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.difficulty = difficulty
        self.time_limit = self.TIME_LIMITS.get(difficulty, 90)  # seconds

        # Sử dụng cached fonts thay vì tạo mới
        self.font_title = _get_time_attack_font('Arial', 60, bold=True)
        self.font_hud = _get_time_attack_font('Arial', 28, bold=True)
        self.font_small = _get_time_attack_font('Arial', 20)

        self.reset()
    
    def reset(self):
        self.dino = Dino()
        self.obstacles = []
        self.score = 0  # Số obstacle đã vượt qua
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        
        self.game_over = False
        self.time_remaining = self.time_limit
        self.start_ticks = pygame.time.get_ticks()
        
        self.collect_data = False  # Disabled by default to avoid lag
        self.collector = get_collector()
        self.frame_count = 0
    
    def spawn_obstacle(self):
        if self.last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(SCREEN_WIDTH + 50, speed)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x
    
    def check_collision(self):
        dino_rect = self.dino.get_rect()
        # Giảm margin từ 8 xuống 2 để tránh collision quá nhạy khi nhảy qua
        margin = 2
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)
        for obs in self.obstacles:
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                return True
        return False
    
    def update(self, keys=None):
        if self.game_over:
            return
        
        # Update time
        elapsed = (pygame.time.get_ticks() - self.start_ticks) // 1000
        self.time_remaining = max(0, self.time_limit - elapsed)
        
        if self.time_remaining <= 0:
            self.game_over = True
            play_sound("gameover")
            return
        
        # Handle input
        if keys is not None:
            if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                self.dino.jump()
            if keys[pygame.K_DOWN]:
                self.dino.duck(True)
        
        self.dino.update(jump_held=False)
        self.spawn_obstacle()
        
        # Update obstacles
        for obs in self.obstacles:
            obs.update()
            if obs.x < self.dino.x and not obs.passed:
                obs.passed = True
                self.score += 1
        
        self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
        if self.obstacles:
            self.last_obstacle_x = max(o.x for o in self.obstacles)
        
        # Increase speed over time
        self.game_speed = OBSTACLE_SPEED_MIN + (self.score // 10) * SPEED_INCREASE_AMOUNT
        self.game_speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
        
        # Collect data
        if self.collect_data:
            self.frame_count += 1
            if self.frame_count % 10 == 0:
                action = (1 if keys and (keys[pygame.K_SPACE] or keys[pygame.K_UP]) else 0,
                         1 if keys and keys[pygame.K_DOWN] else 0)
                self.collector.record_sample(
                    self.dino, self.obstacles, self.game_speed,
                    action, source="human", score=self.score
                )
        
        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
    
    def draw_background(self):
        # Sử dụng cached gradient background
        self.screen.blit(_get_gradient_bg(), (0, 0))

        # Ground
        pygame.draw.rect(self.screen, GROUND_COL, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
        pygame.draw.line(self.screen, GROUND_LINE, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
    
    def draw(self):
        self.draw_background()
        
        # Draw dino
        self.dino.draw(self.screen)
        
        # Draw obstacles
        for obs in self.obstacles:
            obs.draw(self.screen)
        
        # Draw HUD
        self._draw_hud()
        
        if self.game_over:
            self._draw_game_over()
        
        pygame.display.flip()
    
    def _draw_hud(self):
        # Timer
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        time_text = self.font_hud.render(f"TIME: {minutes:02d}:{seconds:02d}", True, (255, 255, 255))
        
        # Timer color based on time left
        if self.time_remaining <= 10:
            time_text = self.font_hud.render(f"TIME: {minutes:02d}:{seconds:02d}", True, (255, 50, 50))
        elif self.time_remaining <= 30:
            time_text = self.font_hud.render(f"TIME: {minutes:02d}:{seconds:02d}", True, (255, 200, 50))
        
        self.screen.blit(time_text, (20, 20))
        
        # Score
        score_text = self.font_hud.render(f"SCORE: {self.score}", True, (255, 230, 80))
        self.screen.blit(score_text, (SCREEN_WIDTH - 200, 20))
        
        # Mode label
        mode_text = self.font_small.render(f"TIME ATTACK - {self.difficulty.upper()}", True, (200, 200, 200))
        self.screen.blit(mode_text, (SCREEN_WIDTH // 2 - mode_text.get_width() // 2, 20))
    
    def _draw_game_over(self):
        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Panel
        pw, ph = 400, 250
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        
        pygame.draw.rect(self.screen, (20, 20, 30), (px, py, pw, ph), border_radius=15)
        pygame.draw.rect(self.screen, (255, 200, 50), (px, py, pw, ph), 3, border_radius=15)
        
        # Title
        title = self.font_title.render("TIME'S UP!", True, (255, 200, 50))
        self.screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, py + 50)))
        
        # Score
        score_label = self.font_hud.render(f"Obstacles Passed: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_label, score_label.get_rect(center=(SCREEN_WIDTH // 2, py + 120)))
        
        # Instructions
        hint = self.font_small.render("Press R to Restart  |  ESC for Menu", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, py + 200)))
    
    def run(self):
        """Chạy game Time Attack"""
        running = True
        
        while running:
            self.draw()
            self.clock.tick(FPS)
            
            keys = pygame.key.get_pressed()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        # Save collected data before exit
                        if self.collect_data:
                            self.collector.save_session_data()
                        running = False
                    elif event.key == pygame.K_r and self.game_over:
                        self.reset()
                
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN:
                        self.dino.duck(False)
            
            self.update(keys if not self.game_over else None)
        
        return self.score


def run_time_attack(screen, difficulty='normal'):
    """Chạy chế độ Time Attack"""
    game = TimeAttackGame(screen, difficulty)
    return game.run()
