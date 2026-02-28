-- ============================================
-- DATABASE SCHEMA FOR DINORACER
-- Created for Neon.tech PostgreSQL
-- ============================================

-- ============================================
-- PLAYER ACCOUNTS
-- ============================================

-- Bảng users (người chơi)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Authentication
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Profile
    display_name VARCHAR(50),
    avatar_url VARCHAR(255),
    bio TEXT,

    -- Stats
    total_games INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_playtime INTEGER DEFAULT 0,  -- seconds

    -- Settings
    is_public BOOLEAN DEFAULT TRUE,    -- Public profile
    is_online BOOLEAN DEFAULT FALSE,

    -- Social
    friends_count INTEGER DEFAULT 0,
    followers_count INTEGER DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP,
    last_seen TIMESTAMP
);

-- Bảng user profiles (thông tin chi tiết)
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,

    -- Game preferences
    preferred_difficulty VARCHAR(20) DEFAULT 'normal',
    preferred_controls VARCHAR(20) DEFAULT 'keyboard',

    -- Statistics by game mode
    pve_games INTEGER DEFAULT 0,
    pve_wins INTEGER DEFAULT 0,
    pve_best_score INTEGER DEFAULT 0,

    pvp_games INTEGER DEFAULT 0,
    pvp_wins INTEGER DEFAULT 0,
    pvp_best_score INTEGER DEFAULT 0,

    endless_games INTEGER DEFAULT 0,
    endless_best_score INTEGER DEFAULT 0,

    time_attack_games INTEGER DEFAULT 0,
    time_attack_best_score INTEGER DEFAULT 0,

    -- Achievements count
    achievements_unlocked INTEGER DEFAULT 0,

    -- Country/Region
    country VARCHAR(50),
    region VARCHAR(50),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng friends (bạn bè)
CREATE TABLE friendships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, blocked
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, friend_id)
);

-- Bảng friend requests
CREATE TABLE friend_requests (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    to_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, rejected
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(from_user_id, to_user_id)
);

-- ============================================
-- LEADERBOARDS
-- ============================================

-- Bảng global leaderboard
CREATE TABLE leaderboard_global (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(20) NOT NULL,  -- pve, pvp, endless, time_attack
    score INTEGER NOT NULL,
    rank INTEGER,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, game_mode)
);

-- Bảng country/region leaderboard
CREATE TABLE leaderboard_country (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    country VARCHAR(50) NOT NULL,
    game_mode VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    rank INTEGER,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, country, game_mode)
);

