"""
Data Collector - Thu thập dữ liệu training từ người chơi và AI
Dữ liệu bao gồm: inputs (trạng thái game) -> outputs (hành động người chơi)
"""
import os
import json
from config.settings import SCREEN_WIDTH


def get_data_path():
    """Đường dẫn lưu file training data"""
    return os.path.join(os.path.dirname(__file__), '..', 'training_data.json')


def get_project_root():
    """Đường dẫn thư mục gốc project"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_data_file_path():
    return os.path.join(get_project_root(), 'training_data.json')


class DataCollector:
    """Thu thập dữ liệu training từ người chơi và AI"""

    # Buffer settings - chỉ lưu database khi đủ dữ liệu
    BUFFER_SIZE = 50  # Lưu database khi có 50 mẫu

    def __init__(self):
        self.data = []
        self.current_session_data = []
        self.use_database = True  # Mặc định sử dụng database
        self._db_buffer = []  # Buffer cho database
    
    def get_inputs_from_game(self, dino, obstacles, game_speed, ground_y=None):
        """
        Lấy inputs từ trạng thái game hiện tại
        Trả về list 8 giá trị đã normalize (để match với NEAT inputs)
        """
        from config.settings import GROUND_Y, OBSTACLE_SPEED_MIN, OBSTACLE_SPEED_MAX

        if ground_y is None:
            ground_y = GROUND_Y

        # Tìm obstacle gần nhất và thứ 2
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

        # Nếu không có obstacle phía trước
        if nearest is None:
            return [1.0, 0.5, 1.0, 0.0, 0.0, 0.0, 0.0, 0.5]

        from src.obstacle import Cactus, Bird

        # 1. Khoảng cách đến obstacle gần nhất (0-1)
        dist1 = min(min_dist / 500, 1.0)

        # 2. Loại obstacle gần nhất (0 = Cactus, 1 = Bird)
        type1 = 0.0 if isinstance(nearest, Cactus) else 1.0

        # Xử lý chiều cao Bird
        if isinstance(nearest, Bird):
            bird_height = nearest.y
            height_ratio = (GROUND_Y - bird_height) / 130
            type1 = 0.3 + height_ratio * 0.7

        # 3. Khoảng cách đến obstacle thứ 2
        dist2 = min(second_dist / 500, 1.0) if second_nearest else 1.0

        # 4. Tốc độ game hiện tại (0-1)
        speed_normalized = (game_speed - OBSTACLE_SPEED_MIN) / (OBSTACLE_SPEED_MAX - OBSTACLE_SPEED_MIN)

        # 5. Độ cao của dino so với mặt đất (0-1)
        height_normalized = min((ground_y - dino.y) / 100, 1.0)

        # 6. Dino có đang nhảy không (0 hoặc 1)
        is_jumping = 1.0 if dino.is_jumping else 0.0

        # 7. Dino có đang cúi không (0 hoặc 1)
        is_ducking = 1.0 if dino.is_ducking else 0.0

        # 8. Bias (fixed value)
        bias = 0.5

        return [
            dist1,               # Khoảng cách đến obstacle 1
            type1,               # Loại obstacle 1
            dist2,               # Khoảng cách đến obstacle 2
            speed_normalized,    # Tốc độ game
            height_normalized,   # Độ cao dino
            is_jumping,          # Đang nhảy
            is_ducking,          # Đang cúi
            bias                 # Bias
        ]
    
    def get_player_action(self, keys_pressed, dino):
        """
        Xác định hành động của người chơi từ input
        Trả về: (jump, duck) với giá trị 0 hoặc 1
        """
        # Record actual key presses - if player pressed jump, record it even if already jumping
        # This fixes data loss issue where jumping state was returning (0,0)
        jump = 1 if keys_pressed.get('jump', False) else 0
        duck = 1 if keys_pressed.get('duck', False) else 0

        # If already jumping, player cannot duck, but still record jump action
        if dino.is_jumping:
            return (jump, 0)

        return (jump, duck)
    
    def record_sample(self, dino, obstacles, game_speed, action, source="human", ground_y=None, score=0):
        """
        Ghi một mẫu dữ liệu
        action: tuple (jump, duck) với giá trị 0 hoặc 1
        source: "human" (người chơi) hoặc "ai" (AI)
        """
        inputs = self.get_inputs_from_game(dino, obstacles, game_speed, ground_y)

        # inputs now has 8 values:
        # [dist1, type1, dist2, speed_norm, height_norm, is_jumping, is_ducking, bias]
        sample = {
            "inputs": inputs,
            "outputs": {
                "jump": action[0],
                "duck": action[1]
            },
            "source": source,
            "game_speed": game_speed,
            "score": score,
            # Raw values for database (mapped to correct indices)
            "distance_to_obstacle": inputs[0],  # dist1
            "obstacle_type": inputs[1],         # type1
            "distance_to_obstacle_2": inputs[2],  # dist2 (NEW)
            "game_speed_norm": inputs[3],       # speed_normalized
            "dino_height": inputs[4],            # height_normalized
            "is_jumping": inputs[5],            # is_jumping
            "is_ducking": inputs[6],           # is_ducking
            "action_jump": action[0],
            "action_duck": action[1],
            "game_speed_raw": game_speed
        }
        
        self.current_session_data.append(sample)
        self._db_buffer.append(sample)

        # Chỉ lưu vào database khi buffer đầy hoặc khi game kết thúc
        if len(self._db_buffer) >= self.BUFFER_SIZE:
            self._flush_db_buffer()
    
    def _flush_db_buffer(self):
        """Lưu buffer vào database (chạy nền để không lag game)"""
        if not self._db_buffer:
            return
        if not self.use_database:
            self._db_buffer = []
            return

        try:
            from src.database_handler import save_training_data
            import threading

            db_data = []
            for sample in self._db_buffer:
                db_data.append({
                    "distance_to_obstacle": sample.get("distance_to_obstacle", 0),
                    "obstacle_type": sample.get("obstacle_type", 0),
                    "distance_to_obstacle_2": sample.get("distance_to_obstacle_2", 1.0),
                    "game_speed": sample.get("game_speed_norm", 0),
                    "dino_height": sample.get("dino_height", 0),
                    "is_jumping": sample.get("is_jumping", 0),
                    "is_ducking": sample.get("is_ducking", 0),
                    "action_jump": sample.get("action_jump", 0),
                    "action_duck": sample.get("action_duck", 0),
                    "source": sample.get("source", "human"),
                    "game_speed_raw": sample.get("game_speed_raw", 0),
                    "score": sample.get("score", 0),
                    "quality_score": 1.0
                })

            def save_in_background():
                try:
                    save_training_data(db_data)
                except Exception as e:
                    print(f"Lỗi lưu database nền: {e}")

            threading.Thread(target=save_in_background, daemon=True).start()
        except Exception as e:
            pass

        self._db_buffer = []

    def save_session_data(self):
        """Lưu dữ liệu session hiện tại vào database và file"""
        # Flush buffer trước
        self._flush_db_buffer()

        if not self.current_session_data:
            return 0

        total_saved = 0
        
        # Lưu vào database nếu được bật
        if self.use_database:
            try:
                from src.database_handler import save_training_data
                
                # Chuyển đổi dữ liệu sang format cho database
                db_data = []
                for sample in self.current_session_data:
                    db_data.append({
                        "distance_to_obstacle": sample.get("distance_to_obstacle", 0),
                        "obstacle_type": sample.get("obstacle_type", 0),
                        "distance_to_obstacle_2": sample.get("distance_to_obstacle_2", 1.0),
                        "game_speed": sample.get("game_speed_norm", 0),
                        "dino_height": sample.get("dino_height", 0),
                        "is_jumping": sample.get("is_jumping", 0),
                        "is_ducking": sample.get("is_ducking", 0),
                        "action_jump": sample.get("action_jump", 0),
                        "action_duck": sample.get("action_duck", 0),
                        "source": sample.get("source", "human"),
                        "game_speed_raw": sample.get("game_speed_raw", 0),
                        "score": sample.get("score", 0),
                        "quality_score": 1.0
                    })
                
                total_saved = save_training_data(db_data)
                print(f"Đã lưu {total_saved} mẫu vào database")
            except Exception as e:
                print(f"Lỗi khi lưu vào database: {e}")
        
        # Vẫn lưu vào file JSON làm backup
        all_data = self.load_data()
        all_data.extend(self.current_session_data)
        
        try:
            with open(get_data_file_path(), 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2)
        except Exception as e:
            print(f"Lỗi khi lưu file: {e}")
        
        self.current_session_data = []
        return total_saved
    
    def load_data(self):
        """Load dữ liệu training từ file"""
        path = get_data_file_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return []
    
    def get_training_data(self):
        """Lấy toàn bộ dữ liệu training"""
        return self.load_data()
    
    def get_data_stats(self):
        """Thống kê dữ liệu training"""
        # Thử lấy từ database trước
        try:
            from src.database_handler import get_training_data_count
            total = get_training_data_count()
            human = get_training_data_count("human")
            ai = get_training_data_count("ai")
            return {"total": total, "human": human, "ai": ai, "source": "database"}
        except:
            pass
        
        # Fallback: lấy từ file
        data = self.load_data()
        if not data:
            return {"total": 0, "human": 0, "ai": 0, "source": "file"}
        
        human_count = sum(1 for d in data if d.get("source") == "human")
        ai_count = sum(1 for d in data if d.get("source") == "ai")
        
        return {
            "total": len(data),
            "human": human_count,
            "ai": ai_count,
            "source": "file"
        }
    
    def clear_data(self):
        """Xóa toàn bộ dữ liệu training"""
        path = get_data_file_path()
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False
    
    def set_use_database(self, use_db):
        """Bật/tắt sử dụng database"""
        self.use_database = use_db


# Singleton instance
_collector = None


def get_collector():
    """Lấy instance của DataCollector"""
    global _collector
    if _collector is None:
        _collector = DataCollector()
    return _collector
