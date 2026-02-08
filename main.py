"""
DinoRacer - Game khủng long nhảy với AI NEAT
Chạy: python main.py [human|ai|ai-play]
- human:   Chế độ người chơi (Space=nhảy, Down=cúi)
- ai:      Train AI NEAT (lưu vào best_genome.pkl khi xong)
- ai-play: Chạy AI đã lưu (không cần train lại)
"""
import sys
import pygame
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.game_manager import GameManager
from src.ai_handler import (
    run_neat_training,
    run_best_genome_display,
    get_config_path,
    load_genome,
)
import neat


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("DinoRacer")

    mode = sys.argv[1] if len(sys.argv) > 1 else "human"

    if mode == "human":
        game = GameManager(screen)
        game.run_human_mode()

    elif mode == "ai":
        print("Bắt đầu training NEAT... (Nhấn Ctrl+C để dừng sớm)")
        winner = run_neat_training(generations=50)
        if winner:
            print("\nTraining xong! Chạy AI tốt nhất...")
            config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                get_config_path())
            run_best_genome_display(winner, config)

    elif mode == "ai-play":
        genome, config = load_genome()
        if genome and config:
            print("Đã tải AI đã lưu. Nhấn phím bất kỳ để bắt đầu...")
            run_best_genome_display(genome, config)
        else:
            print("Chưa có AI đã lưu! Chạy 'python main.py ai' để train trước.")

    else:
        print("Cách dùng: python main.py [human|ai|ai-play]")
        print("  human   - Chơi thủ công (Space=nhảy, ↓=cúi)")
        print("  ai      - Train AI NEAT (lưu vào best_genome.pkl)")
        print("  ai-play - Chạy AI đã lưu (không cần train lại)")


if __name__ == "__main__":
    main()
