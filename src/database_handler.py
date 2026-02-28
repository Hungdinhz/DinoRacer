"""
Database Handler - Ket noi va thao tac voi Neon.tech PostgreSQL
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL not found")
    
    try:
        # Use connection string directly - psycopg2 supports it
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS training_data (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            distance_to_obstacle FLOAT NOT NULL,
            obstacle_type FLOAT NOT NULL,
            game_speed FLOAT NOT NULL,
            dino_height FLOAT NOT NULL,
            is_jumping FLOAT NOT NULL,
            is_ducking FLOAT NOT NULL,
            action_jump INTEGER NOT NULL,
            action_duck INTEGER NOT NULL,
            source VARCHAR(20) NOT NULL,
            game_speed_raw FLOAT,
            score INTEGER,
            quality_score FLOAT DEFAULT 1.0
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_training_source ON training_data(source)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS highscores (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            player_type VARCHAR(20) NOT NULL,
            score INTEGER NOT NULL,
            game_mode VARCHAR(20) NOT NULL,
            game_duration INTEGER,
            CONSTRAINT unique_highscore UNIQUE (player_type, game_mode)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_sessions (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            game_mode VARCHAR(20) NOT NULL,
            player_type VARCHAR(20) NOT NULL,
            score INTEGER NOT NULL,
            is_winner BOOLEAN,
            game_duration INTEGER,
            obstacles_passed INTEGER DEFAULT 0,
            jumps_count INTEGER DEFAULT 0,
            ducks_count INTEGER DEFAULT 0,
            end_reason VARCHAR(20)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_game_mode ON game_sessions(game_mode)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS game_settings (
            id SERIAL PRIMARY KEY,
            key VARCHAR(50) UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT
        )
    """)
    cursor.execute("""
        INSERT INTO game_settings (key, value, description) 
        VALUES 
            ('difficulty', 'normal', 'Do kho'),
            ('sound_enabled', 'true', 'Bat tat am thanh'),
            ('data_collection_enabled', 'true', 'Bat tat thu thap')
        ON CONFLICT (key) DO NOTHING
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("Database initialized!")

def save_training_data(data_list):
    if not data_list:
        return 0
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO training_data 
        (distance_to_obstacle, obstacle_type, game_speed, dino_height, 
         is_jumping, is_ducking, action_jump, action_duck, source, 
         game_speed_raw, score, quality_score)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    count = 0
    for data in data_list:
        try:
            cursor.execute(query, (
                data.get("distance_to_obstacle"),
                data.get("obstacle_type"),
                data.get("game_speed"),
                data.get("dino_height"),
                data.get("is_jumping"),
                data.get("is_ducking"),
                data.get("action_jump"),
                data.get("action_duck"),
                data.get("source"),
                data.get("game_speed_raw"),
                data.get("score"),
                data.get("quality_score", 1.0)
            ))
            count += 1
        except Exception as e:
            print(f"Error: {e}")
    conn.commit()
    cursor.close()
    conn.close()
    return count

def get_training_data_count(source=None):
    conn = get_connection()
    cursor = conn.cursor()
    if source:
        cursor.execute("SELECT COUNT(*) FROM training_data WHERE source = %s", (source,))
    else:
        cursor.execute("SELECT COUNT(*) FROM training_data")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count

def save_highscore_db(player_type, score, game_mode, game_duration=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, score FROM highscores WHERE player_type = %s AND game_mode = %s", (player_type, game_mode))
    existing = cursor.fetchone()
    if existing:
        if score > existing[1]:
            cursor.execute("UPDATE highscores SET score = %s, game_duration = %s WHERE player_type = %s AND game_mode = %s", 
                         (score, game_duration, player_type, game_mode))
    else:
        cursor.execute("INSERT INTO highscores (player_type, score, game_mode, game_duration) VALUES (%s, %s, %s, %s)", 
                     (player_type, score, game_mode, game_duration))
    conn.commit()
    cursor.close()
    conn.close()

def save_game_session(game_mode, player_type, score, is_winner=None, game_duration=None, end_reason=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO game_sessions (game_mode, player_type, score, is_winner, game_duration, end_reason)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (game_mode, player_type, score, is_winner, game_duration, end_reason))
    conn.commit()
    cursor.close()
    conn.close()

def get_setting(key, default=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM game_settings WHERE key = %s", (key,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result[0] if result else default

def set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO game_settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = %s", 
                 (key, value, value))
    conn.commit()
    cursor.close()
    conn.close()

def test_connection():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT version()')
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        return True, version[0]
    except Exception as e:
        return False, str(e)


# ============================================
# USER MANAGEMENT
# ============================================

def create_user(username, email, password_hash, display_name=None, country=None):
    """Tạo user mới"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, display_name, country)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (username, email, password_hash, display_name or username, country))

        user_id = cursor.fetchone()[0]

        # Tạo profile
        cursor.execute("""
            INSERT INTO user_profiles (user_id, country)
            VALUES (%s, %s)
        """, (user_id, country))

        conn.commit()
        cursor.close()
        conn.close()
        return user_id
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        raise e


def get_user_by_username(username):
    """Lấy user theo username"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_user_by_email(email):
    """Lấy user theo email"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_user_profile(user_id):
    """Lấy profile của user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.*, up.*
        FROM users u
        LEFT JOIN user_profiles up ON u.id = up.user_id
        WHERE u.id = %s
    """, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result


def update_user_profile(user_id, **kwargs):
    """Cập nhật profile"""
    conn = get_connection()
    cursor = conn.cursor()

    # Cập nhật users table
    user_fields = ['display_name', 'avatar_url', 'bio', 'is_public']
    user_updates = []
    user_values = []
    for field in user_fields:
        if field in kwargs:
            user_updates.append(f"{field} = %s")
            user_values.append(kwargs[field])

    if user_updates:
        user_values.append(user_id)
        cursor.execute(f"UPDATE users SET {', '.join(user_updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s", user_values)

    # Cập nhật user_profiles table
    profile_fields = ['preferred_difficulty', 'preferred_controls', 'country', 'region']
    profile_updates = []
    profile_values = []
    for field in profile_fields:
        if field in kwargs:
            profile_updates.append(f"{field} = %s")
            profile_values.append(kwargs[field])

    if profile_updates:
        profile_values.append(user_id)
        cursor.execute(f"UPDATE user_profiles SET {', '.join(profile_updates)}, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", profile_values)

    conn.commit()
    cursor.close()
    conn.close()


def update_user_stats(user_id, game_mode, score, is_winner, duration, jumps=0, ducks=0, obstacles=0):
    """Cập nhật stats sau khi chơi"""
    conn = get_connection()
    cursor = conn.cursor()

    # Update users table
    cursor.execute("""
        UPDATE users SET
            total_games = total_games + 1,
            total_wins = total_wins + %s,
            total_playtime = total_playtime + %s,
            last_seen = CURRENT_TIMESTAMP
        WHERE id = %s
    """, (1 if is_winner else 0, duration, user_id))

    # Update user_profiles theo game_mode
    if game_mode == 'pve':
        cursor.execute("""
            UPDATE user_profiles SET
                pve_games = pve_games + 1,
                pve_wins = pve_wins + %s,
                pve_best_score = GREATEST(pve_best_score, %s)
            WHERE user_id = %s
        """, (1 if is_winner else 0, score, user_id))
    elif game_mode == 'pvp':
        cursor.execute("""
            UPDATE user_profiles SET
                pvp_games = pvp_games + 1,
                pvp_wins = pvp_wins + %s,
                pvp_best_score = GREATEST(pvp_best_score, %s)
            WHERE user_id = %s
        """, (1 if is_winner else 0, score, user_id))
    elif game_mode == 'endless':
        cursor.execute("""
            UPDATE user_profiles SET
                endless_games = endless_games + 1,
                endless_best_score = GREATEST(endless_best_score, %s)
            WHERE user_id = %s
        """, (score, user_id))
    elif game_mode == 'time_attack':
        cursor.execute("""
            UPDATE user_profiles SET
                time_attack_games = time_attack_games + 1,
                time_attack_best_score = GREATEST(time_attack_best_score, %s)
            WHERE user_id = %s
        """, (score, user_id))

    conn.commit()
    cursor.close()
    conn.close()


# ============================================
# FRIENDS SYSTEM
# ============================================

def send_friend_request(from_user_id, to_user_id, message=None):
    """Gửi lời mời kết bạn"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO friend_requests (from_user_id, to_user_id, message)
            VALUES (%s, %s, %s)
        """, (from_user_id, to_user_id, message))
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False


