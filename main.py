import sys
import pygame
import neat
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.game_manager import GameManager
from src.menu import Menu
from src.ai_handler import (
    run_neat_training,
    run_best_genome_display,
    get_config_path,
    load_genome,
)
from src.assets_loader import clear_sheet_cache

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
            
        elif choice == 'Train AI':
            print("Bắt đầu training NEAT... (Nhấn Ctrl+C để dừng sớm)")
            # Train AI không cần màn hình đồ họa nặng, nhưng vẫn cần pygame init
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