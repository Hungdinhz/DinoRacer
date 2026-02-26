"""
AI Handler - Xử lý thuật toán NEAT cho DinoRacer
"""
import os
import pickle
import neat
from config.settings import (
    BEST_GENOME_FILE,
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    GROUND_Y, INITIAL_SCORE, SPEED_INCREASE_INTERVAL, SPEED_INCREASE_AMOUNT,
    MIN_OBSTACLE_SPAWN_DISTANCE, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX,
)
from src.dino import Dino
from src.obstacle import create_obstacle
from src.highscore import load_highscore, save_highscore
from src.assets_loader import play_sound


def get_config_path():
    return os.path.join(os.path.dirname(__file__), '..', 'config', 'neat-config.txt')


def get_genome_path():
    return os.path.join(os.path.dirname(__file__), '..', BEST_GENOME_FILE)


def save_genome(genome):
    try:
        with open(get_genome_path(), "wb") as f:
            pickle.dump(genome, f)
        return True
    except (IOError, pickle.PickleError):
        return False


def load_genome():
    path = get_genome_path()
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                genome = pickle.load(f)
            config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                 neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                 get_config_path())
            return genome, config
    except Exception:
        pass
    return None, None


def _get_inputs(dino, obstacles, game_speed):
    nearest = None
    min_dist = float('inf')
    for obs in obstacles:
        if obs.x > dino.x:
            dist = obs.x - dino.x
            if dist < min_dist:
                min_dist = dist
                nearest = obs
    if nearest is None:
        return [1.0, 0.5, 0.0, 0.0, 0.0]
    from src.obstacle import Cactus
    return [
        min(min_dist / 500, 1.0),
        0.0 if isinstance(nearest, Cactus) else 1.0,
        (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN),
        min((GROUND_Y - dino.y) / 100, 1.0),
        1.0 if dino.is_jumping else 0.0,
    ]


def eval_genome(genome, config):
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    dino = Dino()
    obstacles = []
    score = INITIAL_SCORE
    game_speed = OBSTACLE_SPEED_MIN
    last_obstacle_x = SCREEN_WIDTH

    for _ in range(5000):
        inputs = _get_inputs(dino, obstacles, game_speed)
        output = net.activate(inputs)
        jump, duck, _ = output
        if jump > 0.5:
            dino.jump()
        dino.duck(duck > 0.5)
        dino.update()

        if last_obstacle_x - SCREEN_WIDTH < -MIN_OBSTACLE_SPAWN_DISTANCE:
            obs = create_obstacle(SCREEN_WIDTH + 50, min(game_speed, OBSTACLE_SPEED_MAX))
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

        game_speed = min(
            OBSTACLE_SPEED_MIN + (score // SPEED_INCREASE_INTERVAL) * SPEED_INCREASE_AMOUNT,
            OBSTACLE_SPEED_MAX
        )

        dino_rect = dino.get_rect()
        for obs in obstacles:
            if dino_rect.colliderect(obs.get_rect()):
                return score * 10

    return score * 10


def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        genome.fitness = eval_genome(genome, config)


def run_neat_training(generations=50):
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         get_config_path())
    population = neat.Population(config)
    population.add_reporter(neat.StdOutReporter(True))
    population.add_reporter(neat.StatisticsReporter())
    winner = population.run(eval_genomes, generations)
    if winner and save_genome(winner):
        print(f"Đã lưu AI vào {get_genome_path()}")
    return winner


def run_best_genome_display(genome, config):
    """Chạy game với genome tốt nhất - dùng GameManager để hiển thị"""
    import pygame
    from src.game_manager import GameManager

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("DinoRacer - AI Play")
    clock = pygame.time.Clock()

    net = neat.nn.FeedForwardNetwork.create(genome, config)
    gm = GameManager(screen, is_ai_mode=True)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if not gm.game_over:
            inputs = _get_inputs(gm.dino, gm.obstacles, gm.game_speed)
            output = net.activate(inputs)
            gm.update(action=output)
        
        gm.draw()
        clock.tick(FPS)

    return genome
