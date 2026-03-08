"""
User Interface - Giao diện User, Friends, Leaderboards
"""
import pygame
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass

from config.settings import SCREEN_WIDTH, SCREEN_HEIGHT
from src.utils import get_cached_font
from src.assets_loader import play_sound


# Màu sắc
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (180, 180, 180)
DARK_BG = (20, 20, 30)
PANEL_BG = (30, 30, 45)
GOLD = (255, 215, 0)
GREEN = (80, 200, 80)
RED = (255, 80, 80)
BLUE = (100, 150, 255)


@dataclass
class User:
    """Thông tin user"""
    id: int
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    is_online: bool = False
    total_games: int = 0
    total_wins: int = 0
    pve_best_score: int = 0
    pvp_best_score: int = 0


class InputField:
    """Input field cho username/password"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 placeholder: str = "", is_password: bool = False):
        self.rect = pygame.Rect(x, y, width, height)
        self.placeholder = placeholder
        self.text = ""
        self.is_password = is_password
        self.active = False
        self.font = get_cached_font('Arial', 24)
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            return True

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.active = False
            elif len(self.text) < 20:
                if event.unicode.isprintable():
                    self.text += event.unicode
            return True
        return False

    def draw(self, screen: pygame.Surface):
        # Background
        color = BLUE if self.active else GRAY
        pygame.draw.rect(screen, color, self.rect, 2, border_radius=8)

        # Text
        display_text = "*" * len(self.text) if self.is_password else self.text
        if not display_text:
            text_surf = self.font.render(self.placeholder, True, LIGHT_GRAY)
        else:
            text_surf = self.font.render(display_text, True, WHITE)
        screen.blit(text_surf, (self.rect.x + 10, self.rect.centery - text_surf.get_height() // 2))

        # Cursor
        if self.active:
            self.cursor_timer += 1
            if self.cursor_timer > 30:
                self.cursor_timer = 0
                self.cursor_visible = not self.cursor_visible

            if self.cursor_visible:
                cursor_x = self.rect.x + 10 + text_surf.get_width()
                pygame.draw.line(screen, WHITE, (cursor_x, self.rect.y + 5),
                               (cursor_x, self.rect.bottom - 5), 2)


class LoginScreen:
    """Màn hình đăng nhập/đăng ký"""

    def __init__(self, screen):
        self.screen = screen
        self.mode = "login"  # login | register
        self.error_message = ""

        self.font_title = get_cached_font('impact', 48)
        self.font_label = get_cached_font('Arial', 20)
        self.font_button = get_cached_font('Arial', 24, bold=True)
        self.font_error = get_cached_font('Arial', 18)

        # Input fields
        field_width, field_height = 300, 50
        field_x = SCREEN_WIDTH // 2 - field_width // 2

        self.username_field = InputField(
            field_x, 250, field_width, field_height, "Username"
        )
        self.password_field = InputField(
            field_x, 330, field_width, field_height, "Password", is_password=True
        )
        self.email_field = InputField(
            field_x, 410, field_width, field_height, "Email (optional)"
        )

        # Buttons
        btn_width, btn_height = 200, 50
        self.login_btn = pygame.Rect(
            SCREEN_WIDTH // 2 - btn_width // 2, 480, btn_width, btn_height
        )
        self.toggle_btn = pygame.Rect(
            SCREEN_WIDTH // 2 - btn_width // 2, 550, btn_width, btn_height
        )

        # Logged in user
        self.current_user: Optional[User] = None

    def handle_event(self, event: pygame.event.Event) -> Optional[User]:
        """Xử lý event, trả về user nếu đăng nhập thành công"""
        self.username_field.handle_event(event)
        self.password_field.handle_event(event)
        self.email_field.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.login_btn.collidepoint(event.pos):
                return self._try_login()
            elif self.toggle_btn.collidepoint(event.pos):
                self.mode = "register" if self.mode == "login" else "login"
                self.error_message = ""
                play_sound("menu_click")

        return None

    def _try_login(self) -> Optional[User]:
        """Thử đăng nhập"""
        username = self.username_field.text.strip()
        password = self.password_field.text.strip()

        if not username or not password:
            self.error_message = "Vui lòng nhập đầy đủ thông tin"
            return None

        try:
            from src.database_handler import get_user_by_username
            user = get_user_by_username(username)
            if user:
                # Login successful (simplified - no password check)
                self.current_user = User(
                    id=user[0],
                    username=user[1],
                    display_name=user[4] or user[1],
                    is_online=True
                )
                play_sound("menu_click")
                return self.current_user
            elif self.mode == "register":
                # Create new user (simplified)
                self.error_message = "Tính năng đăng ký đang được phát triển"
                return None
            else:
                self.error_message = "Tên đăng nhập không tồn tại"
                return None
        except Exception as e:
            self.error_message = f"Lỗi: {str(e)[:30]}"
            return None

    def draw(self):
        """Vẽ màn hình đăng nhập"""
        # Background
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # Title
        title = "ĐĂNG NHẬP" if self.mode == "login" else "ĐĂNG KÝ"
        title_surf = self.font_title.render(title, True, GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(
            center=(SCREEN_WIDTH // 2, 150)
        ))

        # Username
        label = self.font_label.render("Tên đăng nhập:", True, WHITE)
        self.screen.blit(label, (self.username_field.rect.x, self.username_field.rect.y - 25))
        self.username_field.draw(self.screen)

        # Password
        label = self.font_label.render("Mật khẩu:", True, WHITE)
        self.screen.blit(label, (self.password_field.rect.x, self.password_field.rect.y - 25))
        self.password_field.draw(self.screen)

        # Email (register only)
        if self.mode == "register":
            label = self.font_label.render("Email:", True, WHITE)
            self.screen.blit(label, (self.email_field.rect.x, self.email_field.rect.y - 25))
            self.email_field.draw(self.screen)

        # Error message
        if self.error_message:
            error_surf = self.font_error.render(self.error_message, True, RED)
            self.screen.blit(error_surf, error_surf.get_rect(
                center=(SCREEN_WIDTH // 2, 240)
            ))

        # Login button
        btn_text = "ĐĂNG NHẬP" if self.mode == "login" else "ĐĂNG KÝ"
        pygame.draw.rect(self.screen, GREEN, self.login_btn, border_radius=8)
        btn_surf = self.font_button.render(btn_text, True, WHITE)
        self.screen.blit(btn_surf, btn_surf.get_rect(center=self.login_btn.center))

        # Toggle button
        toggle_text = "Chưa có tài khoản? Đăng ký" if self.mode == "login" else "Đã có tài khoản? Đăng nhập"
        pygame.draw.rect(self.screen, GRAY, self.toggle_btn, 1, border_radius=8)
        toggle_surf = self.font_label.render(toggle_text, True, LIGHT_GRAY)
        self.screen.blit(toggle_surf, toggle_surf.get_rect(center=self.toggle_btn.center))


class LeaderboardPanel:
    """Panel hiển thị leaderboard"""

    def __init__(self, screen, x: int, y: int, width: int, height: int,
                 title: str = "Leaderboard"):
        self.screen = screen
        self.rect = pygame.Rect(x, y, width, height)
        self.title = title

        self.font_title = get_cached_font('impact', 28)
        self.font_item = get_cached_font('Arial', 18)
        self.font_rank = get_cached_font('Arial', 20, bold=True)

        self.entries: List[Tuple[int, str, str, int]] = []  # rank, username, display_name, score
        self.loading = False

    def load_global(self, game_mode: str = "pve", limit: int = 10):
        """Load global leaderboard"""
        self.loading = True
        try:
            from src.database_handler import get_global_leaderboard
            results = get_global_leaderboard(game_mode, limit)
            self.entries = [
                (i + 1, r[1], r[2] or r[1], r[4])
                for i, r in enumerate(results)
            ]
        except Exception as e:
            print(f"Error loading leaderboard: {e}")
            self.entries = []
        self.loading = False

    def load_friends(self, user_id: int, game_mode: str = "pve", limit: int = 10):
        """Load friends leaderboard"""
        self.loading = True
        try:
            from src.database_handler import get_friends_leaderboard
            results = get_friends_leaderboard(user_id, game_mode, limit)
            self.entries = [
                (i + 1, r[1], r[2] or r[1], r[4])
                for i, r in enumerate(results)
            ]
        except Exception as e:
            print(f"Error loading friends leaderboard: {e}")
            self.entries = []
        self.loading = False

    def draw(self):
        """Vẽ leaderboard"""
        # Background
        pygame.draw.rect(self.screen, PANEL_BG, self.rect, border_radius=12)

        # Title
        title_surf = self.font_title.render(self.title, True, GOLD)
        self.screen.blit(title_surf, (self.rect.x + 15, self.rect.y + 10))

        # Entries
        y = self.rect.y + 50
        for rank, username, display_name, score in self.entries:
            # Rank
            rank_color = GOLD if rank == 1 else (WHITE if rank <= 3 else GRAY)
            rank_surf = self.font_rank.render(f"#{rank}", True, rank_color)
            self.screen.blit(rank_surf, (self.rect.x + 15, y))

            # Name
            name_surf = self.font_item.render(display_name, True, WHITE)
            self.screen.blit(name_surf, (self.rect.x + 60, y))

            # Score
            score_surf = self.font_item.render(f"{score}", True, GREEN)
            score_rect = score_surf.get_rect(right=self.rect.right - 15)
            self.screen.blit(score_surf, score_rect)

            y += 30

        # Empty state
        if not self.entries and not self.loading:
            empty_surf = self.font_item.render("No data yet", True, GRAY)
            self.screen.blit(empty_surf, empty_surf.get_rect(
                center=(self.rect.centerx, self.rect.centery)
            ))


class FriendsPanel:
    """Panel hiển thị bạn bè"""

    def __init__(self, screen, x: int, y: int, width: int, height: int):
        self.screen = screen
        self.rect = pygame.Rect(x, y, width, height)

        self.font_title = get_cached_font('impact', 28)
        self.font_item = get_cached_font('Arial', 18)

        self.friends: List[User] = []
        self.requests: List[Tuple[int, str, str]] = []  # id, username, display_name
        self.loading = False

    def load_friends(self, user_id: int):
        """Load friends list"""
        self.loading = True
        try:
            from src.database_handler import get_friends, get_friend_requests
            friends_data = get_friends(user_id)
            self.friends = [
                User(id=f[0], username=f[1], display_name=f[2] or f[1],
                     avatar_url=f[3], is_online=f[4])
                for f in friends_data
            ]

            requests_data = get_friend_requests(user_id)
            self.requests = [(r[0], r[3], r[4]) for r in requests_data]
        except Exception as e:
            print(f"Error loading friends: {e}")
            self.friends = []
            self.requests = []
        self.loading = False

    def draw(self):
        """Vẽ friends panel"""
        # Background
        pygame.draw.rect(self.screen, PANEL_BG, self.rect, border_radius=12)

        # Title
        title_surf = self.font_title.render("Bạn bè", True, GOLD)
        self.screen.blit(title_surf, (self.rect.x + 15, self.rect.y + 10))

        # Friend requests
        if self.requests:
            req_label = self.font_item.render(f"Lời mời kết bạn ({len(self.requests)})", True, BLUE)
            self.screen.blit(req_label, (self.rect.x + 15, self.rect.y + 50))
            y = self.rect.y + 75
            for req_id, username, display_name in self.requests[:3]:
                req_surf = self.font_item.render(f"  {display_name}", True, WHITE)
                self.screen.blit(req_surf, (self.rect.x + 15, y))
                y += 25
            y += 10

        # Friends list
        y = self.rect.y + 50 + (40 if self.requests else 0)
        for friend in self.friends[:5]:
            # Online status
            status_color = GREEN if friend.is_online else GRAY
            pygame.draw.circle(self.screen, status_color,
                            (self.rect.x + 15, y + 8), 5)

            name_surf = self.font_item.render(friend.display_name, True, WHITE)
            self.screen.blit(name_surf, (self.rect.x + 30, y))

            y += 28

        # Empty state
        if not self.friends and not self.requests:
            empty_surf = self.font_item.render("Chưa có bạn bè", True, GRAY)
            self.screen.blit(empty_surf, empty_surf.get_rect(
                center=(self.rect.centerx, self.rect.centery)
            ))


class ProfilePanel:
    """Panel hiển thị profile người dùng"""

    def __init__(self, screen, x: int, y: int, width: int, height: int):
        self.screen = screen
        self.rect = pygame.Rect(x, y, width, height)

        self.font_title = get_cached_font('impact', 28)
        self.font_label = get_cached_font('Arial', 16)
        self.font_value = get_cached_font('Arial', 20, bold=True)

        self.user: Optional[User] = None

    def load_profile(self, user_id: int):
        """Load user profile"""
        try:
            from src.database_handler import get_user_profile
            profile = get_user_profile(user_id)
            if profile:
                self.user = User(
                    id=profile[0],
                    username=profile[1],
                    display_name=profile[4] or profile[1],
                    avatar_url=profile[5],
                    total_games=profile[9] or 0,
                    total_wins=profile[10] or 0,
                    pve_best_score=profile[14] or 0,
                    pvp_best_score=profile[18] or 0
                )
        except Exception as e:
            print(f"Error loading profile: {e}")

    def draw(self):
        """Vẽ profile"""
        if not self.user:
            return

        # Background
        pygame.draw.rect(self.screen, PANEL_BG, self.rect, border_radius=12)

        # Name
        name_surf = self.font_title.render(self.user.display_name, True, GOLD)
        self.screen.blit(name_surf, (self.rect.x + 15, self.rect.y + 15))

        # Username
        username_surf = self.font_label.render(f"@{self.user.username}", True, GRAY)
        self.screen.blit(username_surf, (self.rect.x + 15, self.rect.y + 50))

        # Stats
        y = self.rect.y + 80

        # Games
        games_label = self.font_label.render("Tổng trận:", True, LIGHT_GRAY)
        games_value = self.font_value.render(f"{self.user.total_games}", True, WHITE)
        self.screen.blit(games_label, (self.rect.x + 15, y))
        self.screen.blit(games_value, (self.rect.x + 120, y - 2))

        y += 30

        # Wins
        wins_label = self.font_label.render("Thắng:", True, LIGHT_GRAY)
        wins_value = self.font_value.render(f"{self.user.total_wins}", True, GREEN)
        self.screen.blit(wins_label, (self.rect.x + 15, y))
        self.screen.blit(wins_value, (self.rect.x + 120, y - 2))

        y += 30

        # Best PVE
        pve_label = self.font_label.render("Best PVE:", True, LIGHT_GRAY)
        pve_value = self.font_value.render(f"{self.user.pve_best_score}", True, GOLD)
        self.screen.blit(pve_label, (self.rect.x + 15, y))
        self.screen.blit(pve_value, (self.rect.x + 120, y - 2))

        y += 30

        # Best PVP
        pvp_label = self.font_label.render("Best PVP:", True, LIGHT_GRAY)
        pvp_value = self.font_value.render(f"{self.user.pvp_best_score}", True, BLUE)
        self.screen.blit(pvp_label, (self.rect.x + 15, y))
        self.screen.blit(pvp_value, (self.rect.x + 120, y - 2))
