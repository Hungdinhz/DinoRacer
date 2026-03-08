"""
NEAT Visual Training - Chạy toàn bộ population trên 1 màn hình.
Mỗi dino có màu gradient từ xanh (tốt nhất) -> đỏ (tệ nhất).
Hiển thị: generation, số còn sống, fitness tốt nhất, tốc độ game.
"""
import pygame
import neat
import pickle
import os
import random
import math

from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
)
from src.dino import Dino
from src.obstacle import create_obstacle, Cactus
from src.assets_loader import load_image

# ── Màu sắc ───────────────────────────────────────────
SKY_TOP    = (30,  30,  60)
SKY_BOT    = (80,  50, 100)
GROUND_COL = (50,  40,  70)
GROUND_LN  = (80,  60, 110)
DEAD_COL   = (80,  80,  80)
TEXT_COL   = (220, 220, 255)
PANEL_COL  = (10,  10,  30, 200)

_bg_cache   = {}
_tile_cache = {}


def _rank_color(rank, total):
    """Gradient: rank 0 (tốt nhất) = xanh, rank N-1 (tệ nhất) = đỏ."""
    t = rank / max(total - 1, 1)
    r = int(50  + 205 * t)
    g = int(220 - 180 * t)
    b = int(50  +  50 * (1 - t))
    return (r, g, b)


def _get_inputs(dino, obstacles, game_speed, ground_y=GROUND_Y):
    """Lay 8 inputs cho NEAT (matching ai_handler.py)"""
    nearest = None
    second_nearest = None
    min_dist = float('inf')
    second_dist = float('inf')

    for obs in obstacles:
        if obs.x > dino.x:
            dist = obs.x - dino.x
            if dist < min_dist:
                second_dist = min_dist
                second_nearest = nearest
                min_dist = dist
                nearest = obs
            elif dist < second_dist:
                second_dist = dist
                second_nearest = obs

    if nearest is None:
        return [1.0, 0.5, 1.0, 0.0, 0.0, 0.0, 0.0, 0.5]

    # 1. Khoang cach den obstacle gan nhat
    dist1 = min(min_dist / 500, 1.0)

    # 2. Loai obstacle (0 = Cactus, 1 = Bird)
    type1 = 0.0 if isinstance(nearest, Cactus) else 1.0

    # 3. Khoang cach den obstacle thu 2
    dist2 = min(second_dist / 500, 1.0) if second_nearest else 1.0

    # 4. Toc do game
    speed_norm = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)

    # 5. Chieu cao dino
    height_norm = min((ground_y - dino.y) / 100, 1.0)

    # 6. Dang nhay
    is_jumping = 1.0 if dino.is_jumping else 0.0

    # 7. Dang cui
    is_ducking = 1.0 if dino.is_ducking else 0.0

    # 8. Bias
    bias = 0.5

    return [dist1, type1, dist2, speed_norm, height_norm, is_jumping, is_ducking, bias]


