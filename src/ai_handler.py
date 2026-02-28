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


def _get_inputs_from_lane(lane):
    """Lấy inputs từ LaneGame object (dùng cho PVE mode)."""
    return _get_inputs(lane.dino, lane.obstacles, lane.game_speed)


def _get_inputs(dino, obstacles, game_speed):
    """Cải thiện inputs cho AI - thêm nhiều features hơn"""
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

    # Nếu không có obstacle
    if nearest is None:
        return [1.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    from src.obstacle import Cactus, Bird

    # Tính toán các inputs
    # 1. Khoảng cách đến obstacle gần nhất (normalized)
    dist1 = min(min_dist / 500, 1.0)

    # 2. Loại obstacle gần nhất (0 = Cactus, 1 = Bird)
    type1 = 0.0 if isinstance(nearest, Cactus) else 1.0

    # 3. Chiều cao của Bird (0 = thấp, 1 = cao, 2 = rất cao)
    if isinstance(nearest, Bird):
        bird_height = nearest.y
        height_ratio = (GROUND_Y - bird_height) / 130  # 130 = max height diff
        type1 = 0.3 + height_ratio * 0.7  # Map to 0.3-1.0 range

    # 4. Khoảng cách đến obstacle thứ 2
    dist2 = min(second_dist / 500, 1.0) if second_nearest else 1.0

    # 5. Tốc độ game (normalized)
    speed_norm = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)

    # 6. Độ cao hiện tại của dino (0 = ground, 1 = cao nhất)
    height_norm = min((GROUND_Y - dino.y) / 100, 1.0)

    # 7. Đang nhảy hay không
    is_jumping = 1.0 if dino.is_jumping else 0.0

    # 8. Đang cúi hay không
    is_ducking = 1.0 if dino.is_ducking else 0.0

    return [dist1, type1, dist2, speed_norm, height_norm, is_jumping, is_ducking, 0.5]


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
        dino.set_duck(duck > 0.5)  # AI dùng set_duck thay vì duck
        dino.update(jump_held=False)  # AI không giữ phím

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
        # Thêm margin để AI không bị penalty quá nặng
        margin = 4
        for obs in obstacles:
            if dino_rect.inflate(-margin, -margin).colliderect(obs.get_rect().inflate(-margin, -margin)):
                # Cải thiện fitness: thưởng nhiều hơn khi sống lâu ở tốc độ cao
                speed_bonus = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
                final_fitness = score * 10 * (1 + speed_bonus)
                return final_fitness

    # Cải thiện fitness: thưởng nhiều hơn khi sống lâu ở tốc độ cao
    speed_bonus = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
    final_fitness = score * 10 * (1 + speed_bonus)
    return final_fitness


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
            gm.update(action=output, jump_held=False)
        
        gm.draw()
        clock.tick(FPS)

    return genome