def accept_friend_request(request_id):
    """Chấp nhận lời mời kết bạn"""
    conn = get_connection()
    cursor = conn.cursor()

    # Lấy thông tin request
    cursor.execute("SELECT from_user_id, to_user_id FROM friend_requests WHERE id = %s", (request_id,))
    request = cursor.fetchone()
    if not request:
        cursor.close()
        conn.close()
        return False

    from_user_id, to_user_id = request

    # Thêm vào friendships
    cursor.execute("""
        INSERT INTO friendships (user_id, friend_id, status)
        VALUES (%s, %s, 'accepted'), (%s, %s, 'accepted')
    """, (from_user_id, to_user_id, to_user_id, from_user_id))

    # Xóa request
    cursor.execute("UPDATE friend_requests SET status = 'accepted' WHERE id = %s", (request_id,))

    # Cập nhật friends_count
    cursor.execute("UPDATE users SET friends_count = friends_count + 1 WHERE id IN (%s, %s)", (from_user_id, to_user_id))

    conn.commit()
    cursor.close()
    conn.close()
    return True


def get_friends(user_id):
    """Lấy danh sách bạn bè"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.username, u.display_name, u.avatar_url, u.is_online, u.last_seen
        FROM users u
        JOIN friendships f ON u.id = f.friend_id
        WHERE f.user_id = %s AND f.status = 'accepted'
    """, (user_id,))
    friends = cursor.fetchall()
    cursor.close()
    conn.close()
    return friends


