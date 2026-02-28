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
from src.assets_loader import clear_sheet_cache

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

        if choice == 'Solo':
            # Chế độ chơi thường một mình - Sử dụng GameManager với human mode
            game = GameManager(screen, is_ai_mode=False)
            game.run_human_mode()

        elif choice == 'PVE(VS AI)':
            game = GameManager(screen)
            game.run_pve_mode()

        elif choice == 'PVP(VS PLAYER)':
            game = GameManager(screen)
            game.run_pvp_mode()

        elif choice == 'Time Attack':
            from src.time_attack import run_time_attack
            difficulty = settings.difficulty
            run_time_attack(screen, difficulty=difficulty)
            
        elif choice == 'Endless':
            from src.endless import run_endless
            run_endless(screen)
            
        elif choice == 'NEAT Training' or choice == 'Train AI':
            print("Bắt đầu NEAT Visual Training... (ESC để dừng, S để skip gen)")
            try:
                from src.neat_visual import run_neat_visual
                winner, config = run_neat_visual(screen, get_config_path(), generations=50)
                if winner:
                    from src.ai_handler import save_genome
                    save_genome(winner)
                    print("\nTraining xong! Chạy AI tốt nhất...")
                    run_best_genome_display(winner, config)
            except Exception as e:
                print(f"Lỗi Visual Training: {e}")
                # Fallback về silent training
                winner = run_neat_training(generations=20)
                if winner:
                    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                        neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                        get_config_path())
                    run_best_genome_display(winner, config)

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

        elif choice == 'Quit':
            # 3. Chỉ thoát Pygame khi người dùng chọn Quit từ Menu
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()