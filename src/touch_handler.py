"""
Touch Controls Handler - Xử lý cảm ứng cho mobile/tablet
Hỗ trợ: tap to jump, swipe up to jump, swipe down to duck
"""
import pygame
from typing import Optional, Tuple, Callable, List, Dict
from dataclasses import dataclass, field
import time


@dataclass
class TouchEvent:
    """Sự kiện chạm"""
    touch_id: int
    position: Tuple[int, int]
    start_position: Tuple[int, int]
    event_type: str  # 'tap', 'swipe_up', 'swipe_down', 'hold', 'release'
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0


class TouchHandler:
    """
    Xử lý touch controls cho game.
    Hỗ trợ:
    - Tap: Nhảy
    - Swipe up: Nhảy
    - Swipe down: Cúi
    - Hold: Nhảy cao hơn (giữ tay)
    """

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height

        # Touch tracking
        self.active_touches: Dict[int, Tuple[int, int, float]] = {}
        self.last_tap_position: Optional[Tuple[int, int]] = None

        # Swipe detection
        self.swipe_threshold: int = 50  # pixels
        self.swipe_time_threshold: float = 0.5  # seconds
        self.tap_time_threshold: float = 0.2  # seconds

        # Jump/Duck zones (divide screen)
        self.jump_zone_height: int = screen_height // 2

        # Callbacks
        self.on_jump: Optional[Callable[[], None]] = None
        self.on_jump_release: Optional[Callable[[], None]] = None
        self.on_duck: Optional[Callable[[bool], None]] = None

        # Visual feedback
        self.show_touch_indicators: bool = True
        self.touch_points: List[Tuple[int, int, float, Tuple[int, int, int]]] = []

        # Enable touch
        self.enabled: bool = True

        # Debug
        self.debug_mode: bool = False

    def update_screen_size(self, width: int, height: int):
        """Cập nhật kích thước màn hình"""
        self.screen_width = width
        self.screen_height = height
        self.jump_zone_height = height // 2

    def handle_event(self, event: pygame.event.Event) -> Optional[TouchEvent]:
        """
        Xử lý pygame event và trả về TouchEvent nếu có action.
        """
        if not self.enabled:
            return None

        if event.type == pygame.FINGERDOWN:
            return self._handle_finger_down(event)
        elif event.type == pygame.FINGERUP:
            return self._handle_finger_up(event)
        elif event.type == pygame.FINGERMOTION:
            return self._handle_finger_motion(event)

        # Mouse events for testing on desktop
        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_mouse_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            return self._handle_mouse_up(event)

        return None

    def _handle_finger_down(self, event: pygame.event.Event) -> Optional[TouchEvent]:
        """Xử lý khi ngón tay chạm vào màn hình"""
        # Get touch position
        finger_x = event.x * self.screen_width
        finger_y = event.y * self.screen_height
        pos = (int(finger_x), int(finger_y))

        # Store touch
        self.active_touches[event.finger_id] = (pos[0], pos[1], time.time())

        # Add visual indicator
        if self.show_touch_indicators:
            self.touch_points.append((pos[0], pos[1], time.time(), (0, 255, 0)))

        # Determine action based on position
        touch_event = self._process_tap_or_swipe_start(event.finger_id, pos)
        return touch_event

    def _handle_finger_up(self, event: pygame.event.Event) -> Optional[TouchEvent]:
        """Xử lý khi ngón tay rời màn hình"""
        if event.finger_id not in self.active_touches:
            return None

        start_pos, start_time = self.active_touches[event.finger_id][:2]
        end_x = event.x * self.screen_width
        end_y = event.y * self.screen_height
        end_pos = (int(end_x), int(end_y))

        duration = time.time() - start_time

        # Process release
        touch_event = self._process_release(event.finger_id, start_pos, end_pos, duration)

        # Remove touch
        del self.active_touches[event.finger_id]

        # Add visual indicator
        if self.show_touch_indicators:
            self.touch_points.append((end_pos[0], end_pos[1], time.time(), (255, 0, 0)))

        return touch_event

    def _handle_finger_motion(self, event: pygame.event.Event) -> Optional[TouchEvent]:
        """Xử lý khi ngón tay di chuyển trên màn hình"""
        if event.finger_id not in self.active_touches:
            return None

        start_pos, start_time = self.active_touches[event.finger_id][:2]
        current_x = event.x * self.screen_width
        current_y = event.y * self.screen_height
        current_pos = (int(current_x), int(current_y))

        # Update position
        self.active_touches[event.finger_id] = (current_pos[0], current_pos[1], start_time)

        # Check for swipe
        dx = current_pos[0] - start_pos[0]
        dy = current_pos[1] - start_pos[1]

        if abs(dy) > self.swipe_threshold:
            if dy < 0:  # Swipe up
                touch_event = TouchEvent(
                    touch_id=event.finger_id,
                    position=current_pos,
                    start_position=start_pos,
                    event_type='swipe_up'
                )
                # Add visual
                if self.show_touch_indicators:
                    self.touch_points.append((current_pos[0], current_pos[1], time.time(), (0, 255, 255)))
                return touch_event
            else:  # Swipe down
                touch_event = TouchEvent(
                    touch_id=event.finger_id,
                    position=current_pos,
                    start_position=start_pos,
                    event_type='swipe_down'
                )
                # Add visual
                if self.show_touch_indicators:
                    self.touch_points.append((current_pos[0], current_pos[1], time.time(), (255, 255, 0)))
                return touch_event

        return None

    def _handle_mouse_down(self, event: pygame.event.Event) -> Optional[TouchEvent]:
        """Xử lý mouse click (desktop testing)"""
        pos = event.pos

        # Simulate touch
        self.active_touches[0] = (pos[0], pos[1], time.time())

        if self.show_touch_indicators:
            self.touch_points.append((pos[0], pos[1], time.time(), (0, 255, 0)))

        return self._process_tap_or_swipe_start(0, pos)

    def _handle_mouse_up(self, event: pygame.event.Event) -> Optional[TouchEvent]:
        """Xử lý mouse release (desktop testing)"""
        if 0 not in self.active_touches:
            return None

        start_pos, start_time = self.active_touches[0][:2]
        end_pos = event.pos
        duration = time.time() - start_time

        touch_event = self._process_release(0, start_pos, end_pos, duration)

        del self.active_touches[0]

        if self.show_touch_indicators:
            self.touch_points.append((end_pos[0], end_pos[1], time.time(), (255, 0, 0)))

        return touch_event

    def _process_tap_or_swipe_start(self, touch_id: int, pos: Tuple[int, int]) -> Optional[TouchEvent]:
        """Xử lý tap hoặc bắt đầu swipe"""
        # Upper half = jump zone
        if pos[1] < self.jump_zone_height:
            if self.on_jump:
                self.on_jump()

            return TouchEvent(
                touch_id=touch_id,
                position=pos,
                start_position=pos,
                event_type='tap'
            )
        else:
            # Lower half = duck zone
            if self.on_duck:
                self.on_duck(True)

            return TouchEvent(
                touch_id=touch_id,
                position=pos,
                start_position=pos,
                event_type='tap'
            )

    def _process_release(self, touch_id: int, start_pos: Tuple[int, int],
                        end_pos: Tuple[int, int], duration: float) -> Optional[TouchEvent]:
        """Xử lý khi thả ngón tay"""
        # Stop ducking
        if self.on_duck:
            self.on_duck(False)

        # Stop jump hold
        if self.on_jump_release:
            self.on_jump_release()

        # Check if it was a quick tap
        if duration < self.tap_time_threshold:
            return TouchEvent(
                touch_id=touch_id,
                position=end_pos,
                start_position=start_pos,
                event_type='release',
                duration=duration
            )

        return None

    def update(self):
        """Update visual indicators"""
        current_time = time.time()
        # Remove old touch points (older than 0.5 seconds)
        self.touch_points = [
            (x, y, t, color) for x, y, t, color in self.touch_points
            if current_time - t < 0.5
        ]

    def draw(self, screen: pygame.Surface):
        """Vẽ touch indicators"""
        if not self.show_touch_indicators:
            return

        current_time = time.time()
        for x, y, t, color in self.touch_points:
            # Fade out effect
            age = current_time - t
            alpha = max(0, int(255 * (1 - age / 0.5)))

            # Draw circle
            radius = 30
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius - 2)
            pygame.draw.circle(surf, (*color, alpha), (radius, radius), radius - 2, 2)
            screen.blit(surf, (x - radius, y - radius))

    def get_debug_info(self) -> str:
        """Lấy thông tin debug"""
        return (
            f"Touch Enabled: {self.enabled}\n"
            f"Active Touches: {len(self.active_touches)}\n"
            f"Jump Zone: 0-{self.jump_zone_height}\n"
            f"Duck Zone: {self.jump_zone_height}-{self.screen_height}"
        )


