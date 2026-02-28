"""
Settings - Cấu hình toàn bộ game DinoRacer
"""

# Màn hình - Tăng kích thước để chơi thoải mái hơn
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Màu sắc
BG_COLOR = (247, 247, 247)
GROUND_COLOR = (83, 83, 83)
TEXT_COLOR = (83, 83, 83)
DINO_COLOR = (83, 83, 83)
CACTUS_COLOR = (0, 128, 0)
BIRD_COLOR = (100, 100, 200)

# Mặt đất - Điều chỉnh theo màn hình mới
GROUND_Y = 550

# Dino
DINO_X = 100
DINO_WIDTH = 80
DINO_HEIGHT = 80
GRAVITY = 0.8           # Gravity nhẹ hơn cho cảm giác nhảy mượt hơn
JUMP_VELOCITY = -18

# Smooth physics - Giúp cảm giác nhảy mượt mà hơn
JUMP_HOLD_GRAVITY = 0.4  # Gravity khi giữ nút nhảy (nhảy cao hơn)
JUMP_MIN_VELOCITY = -6   # Velocity tối thiểu khi thả sớm
JUMP_CURVE = 0.15        # Jump curve - giá trị càng lớn càng cong

# Coyote time - Cho phép nhảy sau khi rời chân trong 1 khoảng thời gian ngắn
COYOTE_TIME = 8          # Frames (khoảng 133ms) - tăng lên để dễ nhảy hơn

# Jump buffer - Cho phép nhảy trước khi chạm đất
JUMP_BUFFER = 10          # Frames - tăng lên để responsive hơn

# Landing - Giảm bounce khi chạm đất
LANDING_BOUNCE = 0       # Không bounce

DUCK_HEIGHT_RATIO = 0.5  # Khi cúi xuống còn 50% chiều cao

# Chướng ngại vật - Cactus
CACTUS_WIDTH = 45
CACTUS_HEIGHT_SMALL = 55
CACTUS_HEIGHT_LARGE = 90

# Chướng ngại vật - Bird
BIRD_WIDTH = 70
BIRD_HEIGHT = 45

# Tốc độ chướng ngại vật - Điều chỉnh cho màn hình lớn hơn
OBSTACLE_SPEED_MIN = 7
OBSTACLE_SPEED_MAX = 20

# Khoảng cách spawn tối thiểu - Tăng lên cho màn hình rộng hơn
MIN_OBSTACLE_SPAWN_DISTANCE = 350

# Điểm số
INITIAL_SCORE = 0
SPEED_INCREASE_INTERVAL = 15  # Tăng điểm cần thiết để tăng tốc
SPEED_INCREASE_AMOUNT = 0.3   # Tăng tốc chậm hơn

# File lưu trữ
HIGHSCORE_FILE = "highscore.json"
BEST_GENOME_FILE = "best_genome.pkl"