-- Bảng friends leaderboard
CREATE TABLE leaderboard_friends (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    rank INTEGER,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng seasonal leaderboard (theo mùa)
CREATE TABLE leaderboard_seasonal (
    id SERIAL PRIMARY KEY,
    season VARCHAR(20) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    rank INTEGER,
    rewards_claimed BOOLEAN DEFAULT FALSE,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(season, user_id, game_mode)
);

-- ============================================
-- MULTIPLAYER HISTORY
-- ============================================

-- Bảng multiplayer matches
CREATE TABLE multiplayer_matches (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,

    -- Match info
    match_type VARCHAR(20) NOT NULL,  -- 1v1, 2v2, tournament
    game_mode VARCHAR(20) NOT NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'waiting',  -- waiting, in_progress, finished, cancelled

    -- Players
    player1_id INTEGER REFERENCES users(id),
    player2_id INTEGER REFERENCES users(id),
    player3_id INTEGER REFERENCES users(id),
    player4_id INTEGER REFERENCES users(id),

    -- Results
    winner_id INTEGER REFERENCES users(id),
    player1_score INTEGER,
    player2_score INTEGER,
    player3_score INTEGER,
    player4_score INTEGER,

    -- Duration
    duration INTEGER,  -- seconds

    -- Metadata
    map VARCHAR(50),
    is_ranked BOOLEAN DEFAULT FALSE
);

-- Bảng tournaments
CREATE TABLE tournaments (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,

    -- Tournament info
    name VARCHAR(100) NOT NULL,
    description TEXT,
    tournament_type VARCHAR(20),  -- single_elimination, double_elimination, round_robin

    -- Settings
    max_players INTEGER DEFAULT 16,
    min_players INTEGER DEFAULT 4,
    entry_fee INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft, registration, in_progress, finished, cancelled

    -- Prize
    prize_pool INTEGER DEFAULT 0,
    prize_distribution JSONB,  -- e.g. {"1": 50, "2": 30, "3": 20}

    -- Rules
    game_mode VARCHAR(20),
    rounds INTEGER,
    bracket_type VARCHAR(20)
);

-- Bảng tournament participants
CREATE TABLE tournament_participants (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    seed INTEGER,  -- Seed number
    eliminated_at TIMESTAMP,
    final_rank INTEGER,

    UNIQUE(tournament_id, user_id)
);

-- Bảng tournament matches
CREATE TABLE tournament_matches (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    round INTEGER NOT NULL,
    match_number INTEGER NOT NULL,

    player1_id INTEGER REFERENCES users(id),
    player2_id INTEGER REFERENCES users(id),
    winner_id INTEGER REFERENCES users(id),

    player1_score INTEGER,
    player2_score INTEGER,

    status VARCHAR(20) DEFAULT 'pending',
    played_at TIMESTAMP,

    UNIQUE(tournament_id, round, match_number)
);

-- Bảng match history (cho từng user)
CREATE TABLE match_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    match_id INTEGER REFERENCES multiplayer_matches(id) ON DELETE SET NULL,

    -- Match result
    is_winner BOOLEAN,
    score INTEGER,
    rank INTEGER,

    -- Actions
    jumps_count INTEGER DEFAULT 0,
    ducks_count INTEGER DEFAULT 0,
    obstacles_passed INTEGER DEFAULT 0,

    -- Duration
    duration INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- EXISTING TABLES (keeping for reference)
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
-- QUERY MẪU CHO TÍNH NĂNG MỚI
-- ============================================

-- === USER ACCOUNTS ===

-- Đăng ký user mới
INSERT INTO users (username, email, password_hash, display_name)
VALUES ('player1', 'player1@email.com', 'hash123', 'Player One');

-- Cập nhật profile
UPDATE user_profiles
SET country = 'Vietnam', region = 'Ho Chi Minh'
WHERE user_id = 1;

-- Gửi lời mời kết bạn
INSERT INTO friend_requests (from_user_id, to_user_id, message)
VALUES (1, 2, 'Let be friends!');

-- Chấp nhận friend request
UPDATE friendships
SET status = 'accepted', updated_at = CURRENT_TIMESTAMP
WHERE id = 1;

-- Lấy danh sách bạn bè
SELECT u.id, u.username, u.display_name, u.avatar_url, u.total_games, u.total_wins
FROM users u
JOIN friendships f ON u.id = f.friend_id
WHERE f.user_id = 1 AND f.status = 'accepted';

-- === LEADERBOARDS ===

-- Lấy global leaderboard top 10
SELECT
    u.username,
    u.display_name,
    u.avatar_url,
    lg.score,
    lg.rank,
    lg.achieved_at
FROM leaderboard_global lg
JOIN users u ON lg.user_id = u.id
WHERE lg.game_mode = 'endless'
ORDER BY lg.rank
LIMIT 10;

-- Lấy leaderboard theo quốc gia
SELECT
    u.username,
    u.display_name,
    lc.score,
    lc.rank
FROM leaderboard_country lc
JOIN users u ON lc.user_id = u.id
WHERE lc.country = 'Vietnam' AND lc.game_mode = 'endless'
ORDER BY lc.rank
LIMIT 10;

-- Lấy leaderboard bạn bè
SELECT
    u.username,
    u.display_name,
    lf.score,
    lf.rank
FROM leaderboard_friends lf
JOIN users u ON lf.user_id = u.id
WHERE lf.user_id = 1 AND lf.game_mode = 'pvp'
ORDER BY lf.rank
LIMIT 10;

-- Lấy seasonal leaderboard
SELECT
    u.username,
    ls.score,
    ls.rank,
    ls.rewards_claimed
FROM leaderboard_seasonal ls
JOIN users u ON ls.user_id = u.id
WHERE ls.season = 'season_1' AND ls.game_mode = 'endless'
ORDER BY ls.rank
LIMIT 10;

-- === MULTIPLAYER & TOURNAMENTS ===

-- Tạo multiplayer match
INSERT INTO multiplayer_matches (match_type, game_mode, player1_id, player2_id, status)
VALUES ('1v1', 'pvp', 1, 2, 'in_progress');

-- Cập nhật kết quả match
UPDATE multiplayer_matches
SET winner_id = 1,
    player1_score = 150,
    player2_score = 120,
    status = 'finished',
    finished_at = CURRENT_TIMESTAMP,
    duration = 60
WHERE id = 1;

-- Tạo tournament
INSERT INTO tournaments (name, description, tournament_type, max_players, game_mode, status)
VALUES ('Dino Championship 2024', 'Weekly tournament', 'single_elimination', 16, 'endless', 'registration');

-- Tham gia tournament
INSERT INTO tournament_participants (tournament_id, user_id, seed)
VALUES (1, 1, 1), (1, 2, 2), (1, 3, 3), (1, 4, 4);

-- Lấy lịch sử đấu của user
SELECT
    mm.id,
    mm.match_type,
    mm.game_mode,
    mm.player1_score,
    mm.player2_score,
    mm.duration,
    mm.created_at,
    CASE
        WHEN mm.winner_id = 1 THEN 'Win'
        ELSE 'Loss'
    END as result
FROM match_history mh
JOIN multiplayer_matches mm ON mh.match_id = mm.id
WHERE mh.user_id = 1
ORDER BY mm.created_at DESC
LIMIT 20;

-- Lấy danh sách tournament đang mở
SELECT *
FROM tournaments
WHERE status IN ('registration', 'in_progress')
ORDER BY created_at DESC;

-- Lấy kết quả tournament
SELECT
    tp.user_id,
    u.username,
    tp.final_rank
FROM tournament_participants tp
JOIN users u ON tp.user_id = u.id
WHERE tp.tournament_id = 1
ORDER BY tp.final_rank;

-- ============================================
-- QUERY MẪU CŨ
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