class NeatVisualTrainer:
    """Chạy NEAT training với hình ảnh trực quan trên pygame screen."""

    def __init__(self, screen, config):
        self.screen = screen
        self.config = config
        self.clock  = pygame.time.Clock()

        avail = pygame.font.get_fonts()
        mono  = 'consolas' if 'consolas' in avail else 'courier'
        self.font_hud   = pygame.font.SysFont('Arial', 22, bold=True)
        self.font_mono  = pygame.font.SysFont(mono, 18)
        self.font_small = pygame.font.SysFont('Arial', 16)
        self.font_large = pygame.font.SysFont('Arial', 52, bold=True)

        # Trạng thái cross-generation
        self.generation    = 0
        self.best_fitness  = 0.0
        self.best_score    = 0
        self.winner_genome = None
        self._stop         = False   # cờ Ctrl+C / close

    # ── Game loop cho 1 generation ─────────────────────

    def eval_genomes_visual(self, genomes, config):
        """Hàm được gọi bởi neat.Population.run() mỗi generation."""
        if self._stop:
            return

        self.generation += 1

        # Tạo nets và dinos
        nets   = []
        dinos  = []
        fitnesses = []

        for gid, genome in genomes:
            genome.fitness = 0.0
            net = neat.nn.FeedForwardNetwork.create(genome, config)
            nets.append((gid, genome, net))
            dinos.append(Dino())
            fitnesses.append(0.0)

        alive  = list(range(len(dinos)))
        obstacles = []
        score     = INITIAL_SCORE
        game_speed = OBSTACLE_SPEED_MIN
        last_obs_x = 0
        frame = 0
        ground_off = 0

        running = True
        while running and alive:
            # ── Events ──
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._stop = True
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self._stop = True
                        running = False
                        break
                    # Phím S: bỏ qua generation hiện tại
                    if event.key == pygame.K_s:
                        running = False
                        break

            if not running:
                break

            # ── Spawn obstacle ──
            if last_obs_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
                obs = create_obstacle(SCREEN_WIDTH + 50, min(game_speed, OBSTACLE_SPEED_MAX))
                obstacles.append(obs)
                last_obs_x = obs.x

            # ── AI quyết định ──
            to_kill = []
            for idx in alive:
                gid, genome, net = nets[idx]
                d = dinos[idx]
                inputs = _get_inputs(d, obstacles, game_speed)
                out = net.activate(inputs)
                if out[0] > 0.5:
                    d.jump()
                d.duck(out[1] > 0.5)
                d.update()

            # ── Update obstacles ──
            for obs in obstacles:
                obs.update()
                if obs.x < 80 and not obs.passed:
                    obs.passed = True
                    score += 1

            obstacles = [o for o in obstacles if not o.is_off_screen()]
            if obstacles:
                last_obs_x = max(o.x for o in obstacles)

            game_speed = min(
                OBSTACLE_SPEED_MIN + (score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT,
                OBSTACLE_SPEED_MAX
            )

            # ── Kiểm tra va chạm ──
            # Giảm margin từ 8 xuống 2 để tránh collision quá nhạy khi nhảy qua
            margin = 2
            for idx in list(alive):
                d = dinos[idx]
                dr = d.get_rect().inflate(-margin * 2, -margin * 2)
                for obs in obstacles:
                    if dr.colliderect(obs.get_rect().inflate(-margin, -margin)):
                        _, genome, _ = nets[idx]
                        genome.fitness = score * 10.0
                        fitnesses[idx] = genome.fitness
                        alive.remove(idx)
                        break

            # ── Cập nhật fitness của dino còn sống ──
            for idx in alive:
                _, genome, _ = nets[idx]
                genome.fitness = score * 10.0
                fitnesses[idx] = genome.fitness

            # ── Draw ──
            ground_off = (ground_off + game_speed) % 64
            self._draw(dinos, alive, nets, fitnesses, obstacles,
                       score, game_speed, ground_off, frame)
            self.clock.tick(FPS)
            frame += 1

        # Ghi nhận best
        for idx, (gid, genome, net) in enumerate(nets):
            if genome.fitness > self.best_fitness:
                self.best_fitness = genome.fitness
                self.best_score   = score
                self.winner_genome = genome

    # ── Vẽ ──────────────────────────────────────────────

    def _draw(self, dinos, alive_set, nets, fitnesses,
              obstacles, score, speed, ground_off, frame):
        # Background gradient
        for y in range(SCREEN_HEIGHT):
            t = y / SCREEN_HEIGHT
            r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
            g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
            b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # Ground
        tile = load_image("tiles/Tile_01.png", (64, SCREEN_HEIGHT - GROUND_Y))
        if tile:
            off = int(ground_off) % 64
            for x in range(-64, SCREEN_WIDTH + 64, 64):
                self.screen.blit(tile, (x - off, GROUND_Y))
        else:
            pygame.draw.rect(self.screen, GROUND_COL,
                             (0, GROUND_Y, SCREEN_WIDTH, SCREEN_HEIGHT - GROUND_Y))
            pygame.draw.line(self.screen, GROUND_LN,
                             (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 2)

        # Sắp xếp dino theo fitness để gán màu
        n = len(dinos)
        sorted_alive = sorted(alive_set, key=lambda i: fitnesses[i], reverse=True)
        rank_map = {idx: rank for rank, idx in enumerate(sorted_alive)}

        # Vẽ dino chết (xám, mờ)
        for i in range(n):
            if i not in alive_set:
                dr = dinos[i].get_rect()
                s = pygame.Surface((dr.width, dr.height), pygame.SRCALPHA)
                pygame.draw.rect(s, (*DEAD_COL, 60), (0, 0, dr.width, dr.height),
                                 border_radius=4)
                self.screen.blit(s, (dr.x, dr.y))

        # Vẽ dino còn sống (màu theo rank)
        for i in sorted_alive:
            rank  = rank_map[i]
            color = _rank_color(rank, len(sorted_alive))
            dr = dinos[i].get_rect()
            # Body
            pygame.draw.rect(self.screen, color, dr, border_radius=4)
            # Mắt
            eye_x = dr.right - 10
            eye_y = dr.top + 10
            pygame.draw.circle(self.screen, (255, 255, 255), (eye_x, eye_y), 4)
            pygame.draw.circle(self.screen, (0, 0, 0), (eye_x + 1, eye_y), 2)
            # Label fitness nhỏ
            if rank < 3:
                lbl = self.font_small.render(f"#{rank+1}", True, (255, 255, 255))
                self.screen.blit(lbl, (dr.x, dr.y - 16))

        # Obstacles
        for obs in obstacles:
            obs.draw(self.screen)

        # ── HUD Panel góc trên trái ──
        panel = pygame.Surface((260, 130), pygame.SRCALPHA)
        panel.fill(PANEL_COL)
        self.screen.blit(panel, (8, 8))
        pygame.draw.rect(self.screen, (100, 80, 180), (8, 8, 260, 130), 1, border_radius=6)

        lines = [
            f"GEN   {self.generation:>4}",
            f"ALIVE {len(alive_set):>4} / {n}",
            f"SCORE {score:>5}",
            f"FITNESS {self.best_fitness:>8.0f}",
            f"SPEED {speed:>5.1f}",
        ]
        for i, ln in enumerate(lines):
            surf = self.font_mono.render(ln, True, TEXT_COL)
            self.screen.blit(surf, (16, 14 + i * 22))

        # ── Góc trên phải: legend ──
        leg_items = [
            ("🥇 Rank #1", _rank_color(0, max(len(alive_set), 2))),
            ("🥈 Rank #2", _rank_color(1, max(len(alive_set), 2))),
            ("...", (120, 120, 120)),
            ("💀 Dead",    DEAD_COL),
        ]
        for i, (text, col) in enumerate(leg_items):
            pygame.draw.rect(self.screen, col,
                             (SCREEN_WIDTH - 150, 12 + i * 22, 14, 14), border_radius=3)
            t = self.font_small.render(text, True, TEXT_COL)
            self.screen.blit(t, (SCREEN_WIDTH - 132, 12 + i * 22))

        # ── Góc dưới: phím tắt ──
        hint = self.font_small.render("ESC - Dừng training  |  S - Bỏ qua generation", True, (150, 150, 200))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, SCREEN_HEIGHT - 22))

        pygame.display.flip()

    # ── Public API ──────────────────────────────────────

    def run(self, generations=20):
        """Chạy NEAT visual training."""
        population = neat.Population(self.config)
        population.add_reporter(neat.StdOutReporter(True))
        population.add_reporter(neat.StatisticsReporter())

        try:
            population.run(self.eval_genomes_visual, generations)
        except KeyboardInterrupt:
            print("\nTraining dừng sớm.")

        return self.winner_genome


def run_neat_visual(screen, config_path, generations=20):
    """
    Entry point: tạo NeatVisualTrainer, chạy training và trả về genome tốt nhất.
    """
    config = neat.Config(
        neat.DefaultGenome, neat.DefaultReproduction,
        neat.DefaultSpeciesSet, neat.DefaultStagnation,
        config_path
    )
    trainer = NeatVisualTrainer(screen, config)
    winner = trainer.run(generations=generations)
    return winner, config
