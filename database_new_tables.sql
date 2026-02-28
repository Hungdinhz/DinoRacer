-- ============================================
-- DINORACER DATABASE - NEW TABLES
-- Run this file to create additional tables for:
-- 1. Player Accounts
-- 2. Leaderboards
-- 3. Multiplayer & Tournaments
-- ============================================

-- ============================================
-- PLAYER ACCOUNTS
-- ============================================

-- Bảng users (người chơi)
CREATE TABLE IF NOT EXISTS users (
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
    total_playtime INTEGER DEFAULT 0,

    -- Settings
    is_public BOOLEAN DEFAULT TRUE,
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
CREATE TABLE IF NOT EXISTS user_profiles (
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
CREATE TABLE IF NOT EXISTS friendships (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, friend_id)
);

-- Bảng friend requests
CREATE TABLE IF NOT EXISTS friend_requests (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    to_user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(from_user_id, to_user_id)
);

-- ============================================
-- LEADERBOARDS
-- ============================================

-- Bảng global leaderboard
CREATE TABLE IF NOT EXISTS leaderboard_global (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    rank INTEGER,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(user_id, game_mode)
);

-- Bảng country/region leaderboard
CREATE TABLE IF NOT EXISTS leaderboard_country (
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
CREATE TABLE IF NOT EXISTS leaderboard_friends (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    friend_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    game_mode VARCHAR(20) NOT NULL,
    score INTEGER NOT NULL,
    rank INTEGER,
    achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng seasonal leaderboard (theo mùa)
CREATE TABLE IF NOT EXISTS leaderboard_seasonal (
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
CREATE TABLE IF NOT EXISTS multiplayer_matches (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,

    -- Match info
    match_type VARCHAR(20) NOT NULL,
    game_mode VARCHAR(20) NOT NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'waiting',

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
    duration INTEGER,

    -- Metadata
    map VARCHAR(50),
    is_ranked BOOLEAN DEFAULT FALSE
);

-- Bảng tournaments
CREATE TABLE IF NOT EXISTS tournaments (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,

    -- Tournament info
    name VARCHAR(100) NOT NULL,
    description TEXT,
    tournament_type VARCHAR(20),

    -- Settings
    max_players INTEGER DEFAULT 16,
    min_players INTEGER DEFAULT 4,
    entry_fee INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(20) DEFAULT 'draft',

    -- Prize
    prize_pool INTEGER DEFAULT 0,
    prize_distribution JSONB,

    -- Rules
    game_mode VARCHAR(20),
    rounds INTEGER,
    bracket_type VARCHAR(20)
);

-- Bảng tournament participants
CREATE TABLE IF NOT EXISTS tournament_participants (
    id SERIAL PRIMARY KEY,
    tournament_id INTEGER REFERENCES tournaments(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    seed INTEGER,
    eliminated_at TIMESTAMP,
    final_rank INTEGER,

    UNIQUE(tournament_id, user_id)
);

-- Bảng tournament matches
CREATE TABLE IF NOT EXISTS tournament_matches (
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
CREATE TABLE IF NOT EXISTS match_history (
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
-- INDEXES
-- ============================================

-- Users indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_online ON users(is_online);

-- Leaderboard indexes
CREATE INDEX IF NOT EXISTS idx_leaderboard_global_mode ON leaderboard_global(game_mode);
CREATE INDEX IF NOT EXISTS idx_leaderboard_global_rank ON leaderboard_global(rank);
CREATE INDEX IF NOT EXISTS idx_leaderboard_country ON leaderboard_country(country, game_mode);
CREATE INDEX IF NOT EXISTS idx_leaderboard_seasonal ON leaderboard_seasonal(season, game_mode);

-- Multiplayer indexes
CREATE INDEX IF NOT EXISTS idx_multiplayer_status ON multiplayer_matches(status);
CREATE INDEX IF NOT EXISTS idx_multiplayer_created ON multiplayer_matches(created_at);
CREATE INDEX IF NOT EXISTS idx_match_history_user ON match_history(user_id);
CREATE INDEX IF NOT EXISTS idx_tournaments_status ON tournaments(status);
CREATE INDEX IF NOT EXISTS idx_tournament_participants ON tournament_participants(tournament_id);

-- ============================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================

-- Insert sample users (password: 'password123')
-- INSERT INTO users (username, email, password_hash, display_name, country) VALUES
--     ('player1', 'player1@email.com', 'hash123', 'Player One', 'Vietnam'),
--     ('player2', 'player2@email.com', 'hash123', 'Player Two', 'Vietnam'),
--     ('player3', 'player3@email.com', 'hash123', 'Player Three', 'USA'),
--     ('player4', 'player4@email.com', 'hash123', 'Player Four', 'Japan');

-- Create user profiles for sample users
-- INSERT INTO user_profiles (user_id, country) VALUES
--     (1, 'Vietnam'),
--     (2, 'Vietnam'),
--     (3, 'USA'),
--     (4, 'Japan');

-- ============================================
-- QUERY EXAMPLES
-- ============================================

-- === USER ACCOUNTS ===

-- Đăng ký user mới:
-- INSERT INTO users (username, email, password_hash, display_name)
-- VALUES ('newplayer', 'newplayer@email.com', 'hashed_password', 'New Player');

-- Cập nhật profile:
-- UPDATE user_profiles
-- SET country = 'Vietnam', region = 'Ho Chi Minh'
-- WHERE user_id = 1;

-- Gửi lời mời kết bạn:
-- INSERT INTO friend_requests (from_user_id, to_user_id, message)
-- VALUES (1, 2, 'Let be friends!');

-- Lấy danh sách bạn bè:
-- SELECT u.id, u.username, u.display_name, u.avatar_url, u.total_games, u.total_wins
-- FROM users u
-- JOIN friendships f ON u.id = f.friend_id
-- WHERE f.user_id = 1 AND f.status = 'accepted';

-- === LEADERBOARDS ===

-- Lấy global leaderboard top 10:
-- SELECT u.username, u.display_name, lg.score, lg.rank
-- FROM leaderboard_global lg
-- JOIN users u ON lg.user_id = u.id
-- WHERE lg.game_mode = 'endless'
-- ORDER BY lg.rank
-- LIMIT 10;

-- Lấy leaderboard theo quốc gia:
-- SELECT u.username, u.display_name, lc.score, lc.rank
-- FROM leaderboard_country lc
-- JOIN users u ON lc.user_id = u.id
-- WHERE lc.country = 'Vietnam' AND lc.game_mode = 'endless'
-- ORDER BY lc.rank
-- LIMIT 10;

-- Lấy leaderboard bạn bè:
-- SELECT u.username, u.display_name, lf.score, lf.rank
-- FROM leaderboard_friends lf
-- JOIN users u ON lf.user_id = u.id
-- WHERE lf.user_id = 1 AND lf.game_mode = 'pvp'
-- ORDER BY lf.rank
-- LIMIT 10;

-- === MULTIPLAYER & TOURNAMENTS ===

-- Tạo multiplayer match:
-- INSERT INTO multiplayer_matches (match_type, game_mode, player1_id, player2_id, status)
-- VALUES ('1v1', 'pvp', 1, 2, 'in_progress');

-- Cập nhật kết quả match:
-- UPDATE multiplayer_matches
-- SET winner_id = 1, player1_score = 150, player2_score = 120,
--     status = 'finished', finished_at = CURRENT_TIMESTAMP, duration = 60
-- WHERE id = 1;

-- Tạo tournament:
-- INSERT INTO tournaments (name, description, tournament_type, max_players, game_mode, status)
-- VALUES ('Dino Championship 2024', 'Weekly tournament', 'single_elimination', 16, 'endless', 'registration');

-- Tham gia tournament:
-- INSERT INTO tournament_participants (tournament_id, user_id, seed)
-- VALUES (1, 1, 1), (1, 2, 2);

-- Lấy lịch sử đấu của user:
-- SELECT mm.match_type, mm.game_mode, mm.player1_score, mm.player2_score,
--        mm.duration, mm.created_at,
--        CASE WHEN mm.winner_id = 1 THEN 'Win' ELSE 'Loss' END as result
-- FROM match_history mh
-- JOIN multiplayer_matches mm ON mh.match_id = mm.id
-- WHERE mh.user_id = 1
-- ORDER BY mm.created_at DESC
-- LIMIT 20;

-- Lấy danh sách tournament đang mở:
-- SELECT * FROM tournaments
-- WHERE status IN ('registration', 'in_progress')
-- ORDER BY created_at DESC;