def get_friend_requests(user_id):
    """Lấy danh sách lời mời kết bạn"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fr.id, fr.message, fr.created_at, u.username, u.display_name, u.avatar_url
        FROM friend_requests fr
        JOIN users u ON fr.from_user_id = u.id
        WHERE fr.to_user_id = %s AND fr.status = 'pending'
        ORDER BY fr.created_at DESC
    """, (user_id,))
    requests = cursor.fetchall()
    cursor.close()
    conn.close()
    return requests


# ============================================
# LEADERBOARDS
# ============================================

def update_leaderboard(user_id, game_mode, score):
    """Cập nhật điểm leaderboard toàn cầu"""
    conn = get_connection()
    cursor = conn.cursor()

    # Check existing score
    cursor.execute("""
        SELECT score FROM leaderboard_global
        WHERE user_id = %s AND game_mode = %s
    """, (user_id, game_mode))
    existing = cursor.fetchone()

    if existing and score > existing[0]:
        cursor.execute("""
            UPDATE leaderboard_global SET score = %s, achieved_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND game_mode = %s
        """, (score, user_id, game_mode))
    elif not existing:
        cursor.execute("""
            INSERT INTO leaderboard_global (user_id, game_mode, score)
            VALUES (%s, %s, %s)
        """, (user_id, game_mode, score))

    conn.commit()
    cursor.close()
    conn.close()


def update_country_leaderboard(user_id, country, game_mode, score):
    """Cập nhật leaderboard theo quốc gia"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT score FROM leaderboard_country
        WHERE user_id = %s AND country = %s AND game_mode = %s
    """, (user_id, country, game_mode))
    existing = cursor.fetchone()

    if existing and score > existing[0]:
        cursor.execute("""
            UPDATE leaderboard_country SET score = %s, achieved_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND country = %s AND game_mode = %s
        """, (score, user_id, country, game_mode))
    elif not existing:
        cursor.execute("""
            INSERT INTO leaderboard_country (user_id, country, game_mode, score)
            VALUES (%s, %s, %s, %s)
        """, (user_id, country, game_mode, score))

    conn.commit()
    cursor.close()
    conn.close()


