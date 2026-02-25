"""
High Score - Lưu và tải điểm cao nhất
"""
import os
import json
from config.settings import HIGHSCORE_FILE


def get_project_root():
    """Đường dẫn thư mục gốc project"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_highscore_path():
    return os.path.join(get_project_root(), HIGHSCORE_FILE)


def load_highscore():
    """Tải điểm cao nhất, trả về (human_highscore, ai_highscore)"""
    path = get_highscore_path()
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("human", 0), data.get("ai", 0)
    except (json.JSONDecodeError, IOError):
        pass
    return 0, 0


def save_highscore(human=None, ai=None):
    """Lưu điểm cao (chỉ cập nhật phần được truyền vào)"""
    path = get_highscore_path()
    h, a = load_highscore()
    if human is not None and human > h:
        h = human
    if ai is not None and ai > a:
        a = ai
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"human": h, "ai": a}, f, indent=2)
    except IOError:
        pass
