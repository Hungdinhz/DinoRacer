"""
Multiplayer Client - Kết nối đến WebSocket server cho multiplayer
"""
import asyncio
import json
import threading
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field


class MultiplayerClient:
    """
    Client để kết nối đến multiplayer server.
    Sử dụng trong game để chơi online với người khác.
    """

    def __init__(self):
        self.websocket = None
        self.connected = False
        self.player_id: Optional[str] = None
        self.username: Optional[str] = None

        # Match state
        self.in_match = False
        self.match_id: Optional[str] = None
        self.opponent_name: Optional[str] = None
        self.opponent_score = 0
        self.my_score = 0

        # Callbacks
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.on_match_found: Optional[Callable[[str, str, str], None]] = None  # match_id, opponent, you_are
        self.on_opponent_state: Optional[Callable[[Dict], None]] = None
        self.on_opponent_action: Optional[Callable[[Dict], None]] = None
        self.on_score_update: Optional[Callable[[int, int], None]] = None  # my_score, opponent_score
        self.on_match_ended: Optional[Callable[[Optional[str], Dict], None]] = None  # winner_id, scores
        self.on_chat_message: Optional[Callable[[str, str], None]] = None  # username, message
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_searching: Optional[Callable[[], None]] = None

        # Thread for async handling
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None

    def connect(self, host: str = "localhost", port: int = 8765,
                username: str = "Player") -> bool:
        """
        Kết nối đến server.
        Returns True nếu kết nối thành công.
        """
        self.username = username

        def run_async():
            import websockets
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def connect_async():
                try:
                    uri = f"ws://{host}:{port}"
                    async with websockets.connect(uri) as websocket:
                        self.websocket = websocket
                        self.connected = True

                        # Authenticate
                        await websocket.send(json.dumps({
                            "type": "auth",
                            "username": username
                        }))

                        # Listen for messages
                        async for message in websocket:
                            self._handle_message(json.loads(message))

                except Exception as e:
                    print(f"Connection error: {e}")
                    self.connected = False
                    if self.on_error:
                        self.on_error(str(e))

            try:
                self._loop.run_until_complete(connect_async())
            except Exception as e:
                print(f"Error: {e}")
                self.connected = False

        self._thread = threading.Thread(target=run_async, daemon=True)
        self._thread.start()

        # Wait for connection
        import time
        for _ in range(50):  # 5 seconds timeout
            time.sleep(0.1)
            if self.connected:
                return True

        return False

    def disconnect(self):
        """Ngắt kết nối"""
        if self.websocket:
            import websockets
            # Close the websocket
            try:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.close(),
                    self._loop
                )
            except:
                pass

        self.connected = False
        self._thread = None

    def _handle_message(self, data: Dict):
        """Xử lý message từ server"""
        msg_type = data.get("type")
        msg_data = data.get("data", {})

        if msg_type == "authenticated":
            self.player_id = msg_data.get("player_id")
            if self.on_connected:
                self.on_connected()

        elif msg_type == "searching":
            if self.on_searching:
                self.on_searching()

        elif msg_type == "match_found":
            self.in_match = True
            self.match_id = msg_data.get("match_id")
            self.opponent_name = msg_data.get("opponent")
            you_are = msg_data.get("you_are")

            if self.on_match_found:
                self.on_match_found(self.match_id, self.opponent_name, you_are)

        elif msg_type == "opponent_state":
            if self.on_opponent_state:
                self.on_opponent_state(msg_data)

        elif msg_type == "opponent_action":
            if self.on_opponent_action:
                self.on_opponent_action(msg_data)

        elif msg_type == "score_update":
            scores = msg_data.get("scores", {})
            # Determine which score is mine vs opponent
            if self.player_id in scores:
                # This is simplified - need proper player identification
                pass

            if self.on_score_update:
                self.on_score_update(self.my_score, self.opponent_score)

        elif msg_type == "match_ended":
            self.in_match = False
            winner_id = msg_data.get("winner_id")
            scores = msg_data.get("scores", {})

            if self.on_match_ended:
                self.on_match_ended(winner_id, scores)

        elif msg_type == "chat_message":
            username = msg_data.get("username")
            message = msg_data.get("message")
            if self.on_chat_message:
                self.on_chat_message(username, message)

        elif msg_type == "error":
            error_msg = msg_data.get("message", "Unknown error")
            if self.on_error:
                self.on_error(error_msg)

        elif msg_type == "opponent_disconnected":
            self.in_match = False
            if self.on_error:
                self.on_error("Opponent disconnected!")

    # ==================== SEND METHODS ====================

    def search_match(self):
        """Tìm trận đấu"""
        if not self.connected:
            return
        self._send({"type": "search_match"})

    def cancel_search(self):
        """Hủy tìm trận"""
        if not self.connected:
            return
        self._send({"type": "cancel_search"})

    def send_game_state(self, state: Dict):
        """Gửi game state cho đối thủ"""
        if not self.connected or not self.in_match:
            return
        self._send({
            "type": "game_state",
            "data": state
        })

    def send_action(self, action: str, data: Dict):
        """Gửi action (jump, duck) cho đối thủ"""
        if not self.connected or not self.in_match:
            return
        self._send({
            "type": "player_action",
            "data": {
                "action": action,
                **data
            }
        })

    def update_score(self, score: int):
        """Cập nhật điểm số"""
        if not self.connected or not self.in_match:
            return
        self.my_score = score
        self._send({
            "type": "score_update",
            "data": {"score": score}
        })

    def end_match(self, winner_id: str):
        """Kết thúc trận đấu"""
        if not self.connected or not self.in_match:
            return
        self._send({
            "type": "match_end",
            "data": {"winner_id": winner_id}
        })
        self.in_match = False

    def send_chat(self, message: str):
        """Gửi chat message"""
        if not self.connected or not self.in_match:
            return
        self._send({
            "type": "chat_message",
            "data": {"message": message}
        })

    def ping(self):
        """Gửi ping để giữ kết nối"""
        if not self.connected:
            return
        self._send({"type": "ping"})

    def _send(self, message: Dict):
        """Gửi message (chạy trong thread)"""
        if not self._loop or not self.connected:
            return

        def send_msg():
            if self.websocket:
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.websocket.send(json.dumps(message)),
                        self._loop
                    )
                except:
                    pass

        if threading.current_thread() != self._thread:
            threading.Thread(target=send_msg, daemon=True).start()
        else:
            if self.websocket:
                asyncio.run_coroutine_threadsafe(
                    self.websocket.send(json.dumps(message)),
                    self._loop
                )


# Example usage:
if __name__ == "__main__":
    # Test connection
    client = MultiplayerClient()

    def on_connected():
        print("Connected! Searching for match...")
        client.search_match()

    def on_match_found(match_id, opponent, you_are):
        print(f"Match found! vs {opponent} (you are {you_are})")

    def on_score_update(my_score, opp_score):
        print(f"Score: {my_score} - {opp_score}")

    client.on_connected = on_connected
    client.on_match_found = on_match_found
    client.on_score_update = on_score_update

    print("Connecting to server...")
    if client.connect(username="TestPlayer"):
        print("Connected! Press Enter to quit...")
        input()
        client.disconnect()
    else:
        print("Failed to connect!")
