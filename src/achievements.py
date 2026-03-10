"""
Achievements System - Hệ thống thành tựu trong game
"""
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Định nghĩa các thành tựu
ACHIEVEMENTS = {
    # Score achievements
    "score_100": {
        "name": "Beginner Runner",
        "description": "Score 100 points",
        "icon": "🏃",
        "requirement": {"type": "score", "value": 100}
    },
    "score_500": {
        "name": "Intermediate Runner", 
        "description": "Score 500 points",
        "icon": "🏅",
        "requirement": {"type": "score", "value": 500}
    },
    "score_1000": {
        "name": "Expert Runner",
        "description": "Score 1000 points",
        "icon": "🥇",
        "requirement": {"type": "score", "value": 1000}
    },
    "score_5000": {
        "name": "Master Runner",
        "description": "Score 5000 points",
        "icon": "👑",
        "requirement": {"type": "score", "value": 5000}
    },
    
    # Obstacles passed
    "obstacles_50": {
        "name": "Dodger",
        "description": "Pass 50 obstacles",
        "icon": "🎯",
        "requirement": {"type": "obstacles", "value": 50}
    },
    "obstacles_200": {
        "name": "Expert Dodger",
        "description": "Pass 200 obstacles",
        "icon": "⭐",
        "requirement": {"type": "obstacles", "value": 200}
    },
    "obstacles_500": {
        "name": "Dodge Master",
        "description": "Pass 500 obstacles",
        "icon": "🌟",
        "requirement": {"type": "obstacles", "value": 500}
    },
    
    # Games played
    "games_10": {
        "name": "Regular Player",
        "description": "Play 10 games",
        "icon": "🎮",
        "requirement": {"type": "games", "value": 10}
    },
    "games_50": {
        "name": "Dedicated Player",
        "description": "Play 50 games",
        "icon": "🎰",
        "requirement": {"type": "games", "value": 50}
    },
    "games_100": {
        "name": "Game Enthusiast",
        "description": "Play 100 games",
        "icon": "🎲",
        "requirement": {"type": "games", "value": 100}
    },
    
    # Training data
    "data_100": {
        "name": "Data Collector",
        "description": "Collect 100 training samples",
        "icon": "📊",
        "requirement": {"type": "data", "value": 100}
    },
    "data_1000": {
        "name": "Data Master",
        "description": "Collect 1000 training samples",
        "icon": "📈",
        "requirement": {"type": "data", "value": 1000}
    },
    "data_10000": {
        "name": "Big Data Expert",
        "description": "Collect 10000 training samples",
        "icon": "🏆",
        "requirement": {"type": "data", "value": 10000}
    },
    
    # Time attack
    "time_attack_20": {
        "name": "Speed Demon",
        "description": "Pass 20 obstacles in Time Attack",
        "icon": "⚡",
        "requirement": {"type": "time_attack", "value": 20}
    },
    "time_attack_50": {
        "name": "Time Lord",
        "description": "Pass 50 obstacles in Time Attack",
        "icon": "⏰",
        "requirement": {"type": "time_attack", "value": 50}
    },
    
    # Special
    "win_streak_5": {
        "name": "On Fire",
        "description": "Win 5 games in a row",
        "icon": "🔥",
        "requirement": {"type": "streak", "value": 5}
    },
    "win_streak_10": {
        "name": "Unstoppable",
        "description": "Win 10 games in a row",
        "icon": "💥",
        "requirement": {"type": "streak", "value": 10}
    },
}


def get_achievements_file():
    """Lấy đường dẫn file achievements"""
    from pathlib import Path
    return str(Path(__file__).parent.parent / 'achievements.json')


class Achievements:
    """Quản lý thành tựu"""
    
    def __init__(self):
        self.achievements = {}
        self.unlocked = set()
        self.load()
    
    def load(self):
        """Load achievements từ file"""
        path = get_achievements_file()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.achievements = data.get('achievements', {})
                    self.unlocked = set(data.get('unlocked', []))
        except Exception as e:
            logger.error(f"Error loading achievements: {e}")
    
    def save(self):
        """Lưu achievements vào file"""
        path = get_achievements_file()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({
                    'achievements': self.achievements,
                    'unlocked': list(self.unlocked)
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving achievements: {e}")
    
    def unlock(self, achievement_id):
        """Mở khóa thành tựu"""
        if achievement_id not in self.unlocked:
            self.unlocked.add(achievement_id)
            self.achievements[achievement_id] = {
                'unlocked_at': self.get_timestamp(),
                **ACHIEVEMENTS.get(achievement_id, {})
            }
            self.save()
            return True
        return False
    
    def get_timestamp(self):
        """Lấy thời gian hiện tại"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def check_and_unlock(self, stats):
        """
        Kiểm tra và mở khóa achievements dựa trên stats
        stats: dict chứa score, obstacles, games, data, time_attack, streak
        """
        newly_unlocked = []
        
        for aid, ach in ACHIEVEMENTS.items():
            if aid in self.unlocked:
                continue
            
            req = ach.get('requirement', {})
            req_type = req.get('type')
            req_value = req.get('value', 0)
            current_value = stats.get(req_type, 0)
            
            if current_value >= req_value:
                if self.unlock(aid):
                    newly_unlocked.append(ach)
        
        return newly_unlocked
    
    def get_all_achievements(self):
        """Lấy tất cả achievements"""
        result = []
        for aid, ach in ACHIEVEMENTS.items():
            result.append({
                'id': aid,
                'name': ach['name'],
                'description': ach['description'],
                'icon': ach['icon'],
                'unlocked': aid in self.unlocked,
                'unlocked_at': self.achievements.get(aid, {}).get('unlocked_at')
            })
        return result
    
    def get_unlocked_count(self):
        """Số achievements đã mở khóa"""
        return len(self.unlocked)
    
    def get_total_count(self):
        """Tổng số achievements"""
        return len(ACHIEVEMENTS)


# Singleton
_achievements = None


def get_achievements():
    """Lấy instance của Achievements"""
    global _achievements
    if _achievements is None:
        _achievements = Achievements()
    return _achievements


def check_achievements(score=0, obstacles=0, games=0, data=0, time_attack=0, streak=0):
    """Hàm tiện ích để kiểm tra achievements"""
    stats = {
        'score': score,
        'obstacles': obstacles,
        'games': games,
        'data': data,
        'time_attack': time_attack,
        'streak': streak
    }
    
    ach = get_achievements()
    return ach.check_and_unlock(stats)
