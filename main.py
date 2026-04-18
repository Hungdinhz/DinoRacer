import sys
import os
import pygame
import neat
from dotenv import load_dotenv
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.game_manager import GameManager
from src.menu import Menu, settings
from src.ai_handler import (
    run_neat_training,
    run_best_genome_display,
    get_config_path,
    load_genome,
)
from src.assets_loader import clear_sheet_cache, preload_item_sprites
from src.utils import get_cached_font
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT

# Load environment variables from .env file
load_dotenv()

# Initialize database on startup
try:
    from src.database_handler import init_database, test_connection
    success, result = test_connection()
    if success:
        print(f"Database connected: {result}")
        init_database()
    else:
        print(f"Database connection failed: {result}")
except Exception as e:
    print(f"Database initialization skipped: {e}")

def main():
    # 1. Khởi tạo Pygame MỘT LẦN DUY NHẤT ở đầu chương trình
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("DinoRacer Ultimate")

    # Biến theo dõi kích thước màn hình hiện tại
    current_width = SCREEN_WIDTH
    current_height = SCREEN_HEIGHT

    # Xóa cache sprite để load lại với kích thước mới
    clear_sheet_cache()
    # Pre-load tất cả item sprite một lần tránh lag khi spawn
    preload_item_sprites()

    # Biến theo dõi fullscreen
    is_fullscreen = [False]

    # Hàm toggle fullscreen
    def toggle_fullscreen():
        nonlocal current_width, current_height
        if is_fullscreen[0]:
            screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
            current_width = SCREEN_WIDTH
            current_height = SCREEN_HEIGHT
            is_fullscreen[0] = False
        else:
            screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            current_width = screen.get_width()
            current_height = screen.get_height()
            is_fullscreen[0] = True
        # Xóa cache background để tạo lại với kích thước mới
        from src.menu import _clear_background_cache
        _clear_background_cache()
        return screen

    # 2. Vòng lặp chính của ứng dụng
    while True:
        # Xử lý sự kiện resize và fullscreen
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                current_width = event.w
                current_height = event.h
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                # Xóa cache background để tạo lại với kích thước mới
                from src.menu import _clear_background_cache
                _clear_background_cache()
                # Cập nhật SCREEN_WIDTH, SCREEN_HEIGHT trong tất cả các module
                import config.settings as game_settings
                game_settings.SCREEN_WIDTH = current_width
                game_settings.SCREEN_HEIGHT = current_height
                # Cập nhật lại trong menu module
                import src.menu as menu_module
                menu_module.SCREEN_WIDTH = current_width
                menu_module.SCREEN_HEIGHT = current_height
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    screen = toggle_fullscreen()
                    # Cập nhật sau khi toggle fullscreen
                    import config.settings as game_settings
                    game_settings.SCREEN_WIDTH = current_width
                    game_settings.SCREEN_HEIGHT = current_height
                    import src.menu as menu_module
                    menu_module.SCREEN_WIDTH = current_width
                    menu_module.SCREEN_HEIGHT = current_height
        
        # Cập nhật settings với kích thước màn hình hiện tại
        import config.settings as game_settings
        game_settings.SCREEN_WIDTH = current_width
        game_settings.SCREEN_HEIGHT = current_height
        
        # Tạo và chạy menu
        menu = Menu(screen)
        choice = menu.run()

        if choice == 'Classic':
            # Chế độ chơi thường một mình - Sử dụng GameManager với human mode
            game = GameManager(screen, is_ai_mode=False)
            game.run_human_mode()

        elif choice == 'Time Attack':
            from src.time_attack import run_time_attack
            difficulty = settings.difficulty
            run_time_attack(screen, difficulty=difficulty)

        elif choice == 'Endless':
            from src.endless import run_endless
            run_endless(screen)

        elif choice == 'PVE(VS AI)':
            # Hien thi menu chon loai AI trong game
            ai_type = select_ai_type(screen)
            if ai_type:
                print(f"Dang khoi tao AI: {ai_type}")
                game = GameManager(screen)
                game.run_pve_mode(ai_type=ai_type)

        elif choice == 'PVP(VS PLAYER)':
            game = GameManager(screen)
            game.run_pvp_mode()
            
        elif choice == 'NEAT Training' or choice == 'Train AI':
            print("Bat dau NEAT Visual Training... (ESC de dung, S de skip gen, R de reset)")
            try:
                from src.neat_visual import run_neat_visual, load_best_model
                from src.ai_handler import get_config_path as ai_config_path

                winner, config = run_neat_visual(screen, ai_config_path(), generations=50)
                if winner:
                    print("\nTraining xong! Chay AI tot nhat...")
                    genome, cfg = load_best_model()
                    if genome and cfg:
                        run_best_genome_display(genome, cfg)
                    else:
                        print("Khong load duoc model - thu lai training!")
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"Loi Visual Training: {e}")
                # Fallback ve silent training
                winner = run_neat_training(generations=20)
                if winner:
                    genome, config = load_genome()
                    if genome and config:
                        run_best_genome_display(genome, config)

        elif choice == 'Supervised Training':
            print("Bắt đầu Supervised Learning training...")
            try:
                from src.supervised_trainer import train_supervised, get_data_stats
                stats = get_data_stats()
                print(f"Dữ liệu hiện có: {stats['total']} mẫu (Human: {stats['human']}, AI: {stats['ai']})")
                if stats['total'] < 10:
                    print("Chưa đủ dữ liệu! Hãy chơi PVP mode để thu thập dữ liệu trước.")
                else:
                    success = train_supervised()
                    if success:
                        print("Training Supervised hoàn tất! Models đã lưu.")
            except Exception as e:
                print(f"Lỗi Supervised Training: {e}")

    pygame.quit()
    sys.exit()

