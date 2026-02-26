# DinoRacer

Game khủng long nhảy (giống Chrome Dino) với AI học bằng thuật toán NEAT.

---

## Mô tả

- **Chế độ Human**: Chơi thủ công (Space nhảy, ↓ cúi)
- **Chế độ AI**: Huấn luyện neural network bằng NEAT
- **Chế độ AI-play**: Chạy AI đã lưu, không cần train lại

---

## Cài đặt

```bash
pip install -r requirements.txt
```

---

## Chạy game

```bash
python main.py human    # Chơi thủ công
python main.py ai       # Train AI (lưu vào best_genome.pkl)
python main.py ai-play  # Chạy AI đã lưu
```

**Điều khiển:** Space = nhảy, ↓ = cúi, R = Restart (khi game over)

---

## Cấu trúc dự án

```
DinoRacer/
├── main.py           # Điểm vào
├── config/           # Cấu hình (settings, NEAT)
├── src/              # Code game
├── assets/           # Ảnh, âm thanh
└── docs/             # Tài liệu
    ├── TEAM_REVIEW.md   # Review cho team
    └── ASSETS.md       # Hướng dẫn sprites & âm thanh
```

---

## Tài liệu

| File | Nội dung |
|------|----------|
| [docs/HUONG_DAN_CONG_VIEC.md](docs/HUONG_DAN_CONG_VIEC.md) | **Hướng dẫn chi tiết** cho từng thành viên team |
| [docs/TEAM_REVIEW.md](docs/TEAM_REVIEW.md) | Cấu trúc code, chi tiết module, trạng thái dự án |
| [docs/ASSETS.md](docs/ASSETS.md) | Hướng dẫn thêm sprites và âm thanh |

---

## Công nghệ

- Python 3
- Pygame
- NEAT (neat-python)
