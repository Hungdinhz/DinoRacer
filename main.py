"""
DinoRacer - Game khủng long nhảy với AI NEAT
Chạy: python main.py [human|ai]
- human: Chế độ người chơi (Space=nhảy, Down=cúi)
- ai: Chế độ AI train NEAT
"""
import sys
import pygame
from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.game_manager import GameManager
from src.ai_handler import run_neat_training, run_best_genome_display, get_config_path
import neat


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("DinoRacer")

    mode = sys.argv[1] if len(sys.argv) > 1 else "human"

    if mode == "human":
        # Chế độ người chơi
        game = GameManager(screen)
        game.run_human_mode()

    elif mode == "ai":
        # Chế độ AI - train NEAT
        print("Bắt đầu training NEAT... (Nhấn Ctrl+C để dừng sớm)")
        winner = run_neat_training(generations=50)
        if winner:
            print("\nTraining xong! Chạy AI tốt nhất...")
            config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                                neat.DefaultSpeciesSet, neat.DefaultStagnation,
                                get_config_path())
            run_best_genome_display(winner, config)

    else:
        print("Cách dùng: python main.py [human|ai]")
        print("  human - Chơi thủ công (Space=nhảy, ↓=cúi)")
        print("  ai    - Train AI NEAT")


if __name__ == "__main__":
    main()