def get_global_leaderboard(game_mode, limit=10):
    """Lấy top leaderboard toàn cầu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT lg.rank, u.username, u.display_name, u.avatar_url, lg.score, lg.achieved_at
        FROM leaderboard_global lg
        JOIN users u ON lg.user_id = u.id
        WHERE lg.game_mode = %s
        ORDER BY lg.score DESC
        LIMIT %s
    """, (game_mode, limit))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_country_leaderboard(country, game_mode, limit=10):
    """Lấy top leaderboard theo quốc gia"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT lc.rank, u.username, u.display_name, u.avatar_url, lc.score, lc.achieved_at
        FROM leaderboard_country lc
        JOIN users u ON lc.user_id = u.id
        WHERE lc.country = %s AND lc.game_mode = %s
        ORDER BY lc.score DESC
        LIMIT %s
    """, (country, game_mode, limit))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_friends_leaderboard(user_id, game_mode, limit=10):
    """Lấy top leaderboard bạn bè"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT lf.rank, u.username, u.display_name, u.avatar_url, lf.score
        FROM leaderboard_friends lf
        JOIN users u ON lf.user_id = u.id
        WHERE lf.friend_id = %s AND lf.game_mode = %s
        ORDER BY lf.score DESC
        LIMIT %s
    """, (user_id, game_mode, limit))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


# ============================================
# MULTIPLAYER & TOURNAMENTS
# ============================================

def create_multiplayer_match(match_type, game_mode, player1_id, player2_id):
    """Tạo trận multiplayer"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO multiplayer_matches (match_type, game_mode, player1_id, player2_id, status)
        VALUES (%s, %s, %s, %s, 'waiting')
        RETURNING id
    """, (match_type, game_mode, player1_id, player2_id))
    match_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return match_id


def start_match(match_id):
    """Bắt đầu trận đấu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE multiplayer_matches SET status = 'in_progress'
        WHERE id = %s
    """, (match_id,))
    conn.commit()
    cursor.close()
    conn.close()


def finish_match(match_id, winner_id, player1_score, player2_score, duration):
    """Kết thúc trận đấu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE multiplayer_matches SET
            winner_id = %s,
            player1_score = %s,
            player2_score = %s,
            status = 'finished',
            finished_at = CURRENT_TIMESTAMP,
            duration = %s
        WHERE id = %s
    """, (winner_id, player1_score, player2_score, duration, match_id))
    conn.commit()
    cursor.close()
    conn.close()


def save_match_history(user_id, match_id, is_winner, score, rank, jumps, ducks, obstacles, duration):
    """Lưu lịch sử trận đấu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO match_history (user_id, match_id, is_winner, score, rank, jumps_count, ducks_count, obstacles_passed, duration)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (user_id, match_id, is_winner, score, rank, jumps, ducks, obstacles, duration))
    conn.commit()
    cursor.close()
    conn.close()


def get_match_history(user_id, limit=20):
    """Lấy lịch sử trận đấu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mm.id, mm.match_type, mm.game_mode, mm.player1_score, mm.player2_score,
               mm.duration, mm.created_at, mm.winner_id, mh.is_winner, mh.score
        FROM match_history mh
        JOIN multiplayer_matches mm ON mh.match_id = mm.id
        WHERE mh.user_id = %s
        ORDER BY mm.created_at DESC
        LIMIT %s
    """, (user_id, limit))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def create_tournament(name, description, tournament_type, max_players, game_mode, entry_fee=0):
    """Tạo giải đấu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tournaments (name, description, tournament_type, max_players, game_mode, entry_fee, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'registration')
        RETURNING id
    """, (name, description, tournament_type, max_players, game_mode, entry_fee))
    tournament_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return tournament_id


def join_tournament(tournament_id, user_id):
    """Tham gia giải đấu"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tournament_participants (tournament_id, user_id)
        VALUES (%s, %s)
    """, (tournament_id, user_id))
    conn.commit()
    cursor.close()
    conn.close()


def get_active_tournaments():
    """Lấy danh sách giải đấu đang hoạt động"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, description, tournament_type, max_players, game_mode, entry_fee, status
        FROM tournaments
        WHERE status IN ('registration', 'in_progress')
        ORDER BY created_at DESC
    """)
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


def get_tournament_matches(tournament_id):
    """Lấy danh sách trận đấu trong giải"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tm.round, tm.match_number, u1.username as player1, u2.username as player2,
               tm.winner_id, tm.player1_score, tm.player2_score, tm.status
        FROM tournament_matches tm
        LEFT JOIN users u1 ON tm.player1_id = u1.id
        LEFT JOIN users u2 ON tm.player2_id = u2.id
        WHERE tm.tournament_id = %s
        ORDER BY tm.round, tm.match_number
    """, (tournament_id,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


if __name__ == "__main__":
    success, result = test_connection()
    if success:
        print(f"Connected! {result}")
        init_database()
    else:
        print(f"Failed: {result}")