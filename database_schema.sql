-- ============================================
-- DATABASE SCHEMA FOR DINORACER
-- Created for Neon.tech PostgreSQL
-- ============================================

-- 1. Bảng lưu dữ liệu training (thu thập từ người chơi và AI)
CREATE TABLE training_data (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Input features (6 values)
    distance_to_obstacle FLOAT NOT NULL,        -- Khoảng cách đến obstacle (0-1)
    obstacle_type FLOAT NOT NULL,              -- Loại obstacle: 0=Cactus, 1=Bird (0-1)
    game_speed FLOAT NOT NULL,                 -- Tốc độ game (0-1)
    dino_height FLOAT NOT NULL,               -- Độ cao dino (0-1)
    is_jumping FLOAT NOT NULL,                 -- Đang nhảy: 0 hoặc 1
    is_ducking FLOAT NOT NULL,                -- Đang cúi: 0 hoặc 1
    
    -- Output labels (actions)
    action_jump INTEGER NOT NULL,              -- Hành động nhảy: 0 hoặc 1
    action_duck INTEGER NOT NULL,              -- Hành động cúi: 0 hoặc 1
    
    -- Metadata
    source VARCHAR(20) NOT NULL,               -- 'human' hoặc 'ai'
    game_speed_raw FLOAT,                      -- Tốc độ game thực tế
    score INTEGER,                              -- Điểm số tại thời điểm thu thập
    quality_score FLOAT DEFAULT 1.0            -- Chất lượng dữ liệu (0-1)
);

-- Index để tăng tốc truy vấn training
CREATE INDEX idx_training_source ON training_data(source);
CREATE INDEX idx_training_created ON training_data(created_at);

-- 2. Bảng lưu high scores
CREATE TABLE highscores (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    player_type VARCHAR(20) NOT NULL,          -- 'human', 'ai_pve', 'ai_pvp'
    score INTEGER NOT NULL,
    game_mode VARCHAR(20) NOT NULL,             -- 'pve', 'pvp', 'endless'
    game_duration INTEGER,                     -- Thời gian chơi (giây)
    
    CONSTRAINT unique_highscore UNIQUE (player_type, game_mode)
);

-- 3. Bảng lưu thống kê người chơi
CREATE TABLE player_stats (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Tổng quan
    total_games INTEGER DEFAULT 0,              -- Tổng số trận đã chơi
    total_playtime INTEGER DEFAULT 0,           -- Tổng thời gian chơi (giây)
    total_score INTEGER DEFAULT 0,              -- Tổng điểm
    
    -- Chi tiết chế độ chơi
    pve_games INTEGER DEFAULT 0,
    pvp_games INTEGER DEFAULT 0,
    pve_wins INTEGER DEFAULT 0,
    pvp_wins INTEGER DEFAULT 0,
    
    -- Thống kê hành động
    total_jumps INTEGER DEFAULT 0,
    total_ducks INTEGER DEFAULT 0,
    total_obstacles_passed INTEGER DEFAULT 0,
    
    -- AI Stats
    ai_training_samples INTEGER DEFAULT 0,     -- Số mẫu đã thu thập
    
    -- Streaks
    current_streak INTEGER DEFAULT 0,          -- Chuỗi thắng hiện tại
    best_streak INTEGER DEFAULT 0              -- Chuỗi thắng tốt nhất
);

-- 4. Bảng lưu lịch sử ván chơi
CREATE TABLE game_sessions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    game_mode VARCHAR(20) NOT NULL,            -- 'pve', 'pvp', 'endless'
    player_type VARCHAR(20) NOT NULL,          -- 'human', 'ai'
    
    -- Kết quả
    score INTEGER NOT NULL,
    is_winner BOOLEAN,
    game_duration INTEGER,                     -- Thời gian chơi (giây)
    
    -- Chi tiết
    obstacles_passed INTEGER DEFAULT 0,
    jumps_count INTEGER DEFAULT 0,
    ducks_count INTEGER DEFAULT 0,
    game_speed_max FLOAT DEFAULT 0,
    
    -- Điều kiện kết thúc
    end_reason VARCHAR(20),                   -- 'collision', 'timeout', 'quit'
    
    -- Metadata
    game_version VARCHAR(20) DEFAULT '1.0'
);

