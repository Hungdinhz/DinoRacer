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
    """Tải điểm cao nhất, kết hợp giữa local và database, trả về (human_highscore, ai_highscore)"""
    path = get_highscore_path()
    local_human, local_ai = 0, 0
    
    # 1. Tải từ file local
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                local_human = data.get("human", 0)
                local_ai = data.get("ai", 0)
    except (json.JSONDecodeError, IOError):
        pass
        
    # 2. Tải từ Database (nếu có)
    db_human, db_ai = 0, 0
    try:
        from src.database_handler import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(score) FROM highscores WHERE player_type = 'human'")
        res = cursor.fetchone()
        if res and res[0] is not None:
            db_human = res[0]
            
        cursor.execute("SELECT MAX(score) FROM highscores WHERE player_type = 'ai'")
        res = cursor.fetchone()
        if res and res[0] is not None:
            db_ai = res[0]
            
        cursor.close()
        conn.close()
    except Exception:
        pass
        
    # 3. Lấy giá trị lớn nhất
    final_human = max(local_human, db_human)
    final_ai = max(local_ai, db_ai)
    
    # Đồng bộ lại local nếu DB lớn hơn
    if final_human > local_human or final_ai > local_ai:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"human": final_human, "ai": final_ai}, f, indent=2)
        except IOError:
            pass
            
    return final_human, final_ai


def save_highscore(human=None, ai=None):
    """Lưu điểm cao (chỉ cập nhật phần được truyền vào) vào cả local và DB"""
    path = get_highscore_path()
    h, a = load_highscore()
    
    updated = False
    if human is not None and human > h:
        h = human
        updated = True
        # Lưu DB
        try:
            from src.database_handler import save_highscore_db
            save_highscore_db('human', human, 'human')
        except Exception:
            pass
            
    if ai is not None and ai > a:
        a = ai
        updated = True
        # Lưu DB
        try:
            from src.database_handler import save_highscore_db
            save_highscore_db('ai', ai, 'ai_pve')
        except Exception:
            pass
            
    if updated:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"human": h, "ai": a}, f, indent=2)
        except IOError:
            pass
