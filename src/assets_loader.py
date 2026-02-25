"""
Assets Loader - Tải sprites và âm thanh, fallback nếu không có file
Thêm file vào assets/images/ và assets/sounds/ để sử dụng.

Cần có:
  assets/images/dino.png, dino_duck.png, cactus.png, bird.png
  assets/sounds/jump.wav, gameover.wav, score.wav
"""
import os
import pygame


def get_assets_path():
    """Đường dẫn thư mục assets"""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def load_image(path, scale=None):
    """Tải ảnh, trả về Surface hoặc None nếu không có file"""
    full = os.path.join(get_assets_path(), "images", path)
    try:
        if os.path.exists(full):
            img = pygame.image.load(full).convert_alpha()
            if scale:
                img = pygame.transform.scale(img, scale)
            return img
    except pygame.error:
        pass
    return None


def _load_sound_file(path):
    """Tải âm thanh từ đường dẫn đầy đủ"""
    full = os.path.join(get_assets_path(), "sounds", path)
    try:
        if os.path.exists(full):
            return pygame.mixer.Sound(full)
    except pygame.error:
        pass
    return None


# Sprites (lazy load)
_sprites = {}


def get_sprite(name, scale=None):
    """Lấy sprite theo tên, cache kết quả"""
    key = (name, scale)
    if key not in _sprites:
        _sprites[key] = load_image(name + ".png", scale)
    return _sprites[key]


# Sounds (lazy load)
_sounds = {}
_mixer_initialized = False


def init_mixer():
    global _mixer_initialized
    if not _mixer_initialized:
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            _mixer_initialized = True
        except pygame.error:
            pass


def get_sound(name):
    """Lấy sound theo tên, cache kết quả"""
    if name not in _sounds:
        init_mixer()
        _sounds[name] = _load_sound_file(name + ".wav")
    return _sounds[name]


def play_sound(name):
    """Phát âm thanh nếu có file"""
    s = get_sound(name)
    if s:
        try:
            s.play()
        except pygame.error:
            pass


# Cloud positions (vẽ mây bằng pygame - không cần asset)
CLOUD_POSITIONS = [
    (150, 100), (400, 80), (700, 120), (950, 90), (200, 200), (600, 180),
]
