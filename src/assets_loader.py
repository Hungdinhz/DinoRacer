"""
Assets Loader - Tải sprites, sprite sheets và âm thanh
"""
import os
import pygame

# Đường dẫn thư mục assets/images (dùng cho load_sprite_sheet)
current_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "images")


def get_assets_path():
    """Đường dẫn thư mục assets"""
    return os.path.dirname(current_path)


# --- HÀM TẢI VÀ CẮT SPRITE SHEET ---
def load_sprite_sheet(filename, num_frames, scale=4):
    """
    Tải sprite sheet và cắt thành danh sách frames.
    filename  : đường dẫn tương đối từ assets/images/ (vd: 'dino/move.png')
    num_frames: số frame trong sheet
    scale     : hệ số phóng to (mặc định 4x)
    Trả về list[Surface] hoặc [] nếu không tìm thấy file.
    """
    image_path = os.path.join(current_path, filename)
    try:
        sheet = pygame.image.load(image_path).convert_alpha()
    except (FileNotFoundError, pygame.error):
        print(f"[assets_loader] Không tìm thấy sprite sheet: '{filename}'")
        return []

    sheet_w = sheet.get_width()
    sheet_h = sheet.get_height()
    frame_w = sheet_w // num_frames
    frame_h = sheet_h

    frames = []
    for i in range(num_frames):
        frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), (i * frame_w, 0, frame_w, frame_h))
        frame = pygame.transform.scale(frame, (frame_w * scale, frame_h * scale))
        frames.append(frame)
    return frames


def load_sprite_sheet_sized(filename, num_frames, target_w, target_h):
    """
    Tải sprite sheet và scale mỗi frame về kích thước cố định (target_w x target_h).
    Dùng khi cần fit vào hitbox cụ thể thay vì dùng scale factor.
    """
    image_path = os.path.join(current_path, filename)
    try:
        sheet = pygame.image.load(image_path).convert_alpha()
    except (FileNotFoundError, pygame.error):
        print(f"[assets_loader] Không tìm thấy sprite sheet: '{filename}'")
        return []

    sheet_w = sheet.get_width()
    sheet_h = sheet.get_height()
    frame_w = sheet_w // num_frames
    frame_h = sheet_h

    frames = []
    for i in range(num_frames):
        frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
        frame.blit(sheet, (0, 0), (i * frame_w, 0, frame_w, frame_h))
        frame = pygame.transform.scale(frame, (target_w, target_h))
        frames.append(frame)
    return frames


# Cache sprite sheets
_sheet_cache = {}


def clear_sheet_cache():
    """Xóa cache sprite sheets - dùng khi thay đổi kích thước."""
    global _sheet_cache, _img_cache, _item_sprites, _sprites, _font_cache
    _sheet_cache = {}
    _img_cache = {}
    _item_sprites = {}
    _sprites = {}
    _font_cache = {}
    preload_item_sprites()


def get_sheet(filename, num_frames, target_w, target_h):
    """Lấy frames từ sprite sheet, cache kết quả."""
    key = (filename, num_frames, target_w, target_h)
    if key not in _sheet_cache:
        _sheet_cache[key] = load_sprite_sheet_sized(filename, num_frames, target_w, target_h)
    return _sheet_cache[key]


# --- Load ảnh đơn ---
_img_cache = {}

# --- Font cache ---
_font_cache = {}

# --- Item sprite cache ---
_item_sprites = {}


def load_image(path, scale=None):
    """Tải ảnh đơn (cached), trả về Surface hoặc None nếu không có file."""
    key = (path, scale)
    if key in _img_cache:
        return _img_cache[key]
    full = os.path.join(current_path, path)
    img = None
    try:
        if os.path.exists(full):
            img = pygame.image.load(full).convert_alpha()
            if scale:
                img = pygame.transform.scale(img, scale)
    except pygame.error:
        pass
    _img_cache[key] = img
    return img


def get_cached_font_item(name, size, bold=False):
    """Font cache cho item (tránh tạo mới mỗi frame)."""
    key = (name, size, bold)
    if key not in _font_cache:
        _font_cache[key] = pygame.font.SysFont(name, size, bold=bold)
    return _font_cache[key]


def preload_item_sprites():
    """Load tất cả sprite item một lần khi game khởi động."""
    from config.settings import ITEM_WIDTH, ITEM_HEIGHT, ITSPEED_WIDTH, ITSPEED_HEIGHT, X2COIN_WIDTH, X2COIN_HEIGHT
    paths_sizes = [
        ('shield', 'items/Shield.png',  (ITEM_WIDTH,  ITEM_HEIGHT)),
        ('speed',  'items/Speed.png',   (ITSPEED_WIDTH, ITSPEED_HEIGHT)),
        ('x2',     'items/x2coin.png',   (X2COIN_WIDTH, X2COIN_HEIGHT)),
        ('sword',  'items/Sword.png',    (X2COIN_WIDTH, X2COIN_HEIGHT)),
    ]
    for key, path, size in paths_sizes:
        _item_sprites[key] = load_image(path, size)


def get_item_sprite(item_type):
    """Lấy sprite đã cache sẵn cho item type."""
    return _item_sprites.get(item_type)


_sprites = {}


def get_sprite(name, scale=None):
    key = (name, scale)
    if key not in _sprites:
        _sprites[key] = load_image(name + ".png", scale)
    return _sprites[key]


def get_sprite_from_folder(folder, filename, scale=None):
    key = (folder, filename, scale)
    if key not in _sprites:
        _sprites[key] = load_image(os.path.join(folder, filename), scale)
    return _sprites[key]


# --- Âm thanh ---
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
    if name not in _sounds:
        init_mixer()
        base_path = os.path.join(get_assets_path(), "sounds", name)
        sound_loaded = None
        
        # Danh sách các đuôi file âm thanh muốn hỗ trợ
        for ext in [".wav", ".mp3", ".ogg"]:
            full = base_path + ext
            if os.path.exists(full):
                try:
                    sound_loaded = pygame.mixer.Sound(full)
                    break  # Nếu tìm thấy và load thành công thì thoát vòng lặp luôn
                except pygame.error:
                    pass   # Nếu file lỗi thì bỏ qua, thử đuôi tiếp theo
                    
        _sounds[name] = sound_loaded
        
    return _sounds[name]


def play_sound(name, volume=1.0):
    """
    Phát âm thanh với mức âm lượng tùy chỉnh.
    volume: từ 0.0 (im lặng) đến 1.0 (to nhất mặc định)
    """
    s = get_sound(name)
    if s:
        try:
            # Cài đặt âm lượng trước khi phát
            s.set_volume(volume) 
            s.play()
        except pygame.error:
            pass


CLOUD_POSITIONS = [
    (150, 60), (400, 40), (700, 80), (950, 50), (200, 150), (600, 130),
]
