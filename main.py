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
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("DinoRacer Ultimate")

    # Xóa cache sprite để load lại với kích thước mới
    clear_sheet_cache()

    # 2. Vòng lặp chính của ứng dụng
    while True:
        # Tạo và chạy menu
        menu = Menu(screen)
        choice = menu.run()
        
        if choice == 'PVE(VS AI)':
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
            
        elif choice == 'Train AI':
            print("Bắt đầu training NEAT... (Nhấn Ctrl+C để dừng sớm)")
            winner = run_neat_training(generations=20)
            if winner:
                print("\nTraining xong! Chạy AI tốt nhất...")
                config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                    neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                    get_config_path())
                run_best_genome_display(winner, config)
        
        elif choice == 'Quit':
            # 3. Chỉ thoát Pygame khi người dùng chọn Quit từ Menu
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()