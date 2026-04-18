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


def get_best_model_path():
    return os.path.join(os.path.dirname(__file__), '..', 'models', 'best_model.pkl')


def get_last_model_path():
    return os.path.join(os.path.dirname(__file__), '..', 'models', 'last_model.pkl')


def save_genome(genome):
    try:
        with open(get_genome_path(), "wb") as f:
            pickle.dump(genome, f)
        return True
    except (IOError, pickle.PickleError):
        return False


def load_genome():
    """Load genome từ file cũ (best_genome.pkl) hoặc models/best_model.pkl mới."""
    # Ưu tiên file mới trong models/
    best_path = get_best_model_path()
    if os.path.exists(best_path):
        try:
            with open(best_path, "rb") as f:
                genome = pickle.load(f)
            config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                 neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                 get_config_path())
            print(f"[AI] Loaded model from {best_path}")
            return genome, config
        except Exception as e:
            print(f"[AI] Loi load tu {best_path}: {e}")

    # Fallback về file cũ
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
    frames_survived = 0

    for i in range(5000):
        frames_survived = i
        inputs = _get_inputs(dino, obstacles, game_speed)
        output = net.activate(inputs)
        jump, duck = output[:2]
        if jump > 0.5:
            dino.jump()
        dino.set_duck(duck > 0.5)  # AI dùng set_duck thay vì duck
        dino.update(jump_held=False)  # AI không giữ phím

        # Spawn new obstacle if enough distance from last one
        if len(obstacles) == 0 or last_obstacle_x <= SCREEN_WIDTH - MIN_OBSTACLE_SPAWN_DISTANCE:
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
                final_fitness = frames_survived + score * 10 * (1 + speed_bonus)
                return final_fitness

    # Cải thiện fitness: thưởng nhiều hơn khi sống lâu ở tốc độ cao
    speed_bonus = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)
    # Use frames survived + score as fitness (prevents zero fitness)
    final_fitness = frames_survived + score * 10 * (1 + speed_bonus)
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
    if winner:
        saved1 = save_genome(winner)
        # Also save to new model path
        try:
            import os as osmod
            model_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
            osmod.makedirs(model_dir, exist_ok=True)
            with open(get_best_model_path(), "wb") as f:
                pickle.dump(winner, f)
            saved2 = True
        except Exception:
            saved2 = False
        print(f"AI saved: best_genome.pkl={saved1}, models/best_model.pkl={saved2}")
        if saved1 or saved2:
            print(f"Da luu AI vao {get_genome_path()}")
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


# ============================================
# HYBRID AI - Kết hợp NEAT và Supervised
# ============================================

class HybridAI:
    """Hybrid AI kết hợp NEAT và Supervised Learning"""

    def __init__(self, neat_genome=None, neat_config=None, neat_weight=0.3):
        """
        Khởi tạo Hybrid AI
        - neat_genome: NEAT genome (nếu None sẽ load từ file)
        - neat_config: NEAT config
        - neat_weight: Trọng số của NEAT (0-1), supervised sẽ là (1 - neat_weight)
        """
        self.neat_net = None
        self.supervised_jump_model = None
        self.supervised_duck_model = None
        self.supervised_scaler = None
        self.neat_weight = neat_weight

        # Load NEAT
        if neat_genome and neat_config:
            self.neat_net = neat.nn.FeedForwardNetwork.create(neat_genome, neat_config)
        else:
            # Thử load từ file
            genome, config = load_genome()
            if genome and config:
                self.neat_net = neat.nn.FeedForwardNetwork.create(genome, config)

        # Load Supervised models
        try:
            from src.supervised_trainer import load_models
            jump_data, duck_data = load_models()
            if jump_data and duck_data:
                self.supervised_jump_model = jump_data['model']
                self.supervised_duck_model = duck_data['model']
                self.supervised_scaler = jump_data['scaler']
                print("Hybrid AI: Loaded both NEAT and Supervised models")
            else:
                print("Hybrid AI: Chỉ có NEAT (Supervised models chưa train)")
        except Exception as e:
            print(f"Hybrid AI: Lỗi load supervised: {e}")
            print("Hybrid AI: Chỉ dùng NEAT")

    def predict(self, inputs):
        """
        Dự đoán action kết hợp từ cả 2 model
        inputs: 8 giá trị [dist1, type1, dist2, speed, height, is_jumping, is_ducking, bias]
        Returns: (jump, duck) với giá trị 0-1
        """
        neat_jump = 0
        neat_duck = 0

        # NEAT prediction
        if self.neat_net:
            neat_output = self.neat_net.activate(inputs)
            neat_jump = neat_output[0]
            neat_duck = neat_output[1] if len(neat_output) > 1 else 0

        # Nếu không có supervised, chỉ dùng NEAT
        if not self.supervised_jump_model:
            return (1 if neat_jump > 0.5 else 0, 1 if neat_duck > 0.5 else 0)

        # Supervised prediction - chỉ dùng 6 features đầu (bỏ dist2 và bias)
        try:
            import numpy as np
            # Supervised model được train với 6 features: [dist1, type1, speed, height, is_jumping, is_ducking]
            supervised_inputs = [inputs[0], inputs[1], inputs[3], inputs[4], inputs[5], inputs[6]]
            inputs_arr = np.array(supervised_inputs).reshape(1, -1)
            inputs_scaled = self.supervised_scaler.transform(inputs_arr)

            sup_jump_prob = self.supervised_jump_model.predict_proba(inputs_scaled)[0][1]
            sup_duck_prob = self.supervised_duck_model.predict_proba(inputs_scaled)[0][1]

            # Rule-based combination: NEAT with safety override
            dist1 = inputs[0]  # normalized distance to nearest obstacle

            # If obstacle is close (< 25% of screen), FORCE JUMP
            if dist1 < 0.25:
                return (1, 0)

            # Otherwise use NEAT output directly
            final_jump = 1 if neat_jump > 0.3 else 0
            final_duck = 0  # Disable duck for safety

            return (final_jump, final_duck)

        except Exception as e:
            # Nếu supervised lỗi, fallback về NEAT
            print(f"Hybrid AI warning: {e}")
            return (1 if neat_jump > 0.5 else 0, 1 if neat_duck > 0.5 else 0)


def get_hybrid_ai():
    """Factory function để lấy Hybrid AI instance"""
    genome, config = load_genome()
    return HybridAI(neat_genome=genome, neat_config=config, neat_weight=0.3)
