"""
Game Manager - Quản lý vòng lặp game, tính điểm, va chạm
"""
import pygame
import random
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, GROUND_COLOR, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
    TEXT_COLOR
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound, CLOUD_POSITIONS
from src.ui import UILayer

class GameManager:
    def __init__(self, screen, is_ai_mode=False):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.dino = Dino()
        self.obstacles = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0  # Cho phép spawn obstacle đầu tiên ngay
        self.running = True
        self.game_over = False
        self.is_ai_mode = is_ai_mode
        self.highscore_human, self.highscore_ai = load_highscore()

        # Khoi tao UI
        self.ui = UILayer(screen)

        self.reset()  # Khởi tạo game state ban đầu

    def reset(self):
        """Reset game về trạng thái ban đầu"""
        self.dino = Dino()
        self.obstacles = []
        self.score = INITIAL_SCORE
        self.game_speed = OBSTACLE_SPEED_MIN
        self.last_obstacle_x = 0  # Cho phép spawn obstacle đầu tiên ngay
        self.game_over = False
        self.paused = False
    
    def toggle_pause(self):
        """Bật/tắt chế độ pause"""
        self.paused = not self.paused

    def spawn_obstacle(self):
        """Tạo chướng ngại vật mới nếu đủ khoảng cách"""
        if self.last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
            speed = min(self.game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(SCREEN_WIDTH + 50, speed)
            self.obstacles.append(obs)
            self.last_obstacle_x = obs.x

    def check_collision(self):
        """Kiểm tra va chạm giữa dino và chướng ngại vật"""
        dino_rect = self.dino.get_rect()
        for obs in self.obstacles:
            if dino_rect.colliderect(obs.get_rect()):
                return True
        return False

    def update(self, action=None, speed_mult=1.0):
        """
        Cập nhật game state.
        action: None (human), hoặc (jump, duck, nothing) từ AI
        """
        if self.paused or self.game_over:
            return

        # Xử lý action từ AI hoặc human
        if action is not None:
            jump, duck, _ = action
            if jump > 0.5:
                self.dino.jump()
            self.dino.duck(duck > 0.5)

        self.dino.update()
        self.spawn_obstacle()

        prev_score = self.score
        for obs in self.obstacles:
            # Lưu lại vị trí cũ trước khi update
            old_x = obs.x
            obs.update()

            # Tính toán lại quãng đường di chuyển thực tế với hệ số A/D
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

        # Tăng tốc theo điểm
        self.game_speed = OBSTACLE_SPEED_MIN + (self.score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
        self.game_speed = min(self.game_speed, OBSTACLE_SPEED_MAX)

        if self.check_collision():
            self.game_over = True
            play_sound("gameover")
            h_cur = self.highscore_ai if self.is_ai_mode else self.highscore_human
            if self.score > h_cur:
                if self.is_ai_mode:
                    save_highscore(ai=self.score)
                else:
                    save_highscore(human=self.score)

    def get_state(self):
        """
        Trả về state cho AI: [distance, obstacle_type, speed, dino_y_norm, is_jumping]
        """
        # Tìm chướng ngại vật gần nhất phía trước
        nearest = None
        min_dist = float('inf')
        for obs in self.obstacles:
            if obs.x > self.dino.x:
                dist = obs.x - self.dino.x
                if dist < min_dist:
                    min_dist = dist
                    nearest = obs

        if nearest is None:
            return [1.0, 0.5, 0.0, 0.0, 0.0]  # Normalized defaults

        from src.obstacle import Cactus
        dist_norm = min(min_dist / 500, 1.0)
        obs_type = 0.0 if isinstance(nearest, Cactus) else 1.0
        speed_norm = (self.game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
        dino_y_norm = (GROUND_Y - self.dino.y) / 100  # Độ cao chuẩn hóa
        is_jump = 1.0 if self.dino.is_jumping else 0.0

        return [dist_norm, obs_type, speed_norm, min(dino_y_norm, 1.0), is_jump]

    def draw(self):
        """Vẽ toàn bộ game"""
        self.screen.fill(BG_COLOR)
        # Mây
        for cx, cy in CLOUD_POSITIONS:
            pygame.draw.ellipse(self.screen, (220, 220, 220), (cx, cy, 60, 30))
            pygame.draw.ellipse(self.screen, (230, 230, 230), (cx + 20, cy - 5, 50, 25))
        # Mặt đất
        pygame.draw.line(self.screen, GROUND_COLOR, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)

        self.dino.draw(self.screen)
        for obs in self.obstacles:
            obs.draw(self.screen)

        # Ve UI
        # Điểm số và High Score
        h_score = self.highscore_ai if self.is_ai_mode else self.highscore_human
        self.ui.draw_score(self.score, h_score)

        # Nút Pause
        self.ui.draw_pause_icon(self.paused)

        # Menu Pause hoặc Game Over
        if self.paused:
            self.ui.draw_pause_menu()
        if self.game_over:
            self.ui.draw_game_over()

        pygame.display.flip()

    def run_human_mode(self):
        """Chạy game với người chơi (Space=nhảy, Down=cúi)"""
        pygame.init()
        running = True
        while running:
            # --- KIỂM TRA PHÍM GIỮ CHO A VÀ D ---
            keys = pygame.key.get_pressed()
            speed_mult = 1.0  # Tốc độ bình thường
            
            if not self.paused and not self.game_over:
                if keys[pygame.K_a]:
                    speed_mult = 0.5  # Bấm A: Trôi chậm lại 50%
                elif keys[pygame.K_d]:
                    speed_mult = 1.5  # Bấm D: Trôi nhanh lên 180%
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    # using W A S D de dieu khien dino
                    if event.key == pygame.K_w and not self.paused:
                        self.dino.jump()
                    if event.key == pygame.K_s and not self.paused:
                        self.dino.duck(True)
                    # if event.key == pygame.K_d and not self.paused:
                    #     self.toggle_pause()
                    # if event.key == pygame.K_a and not self.paused:
                    #     self.toggle_pause()
                    if event.key == pygame.K_p:
                        self.toggle_pause()
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.dino.duck(False)
                if event.type == pygame.KEYDOWN and self.game_over and event.key == pygame.K_r:
                    self.reset()
                # Xử lý Click chuột
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # Chuột trái
                        if self.paused:
                        # Hỏi UI xem user bấm vào nút nào
                            action = self.ui.handle_pause_menu_click(event.pos)
                            if action == "Resume": self.toggle_pause()
                            elif action == "Restart": self.reset()
                            elif action == "Quit": return 
                        else:
                            if self.ui.is_pause_button_clicked(event.pos):
                                self.toggle_pause()

            self.update(speed_mult=speed_mult)
            self.draw()
            self.clock.tick(FPS)

        #pygame.quit()
        # Hàm này chỉ cần kết thúc (return) để quay về main.py, đừng tắt Pygame.
