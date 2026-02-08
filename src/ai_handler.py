"""
AI Handler - Xử lý thuật toán NEAT cho DinoRacer
"""
import os
import neat
from config.settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, BG_COLOR, GROUND_COLOR, GROUND_Y,
    INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
    TEXT_COLOR
)
from src.dino import Dino
from src.obstacle import create_obstacle


def get_config_path():
    """Đường dẫn đến file config NEAT"""
    return os.path.join(os.path.dirname(__file__), '..', 'config', 'neat-config.txt')


def eval_genome(genome, config):
    """
    Đánh giá 1 genome - chạy game và trả về fitness
    """
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    fitness = 0

    dino = Dino()
    obstacles = []
    score = INITIAL_SCORE
    game_speed = OBSTACLE_SPEED_MIN
    last_obstacle_x = SCREEN_WIDTH

    # Chạy game cho đến khi chết (tối đa vài nghìn frame)
    max_frames = 5000
    for _ in range(max_frames):
        # Lấy state
        nearest = None
        min_dist = float('inf')
        for obs in obstacles:
            if obs.x > dino.x:
                dist = obs.x - dino.x
                if dist < min_dist:
                    min_dist = dist
                    nearest = obs

        if nearest is None:
            inputs = [1.0, 0.5, 0.0, 0.0, 0.0]
        else:
            from src.obstacle import Cactus
            dist_norm = min(min_dist / 500, 1.0)
            obs_type = 0.0 if isinstance(nearest, Cactus) else 1.0
            speed_norm = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
            dino_y_norm = min((GROUND_Y - dino.y) / 100, 1.0)
            is_jump = 1.0 if dino.is_jumping else 0.0
            inputs = [dist_norm, obs_type, speed_norm, dino_y_norm, is_jump]

        output = net.activate(inputs)
        jump, duck, _ = output

        if jump > 0.5:
            dino.jump()
        dino.duck(duck > 0.5)

        dino.update()

        # Spawn obstacle
        if last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
            speed = min(game_speed, OBSTACLE_SPEED_MAX)
            obs = create_obstacle(SCREEN_WIDTH + 50, speed)
            obstacles.append(obs)
            last_obstacle_x = obs.x

        for obs in obstacles:
            obs.update()
            if obs.x < dino.x and not obs.passed:
                obs.passed = True
                score += 1

        obstacles = [o for o in obstacles if not o.is_off_screen()]
        if obstacles:
            last_obstacle_x = max(o.x for o in obstacles)

        game_speed = OBSTACLE_SPEED_MIN + (score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
        game_speed = min(game_speed, OBSTACLE_SPEED_MAX)

        # Kiểm tra va chạm
        dino_rect = dino.get_rect()
        for obs in obstacles:
            if dino_rect.colliderect(obs.get_rect()):
                fitness = score * 10  # Fitness = điểm * 10
                return fitness

        fitness = score * 10

    return fitness


def eval_genomes(genomes, config):
    """Đánh giá toàn bộ population"""
    for genome_id, genome in genomes:
        genome.fitness = eval_genome(genome, config)


def run_neat_training(generations=50):
    """
    Chạy training NEAT.
    generations: Số thế hệ huấn luyện
    """
    config_path = get_config_path()
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                        neat.DefaultSpeciesSet, neat.DefaultStagnation,
                        config_path)

    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    population.add_reporter(stats)

    winner = population.run(eval_genomes, generations)
    return winner


def run_best_genome_display(genome, config):
    """Chạy game với genome tốt nhất và hiển thị"""
    import pygame
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("DinoRacer - AI Training")
    clock = pygame.time.Clock()

    net = neat.nn.FeedForwardNetwork.create(genome, config)
    dino = Dino()
    obstacles = []
    score = 0
    game_speed = OBSTACLE_SPEED_MIN
    last_obstacle_x = SCREEN_WIDTH
    game_over = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                pygame.quit()
                return genome

        if not game_over:
            nearest = None
            min_dist = float('inf')
            for obs in obstacles:
                if obs.x > dino.x:
                    dist = obs.x - dino.x
                    if dist < min_dist:
                        min_dist = dist
                        nearest = obs

            if nearest is None:
                inputs = [1.0, 0.5, 0.0, 0.0, 0.0]
            else:
                from src.obstacle import Cactus
                dist_norm = min(min_dist / 500, 1.0)
                obs_type = 0.0 if isinstance(nearest, Cactus) else 1.0
                speed_norm = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
                dino_y_norm = min((GROUND_Y - dino.y) / 100, 1.0)
                is_jump = 1.0 if dino.is_jumping else 0.0
                inputs = [dist_norm, obs_type, speed_norm, dino_y_norm, is_jump]

            output = net.activate(inputs)
            jump, duck, _ = output
            if jump > 0.5:
                dino.jump()
            dino.duck(duck > 0.5)

            dino.update()

            if last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
                speed = min(game_speed, OBSTACLE_SPEED_MAX)
                obs = create_obstacle(SCREEN_WIDTH + 50, speed)
                obstacles.append(obs)
                last_obstacle_x = obs.x

            for obs in obstacles:
                obs.update()
                if obs.x < dino.x and not obs.passed:
                    obs.passed = True
                    score += 1

            obstacles = [o for o in obstacles if not o.is_off_screen()]
            if obstacles:
                last_obstacle_x = max(o.x for o in obstacles)

            game_speed = OBSTACLE_SPEED_MIN + (score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT
            game_speed = min(game_speed, OBSTACLE_SPEED_MAX)

            dino_rect = dino.get_rect()
            for obs in obstacles:
                if dino_rect.colliderect(obs.get_rect()):
                    game_over = True
                    break

        screen.fill(BG_COLOR)
        pygame.draw.line(screen, GROUND_COLOR, (0, GROUND_Y), (SCREEN_WIDTH, GROUND_Y), 3)
        dino.draw(screen)
        for obs in obstacles:
            obs.draw(screen)

        font = pygame.font.Font(None, 36)
        text = font.render(f"Score: {score}", True, TEXT_COLOR)
        screen.blit(text, (SCREEN_WIDTH - 150, 30))

        if game_over:
            font_large = pygame.font.Font(None, 72)
            text_go = font_large.render("GAME OVER", True, (200, 0, 0))
            rect = text_go.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(text_go, rect)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    return genome
