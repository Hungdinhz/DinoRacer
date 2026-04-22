# DinoRacer Ultimate

Game khủng long nhảy (giống Chrome Dino) được nâng cấp với nhiều chế độ chơi, hỗ trợ chơi 2 người, tích hợp hệ thống vật phẩm (items) và trí tuệ nhân tạo (AI) sử dụng các thuật toán như NEAT và Supervised Learning.

---

## 🎮 Các chế độ chơi (Game Modes)

- **Classic**: Chơi đơn truyền thống.
- **Time Attack**: Đua với thời gian.
- **Endless**: Chế độ chơi vô tận.
- **PVE (VS AI)**: Thi đấu với các đối thủ AI (bao gồm NEAT AI, Supervised AI, và Hybrid AI).
- **PVP (VS PLAYER)**: Thi đấu 2 người chơi trên cùng một máy.

## 🤖 Tính năng AI

- **NEAT Training**: Huấn luyện AI qua giao diện trực quan hoặc chế độ chạy ngầm bằng thuật toán tiến hóa NEAT.
- **Supervised Training**: Huấn luyện AI bằng phương pháp học có giám sát dựa trên dữ liệu (records) thu thập được từ thao tác của người chơi.

---

## ⚙️ Cài đặt

Yêu cầu đã cài đặt Python 3. Sau đó, chạy lệnh sau để cài đặt các thư viện phụ thuộc:

```bash
pip install -r requirements.txt
```

---

## 🚀 Chạy game

Khởi chạy game để mở Menu chính và lựa chọn các chế độ chơi:

```bash
python main.py
```

### Bảng điều khiển cơ bản:
- **Người chơi 1 / Chơi đơn**:
  - `Space` hoặc `↑` : Nhảy
  - `↓` hoặc `S`     : Cúi (giữ phím)
  - `T`              : Chém kiếm (khi nhặt được vật phẩm kiếm)
  - `P`              : Tạm dừng (Pause)
  - `R`              : Chơi lại (Restart)
  - `ESC`            : Trở về màn hình chính hoặc Thoát
  - `F11`            : Bật/tắt chế độ toàn màn hình (Fullscreen)
- *(Trong chế độ PVP, người chơi 2 sẽ sử dụng các phím như W/S/Q/D hoặc theo cấu hình ingame).*

---

## 📂 Cấu trúc dự án

```
DinoRacer/
├── main.py                   # Điểm vào (khởi chạy trò chơi và menu chính)
├── server.py                 # Backend Server (Leaderboard, quản lý game sessions)
├── config/                   # Các file cấu hình cài đặt hệ thống và NEAT
├── src/                      # Source code chính (game logic, UI, AI, database,...)
├── assets/                   # Hình ảnh (sprites), âm thanh (sounds) và fonts chữ
├── database_schema.sql       # Script khởi tạo cấu trúc cơ sở dữ liệu
├── requirements.txt          # Danh sách các thư viện cần cài đặt
├── best_genome.pkl           # Mô hình AI của thuật toán NEAT tốt nhất
└── duck_model.pkl / jump_model.pkl # Mô hình AI sử dụng Supervised Learning
```

---

## 🛠️ Công nghệ sử dụng

- **Python 3**
- **Pygame**: Render đồ họa 2D và âm thanh
- **NEAT (neat-python)**: Thuật toán di truyền phát triển mạng Neural Network
- **Scikit-learn**: Thuật toán Machine Learning (Supervised Learning)
- **SQLite / PostgreSQL**: Hệ quản trị cơ sở dữ liệu lưu thông tin highscore và sessions