def select_ai_type(screen):
    """Hiển thị menu chọn loại AI trong game"""
    ai_options = ["NEAT AI", "Supervised AI", "Hybrid AI"]
    selected = 0
    btn_width, btn_height = 300, 60
    gap = 15

    font_title = get_cached_font('impact', 50)
    font_item = get_cached_font('Arial', 28, bold=True)

    clock = pygame.time.Clock()

    while True:
        screen.fill((20, 20, 30))

        # Title
        title = font_title.render("Select AI Opponent", True, (255, 215, 0))
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 80))

        # Calculate positions
        total_h = len(ai_options) * btn_height + (len(ai_options) - 1) * gap
        start_y = SCREEN_HEIGHT//2 - total_h//2

        for i, option in enumerate(ai_options):
            cx = SCREEN_WIDTH // 2
            y = start_y + i * (btn_height + gap)
            rect = pygame.Rect(cx - btn_width//2, y, btn_width, btn_height)

            color = (255, 215, 0) if i == selected else (100, 100, 100)
            pygame.draw.rect(screen, color, rect, 3, border_radius=10)

            if i == selected:
                pygame.draw.rect(screen, (255, 215, 0), rect, 3, border_radius=10)

            text = font_item.render(option, True, color)
            screen.blit(text, (cx - text.get_width()//2, y + btn_height//2 - text.get_height()//2))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(ai_options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(ai_options)
                elif event.key == pygame.K_RETURN:
                    ai_types = ['neat', 'supervised', 'hybrid']
                    return ai_types[selected]
                elif event.key == pygame.K_ESCAPE:
                    return None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_pos = pygame.mouse.get_pos()
                    for i in range(len(ai_options)):
                        y = start_y + i * (btn_height + gap)
                        rect = pygame.Rect(SCREEN_WIDTH//2 - btn_width//2, y, btn_width, btn_height)
                        if rect.collidepoint(mouse_pos):
                            ai_types = ['neat', 'supervised', 'hybrid']
                            return ai_types[i]

        clock.tick(60)


if __name__ == "__main__":
    main()