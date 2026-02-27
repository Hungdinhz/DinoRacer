"""
Endless Mode - Chạy càng xa càng tốt, không có game over do thời gian
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
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound
from src.data_collector import get_collector

SKY_TOP = (100, 180, 230)
SKY_BOT = (255, 210, 120)
GROUND_COL = (160, 120, 60)
GROUND_LINE = (120, 85, 35)


class EndlessGame:
    """Chế độ Endless - chạy càng xa càng tốt"""
    
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        
        self.font_title = pygame.font.SysFont('Arial', 60, bold=True)
        self.font_hud = pygame.font.SysFont('Arial', 28, bold=True)
        self.font_small = pygame.font.SysFont('Arial', 20)
        
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
        
        self.collect_data = True
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
        margin = 8
        shrunk = dino_rect.inflate(-margin * 2, -margin * 2)
        for obs in self.obstacles:
            if shrunk.colliderect(obs.get_rect().inflate(-margin, -margin)):
                return True
        return False
    
    def update(self, keys=None):
        if self.game_over:
            return
        
        # Handle input
        if keys:
            if keys.get(pygame.K_SPACE) or keys.get(pygame.K_UP):
                self.dino.jump()
            if keys.get(pygame.K_DOWN):
                self.dino.duck(True)
        
        self.dino.update()
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
        
        # Increase speed
        self.game_speed = OBSTACLE_SPEED_MIN + (self.score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
        self.game_speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
        
        # Collect data
        if self.collect_data:
            self.frame_count += 1
            if self.frame_count % 10 == 0:
                action = (1 if keys and (keys.get(pygame.K_SPACE) or keys.get(pygame.K_UP)) else 0,
                         1 if keys and keys.get(pygame.K_DOWN) else 0)
                self.collector.record_sample(
                    self.dino, self.obstacles, self.game_speed,
                    action, source="human", score=self.score
                )
        
        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
            
            # Save highscore
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(human=self.score)
    
    def draw_background(self):
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))
        
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
        self.screen.blit(hi_text, (SCREEN_WIDTH - 200, 20))
        
        mode_text = self.font_small.render("ENDLESS MODE", True, (200, 200, 200))
        self.screen.blit(mode_text, (SCREEN_WIDTH // 2 - mode_text.get_width() // 2, 20))
    
    def _draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        pw, ph = 400, 280
        px = SCREEN_WIDTH // 2 - pw // 2
        py = SCREEN_HEIGHT // 2 - ph // 2
        
        pygame.draw.rect(self.screen, (20, 20, 30), (px, py, pw, ph), border_radius=15)
        pygame.draw.rect(self.screen, (255, 80, 80), (px, py, pw, ph), 3, border_radius=15)
        
        title = self.font_title.render("GAME OVER", True, (255, 80, 80))
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
            
            self.update(keys if not self.game_over else None)
        
        return self.score


def run_endless(screen):
    """Chạy chế độ Endless"""
    game = EndlessGame(screen)
    return game.run()