-- Index cho game sessions
CREATE INDEX idx_sessions_game_mode ON game_sessions(game_mode);
CREATE INDEX idx_sessions_created ON game_sessions(created_at);

-- 5. Bảng cấu hình game
CREATE TABLE game_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT INTO game_settings (key, value, description) VALUES
    ('difficulty', 'normal', 'Độ khó: easy, normal, hard'),
    ('sound_enabled', 'true', 'Bật/tắt âm thanh'),
    ('music_enabled', 'true', 'Bật/tắt nhạc nền'),
    ('data_collection_enabled', 'true', 'Bật/tắt thu thập dữ liệu training'),
    ('ai_difficulty', 'medium', 'Độ khó AI: easy, medium, hard');

-- 6. Bảng lưu genome AI (đã train)
CREATE TABLE ai_genomes (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    genome_name VARCHAR(100) NOT NULL,
    fitness_score FLOAT NOT NULL,
    generation INTEGER,
    
    -- Genome data (có thể lưu JSON hoặc binary)
    genome_data JSONB,
    config JSONB,
    
    is_active BOOLEAN DEFAULT FALSE,
    description TEXT
);

-- ============================================
-- VIEWS TIỆN ÍCH
-- ============================================

-- View lấy dữ liệu training sạch (chất lượng cao)
CREATE OR REPLACE VIEW clean_training_data AS
SELECT 
    id,
    distance_to_obstacle,
    obstacle_type,
    game_speed,
    dino_height,
    is_jumping,
    is_ducking,
    action_jump,
    action_duck,
    source
FROM training_data
WHERE quality_score >= 0.8
ORDER BY created_at DESC;

-- View thống kê người chơi
CREATE OR REPLACE VIEW player_statistics AS
SELECT 
    'human' as player_type,
    COUNT(*) as total_games,
    SUM(CASE WHEN is_winner THEN 1 ELSE 0 END) as wins,
    AVG(score) as avg_score,
    MAX(score) as best_score,
    SUM(game_duration) as total_playtime
FROM game_sessions
WHERE player_type = 'human'
GROUP BY player_type;

-- ============================================
-- FUNCTIONS TIỆN ÍCH
-- ============================================

-- Function cập nhật player stats
CREATE OR REPLACE FUNCTION update_player_stats()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE player_stats 
    SET 
        total_games = total_games + 1,
        total_playtime = total_playtime + COALESCE(NEW.game_duration, 0),
        total_score = total_score + NEW.score,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = 1;
    
    -- Cập nhật stats theo game mode
    IF NEW.game_mode = 'pve' THEN
        UPDATE player_stats SET pve_games = pve_games + 1 WHERE id = 1;
    ELSIF NEW.game_mode = 'pvp' THEN
        UPDATE player_stats SET pvp_games = pvp_games + 1 WHERE id = 1;
    END IF;
    
    -- Cập nhật wins
    IF NEW.is_winner THEN
        UPDATE player_stats 
        SET current_streak = current_streak + 1,
            best_streak = GREATEST(best_streak, current_streak + 1)
        WHERE id = 1;
    ELSE
        UPDATE player_stats SET current_streak = 0 WHERE id = 1;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger để tự động cập nhật stats
CREATE TRIGGER trigger_update_stats
AFTER INSERT ON game_sessions
FOR EACH ROW
EXECUTE FUNCTION update_player_stats();

-- ============================================
-- QUERY MẪU
-- ============================================

-- Lấy dữ liệu training cho AI
SELECT 
    ARRAY[distance_to_obstacle, obstacle_type, game_speed, dino_height, is_jumping, is_ducking] as inputs,
    ARRAY[action_jump, action_duck] as outputs
FROM training_data
WHERE source = 'human'
ORDER BY RANDOM()
LIMIT 10000;

-- Lấy top scores
SELECT * FROM highscores
ORDER BY score DESC
LIMIT 10;

-- Thống kê dữ liệu đã thu thập
SELECT 
    source,
    COUNT(*) as total_samples,
    AVG(game_speed_raw) as avg_speed,
    SUM(CASE WHEN action_jump = 1 THEN 1 ELSE 0 END) as total_jumps,
    SUM(CASE WHEN action_duck = 1 THEN 1 ELSE 0 END) as total_ducks
FROM training_data
GROUP BY source;