class TouchButton:
    """Nút bấm cảm ứng cho game"""

    def __init__(self, x: int, y: int, width: int, height: int,
                 text: str = "", color: Tuple[int, int, int] = (100, 100, 100),
                 hover_color: Tuple[int, int, int] = (150, 150, 150),
                 text_color: Tuple[int, int, int] = (255, 255, 255),
                 on_click: Optional[Callable[[], None]] = None,
                 icon: Optional[pygame.Surface] = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.on_click = on_click
        self.icon = icon

        # State
        self.is_pressed = False
        self.is_hovered = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Xử lý event, trả về True nếu nút được bấm"""
        if event.type == pygame.FINGERDOWN:
            pos = (int(event.x * pygame.display.get_surface().get_width()),
                   int(event.y * pygame.display.get_surface().get_height()))
            if self.rect.collidepoint(pos):
                self.is_pressed = True
                if self.on_click:
                    self.on_click()
                return True

        elif event.type == pygame.FINGERUP:
            if self.is_pressed:
                self.is_pressed = False
                return True

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.is_pressed = True
                if self.on_click:
                    self.on_click()
                return True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.is_pressed = False

        return False

    def update(self):
        """Update trạng thái"""
        if pygame.mouse.get_focused():
            self.is_hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        else:
            self.is_hovered = False

    def draw(self, screen: pygame.Surface, font: Optional[pygame.font.Font] = None):
        """Vẽ nút"""
        # Determine color
        color = self.hover_color if (self.is_hovered or self.is_pressed) else self.color

        # Draw button
        pygame.draw.rect(screen, color, self.rect, border_radius=10)

        # Draw border
        border_color = (255, 215, 0) if self.is_pressed else (200, 200, 200)
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=10)

        # Draw icon or text
        if self.icon:
            icon_rect = self.icon.get_rect(center=self.rect.center)
            screen.blit(self.icon, icon_rect)
        elif self.text and font:
            text_surf = font.render(self.text, True, self.text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
            screen.blit(text_surf, text_rect)


class TouchControlsOverlay:
    """Overlay hiển thị các nút touch trên màn hình"""

    def __init__(self, screen_width: int, screen_height: int):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.visible = True

        # Button size
        btn_size = 80

        # Create buttons
        self.jump_button = TouchButton(
            x=screen_width - btn_size - 20,
            y=screen_height // 2 - btn_size - 50,
            width=btn_size,
            height=btn_size,
            text="↑",
            on_click=None
        )

        self.duck_button = TouchButton(
            x=screen_width - btn_size - 20,
            y=screen_height // 2 + 50,
            width=btn_size,
            height=btn_size,
            text="↓",
            on_click=None
        )

    def set_callbacks(self, jump_callback: Callable[[], None],
                     duck_callback: Callable[[bool], None]):
        """Đặt callbacks cho các nút"""
        self.jump_button.on_click = jump_callback
        self.duck_button.on_click = lambda: duck_button_pressed(duck_button, duck_callback)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Xử lý event"""
        if not self.visible:
            return False

        self.jump_button.handle_event(event)
        self.duck_button.handle_event(event)
        return False

    def update(self):
        """Update trạng thái"""
        self.jump_button.update()
        self.duck_button.update()

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        """Vẽ overlay"""
        if not self.visible:
            return

        self.jump_button.draw(screen, font)
        self.duck_button.draw(screen, font)

    def toggle(self):
        """Toggle hiển thị"""
        self.visible = not self.visible


def duck_button_pressed(button, callback):
    """Helper để xử lý duck button"""
    callback(True)
    # Schedule release after a short delay
    import threading
    def release():
        import time
        time.sleep(0.1)
        callback(False)
    threading.Thread(target=release, daemon=True).start()
