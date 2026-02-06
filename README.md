```
DinoRacer/
├── assets/                 # Chứa toàn bộ tài nguyên game (KHÔNG chứa code)
│   ├── images/             # Ảnh: khủng long, xương rồng, chim, đất...
│   ├── sounds/             # Âm thanh: tiếng nhảy, game over...
│   └── fonts/              # Font chữ hiển thị điểm số
│
├── config/                 # Chứa các file cấu hình
│   ├── neat-config.txt     # File cấu hình quan trọng cho AI (NEAT)
│   └── settings.py         # Các hằng số: kích thước màn hình, FPS, màu sắc...
│
├── src/                    # Source code chính (Logic game)
│   ├── __init__.py
│   ├── dino.py             # Class Dino (xử lý nhảy, cúi, vẽ hình)
│   ├── obstacle.py         # Class Chướng ngại vật (Cactus, Bird...)
│   ├── game_manager.py     # Quản lý vòng lặp game, tính điểm, va chạm
│   └── ai_handler.py       # Xử lý thuật toán NEAT (AI)
│
├── main.py                 # File chạy chính của chương trình
├── requirements.txt        # Danh sách thư viện cần cài
└── README.md               # File hướng dẫn
```

1. assets/ (Tài nguyên):

Lợi ích: Khi bạn muốn đổi giao diện (ví dụ: từ khủng long đen trắng sang khủng long có màu), bạn chỉ cần thay ảnh trong này mà không cần sửa code.

2. config/ (Cấu hình):

settings.py: Lưu các biến toàn cục như SCREEN_WIDTH = 1100, BG_COLOR = (255, 255, 255). Sau này muốn đổi kích thước game, bạn chỉ sửa 1 dòng ở đây thay vì tìm trong cả nghìn dòng code.

neat-config.txt: Thư viện NEAT bắt buộc cần file này để chỉnh các thông số như "population size" (số lượng cá thể), "mutation rate" (tỷ lệ đột biến). Để riêng giúp bạn tinh chỉnh trí tuệ nhân tạo dễ dàng hơn.

3. src/ (Source Code - Trái tim của game):

dino.py & obstacle.py: Tách riêng từng đối tượng. Nếu con khủng long bị lỗi, bạn biết ngay là vào file dino.py để sửa.

ai_handler.py: Đây là điểm mấu chốt để "dễ nâng cấp". Bạn tách biệt logic AI ra khỏi logic game. Nếu sau này bạn muốn tắt AI để người tự chơi, hoặc đổi thuật toán khác, bạn chỉ cần sửa file này mà không ảnh hưởng đến phần hiển thị game.

4. main.py:

File này chỉ nên làm nhiệm vụ khởi tạo và gọi các module khác chạy. Code trong này càng ngắn càng tốt.


