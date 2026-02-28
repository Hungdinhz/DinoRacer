"""
Endless Mode - Chạy càng xa càng tốt, không có game over do thời gian
"""
import pygame
import random
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
    COLLISION_MARGIN, COMBO_MAX_MULTIPLIER, COMBO_OBSTACLES_PER_LEVEL,
    MILESTONE_STEP, MILESTANE_BANNER_DURATION,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound
from src.data_collector import get_collector
from src.utils import get_cached_font, get_gradient_bg

SKY_TOP = (100, 180, 230)
SKY_BOT = (255, 210, 120)
GROUND_COL = (160, 120, 60)
GROUND_LINE = (120, 85, 35)


def _get_endless_bg():
    """Lấy gradient background cho endless mode."""
    return get_gradient_bg(SCREEN_WIDTH, SCREEN_HEIGHT, 0, SKY_TOP, SKY_BOT)


class EndlessGame:
    """Chế độ Endless - chạy càng xa càng tốt"""
    
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()

        # Sử dụng cached fonts thay vì tạo mới
        self.font_title = get_cached_font('Arial', 60, bold=True)
        self.font_hud = get_cached_font('Arial', 28, bold=True)
        self.font_small = get_cached_font('Arial', 20)

        self.highscore = load_highscore()[0]

        self.reset()
    
    def reset(self):
        self.dino = Dino()
        self.obstacles = []
        self.score = 0
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0
        
        self.game_over = False
        self.start_ticks = pygame.time.get_ticks()

        # Combo system
        self.combo_count = 0       # số obstacle vượt liên tiếp
        self.combo_mult = 1        # hệ số nhân điểm (1x, 2x, 3x, 4x)
        # Milestone banner
        self.milestone_timer = 0   # số frame còn lại của banner
        self.milestone_text = ""
        self.last_milestone = 0    # mốc milestone gần nhất đã hiện

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
        # Sử dụng margin từ settings
        margin = COLLISION_MARGIN
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)
        for obs in self.obstacles:
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                return True
        return False
    
    def update(self, keys=None, jump_held=False):
        if self.game_over:
            return

        # Handle input
        if keys is not None:
            if keys[pygame.K_SPACE] or keys[pygame.K_UP]:
                self.dino.jump_press()
                jump_held = True
            if keys[pygame.K_DOWN]:
                self.dino.duck(True)
            else:
                self.dino.duck(False)

        self.dino.update(jump_held=jump_held)
        self.spawn_obstacle()
        
        # Update obstacles
        for obs in self.obstacles:
            obs.update()
            if obs.x < self.dino.x and not obs.passed:
                obs.passed = True
                self.combo_count += 1
                # Combo multiplier: mỗi 10 obstacle liên tiếp tăng 1 bậc, tối đa 4x
                self.combo_mult = min(1 + self.combo_count // COMBO_OBSTACLES_PER_LEVEL, COMBO_MAX_MULTIPLIER)
                self.score += self.combo_mult
        
        self.obstacles = [o for o in self.obstacles if not o.is_off_screen()]
        if self.obstacles:
            self.last_obstacle_x = max(o.x for o in self.obstacles)

        # Milestone banner
        milestone_step = MILESTONE_STEP
        current_milestone = (self.score // milestone_step) * milestone_step
        if current_milestone > self.last_milestone and current_milestone > 0:
            self.last_milestone = current_milestone
            self.milestone_text = f"{current_milestone} 🎯 PASSED!"
            self.milestone_timer = MILESTANE_BANNER_DURATION
        if self.milestone_timer > 0:
            self.milestone_timer -= 1

        # Increase speed
        self.game_speed = OBSTACLE_SPEED_MIN + (self.score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
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
            self.combo_count = 0
            self.combo_mult = 1

            # Lưu highscore
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(human=self.score)

            # Lưu game session vào DB
            try:
                from src.database_handler import save_game_session, save_highscore_db
                elapsed = (pygame.time.get_ticks() - self.start_ticks) // 1000
                save_game_session('endless', 'human', self.score, game_duration=elapsed, end_reason='collision')
                save_highscore_db('human', self.score, 'endless')
            except Exception:
                pass

    def draw_background(self):
        # Sử dụng cached gradient background
        self.screen.blit(_get_endless_bg(), (0, 0))

        pygame.draw.rect(self.screen, GROUND_COL, (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
        pygame.draw.line(self.screen, GROUND_LINE, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
    
    def draw(self):
        self.draw_background()
        
        self.dino.draw(self.screen)
        
        for obs in self.obstacles:
            obs.draw(self.screen)
        
        self._draw_hud()
        
        if self.game_over:
            self._draw_game_over()
        
        pygame.display.flip()
    
    def _draw_hud(self):
        score_text = self.font_hud.render(f"SCORE: {self.score:05d}", True, (255, 230, 80))
        self.screen.blit(score_text, (20, 20))

        hi_text = self.font_hud.render(f"HI: {self.highscore:05d}", True, (200, 200, 200))
        self.screen.blit(hi_text, (SCREEN_WIDTH - 210, 20))

        mode_text = self.font_small.render("ENDLESS MODE", True, (200, 200, 200))
        self.screen.blit(mode_text, (SCREEN_WIDTH // 2 - mode_text.get_width() // 2, 20))

        # Combo indicator
        if self.combo_mult > 1:
            combo_color = [
                (255, 200, 50),   # 2x - vàng
                (255, 120, 30),   # 3x - cam
                (255, 50,  50),   # 4x - đỏ
            ][min(self.combo_mult - 2, 2)]
            combo_surf = self.font_hud.render(f"COMBO x{self.combo_mult}!", True, combo_color)
            self.screen.blit(combo_surf, (20, 55))

        # Milestone banner
        if self.milestone_timer > 0:
            fade = min(1.0, self.milestone_timer / 20)
            a = int(255 * fade)
            bw, bh = 400, 60
            bx = SCREEN_WIDTH // 2 - bw // 2
            by = SCREEN_HEIGHT // 2 - 100
            banner = pygame.Surface((bw, bh), pygame.SRCALPHA)
            banner.fill((0, 0, 0, int(180 * fade)))
            self.screen.blit(banner, (bx, by))
            pygame.draw.rect(self.screen, (255, 200, 50), (bx, by, bw, bh), 2, border_radius=8)
            ms = self.font_hud.render(self.milestone_text, True, (255, 230, 80))
            self.screen.blit(ms, ms.get_rect(center=(SCREEN_WIDTH // 2, by + bh // 2)))
    
    def _draw_game_over(self):
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
        
        score_value = self.font_hud.render(f"{self.score:05d}", True, (255, 230, 80))
        self.screen.blit(score_value, score_value.get_rect(center=(SCREEN_WIDTH // 2, py + 140)))
        
        if self.score >= self.highscore:
            new_hi = self.font_small.render("NEW HIGH SCORE!", True, (255, 200, 50))
            self.screen.blit(new_hi, new_hi.get_rect(center=(SCREEN_WIDTH // 2, py + 170)))
        
        hint = self.font_small.render("Press R to Restart  |  ESC for Menu", True, (200, 200, 200))
        self.screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, py + 230)))
    
    def run(self):
        running = True

        while running:
            self.draw()
            self.clock.tick(FPS)

            keys = pygame.key.get_pressed()
            jump_held = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.collect_data:
                            self.collector.save_session_data()
                        running = False
                    elif event.key == pygame.K_r and self.game_over:
                        self.reset()
                    elif event.key in (pygame.K_SPACE, pygame.K_UP):
                        jump_held = True

                if event.type == pygame.KEYUP:
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        self.dino.jump_release()
                    if event.key == pygame.K_DOWN:
                        self.dino.duck(False)

            if not self.game_over:
                self.update(keys, jump_held=jump_held)

        return self.score


def run_endless(screen):
    """Chạy chế độ Endless"""
    game = EndlessGame(screen)
    return game.run()
