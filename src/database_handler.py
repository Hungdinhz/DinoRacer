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

if __name__ == "__main__":
    success, result = test_connection()
    if success:
        print(f"Connected! {result}")
        init_database()
    else:
        print(f"Failed: {result}")