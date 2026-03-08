"""
Multiplayer Server - WebSocket server for real-time multiplayer gaming
Run: python server.py

Requirements:
    pip install websockets

This is a simple WebSocket server that handles:
- User authentication
- Matchmaking (finding opponents)
- Game state synchronization
- Real-time position updates
"""
import asyncio
import json
import logging
import uuid
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PlayerState(Enum):
    """Trạng thái người chơi"""
    IDLE = "idle"
    SEARCHING = "searching"
    IN_MATCH = "in_match"
    DISCONNECTED = "disconnected"


@dataclass
class Player:
    """Thông tin người chơi"""
    id: str
    username: str
    websocket: Optional[object] = None
    state: PlayerState = PlayerState.IDLE
    current_match: Optional[str] = None
    score: int = 0
    last_seen: float = field(default_factory=time.time)


@dataclass
class Match:
    """Thông tin trận đấu"""
    id: str
    player1_id: str
    player2_id: str
    game_mode: str = "pvp"
    created_at: float = field(default_factory=time.time)
    status: str = "waiting"  # waiting, in_progress, finished
    winner_id: Optional[str] = None
    scores: Dict[str, int] = field(default_factory=dict)


class GameServer:
    """Game server quản lý kết nối và trận đấu"""

    def __init__(self):
        # Kết nối theo player_id
        self.players: Dict[str, Player] = {}

        # Kết nối theo websocket
        self.connections: Dict[object, str] = {}

        # Đang tìm trận
        self.searching_players: Set[str] = set()

        # Các trận đấu
        self.matches: Dict[str, Match] = {}

        # Matchmaking queue
        self.match_queue: asyncio.Queue = asyncio.Queue()

    def add_player(self, player_id: str, username: str, websocket: object) -> Player:
        """Thêm người chơi mới"""
        player = Player(id=player_id, username=username, websocket=websocket)
        self.players[player_id] = player
        self.connections[websocket] = player_id
        logger.info(f"Player {username} ({player_id}) connected")
        return player

    def remove_player(self, websocket: object):
        """Xóa người chơi"""
        if websocket in self.connections:
            player_id = self.connections[websocket]
            if player_id in self.players:
                player = self.players[player_id]
                player.state = PlayerState.DISCONNECTED

                # Nếu đang trong trận, thông báo cho đối thủ
                if player.current_match:
                    self._notify_opponent(player.current_match, player_id, "opponent_disconnected")

                # Xóa khỏi queue tìm trận
                self.searching_players.discard(player_id)

                logger.info(f"Player {player.username} disconnected")

            del self.connections[websocket]

    async def send_to_player(self, player_id: str, message: dict):
        """Gửi message cho người chơi"""
        if player_id in self.players:
            player = self.players[player_id]
            if player.websocket and player.state != PlayerState.DISCONNECTED:
                try:
                    await player.websocket.send(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error sending to {player.username}: {e}")

    async def broadcast_to_match(self, match_id: str, message: dict, exclude: str = None):
        """Gửi message cho tất cả người trong trận"""
        if match_id in self.matches:
            match = self.matches[match_id]
            for pid in [match.player1_id, match.player2_id]:
                if pid != exclude:
                    await self.send_to_player(pid, message)

    def _notify_opponent(self, match_id: str, player_id: str, message_type: str, data: dict = None):
        """Thông báo cho đối thủ"""
        if match_id in self.matches:
            match = self.matches[match_id]
            opponent_id = match.player2_id if match.player1_id == player_id else match.player1_id
            asyncio.create_task(self.send_to_player(opponent_id, {
                "type": message_type,
                "data": data or {}
            }))

    async def handle_message(self, player_id: str, message: dict):
        """Xử lý message từ người chơi"""
        msg_type = message.get("type")
        data = message.get("data", {})

        if msg_type == "search_match":
            await self._handle_search_match(player_id)

        elif msg_type == "cancel_search":
            await self._handle_cancel_search(player_id)

        elif msg_type == "join_match":
            match_id = data.get("match_id")
            await self._handle_join_match(player_id, match_id)

        elif msg_type == "game_state":
            await self._handle_game_state(player_id, data)

        elif msg_type == "player_action":
            await self._handle_player_action(player_id, data)

        elif msg_type == "score_update":
            await self._handle_score_update(player_id, data)

        elif msg_type == "match_end":
            await self._handle_match_end(player_id, data)

        elif msg_type == "chat_message":
            await self._handle_chat(player_id, data)

        elif msg_type == "ping":
            # Respond with pong
            await self.send_to_player(player_id, {"type": "pong"})

        else:
            logger.warning(f"Unknown message type: {msg_type}")

    async def _handle_search_match(self, player_id: str):
        """Xử lý tìm trận"""
        player = self.players.get(player_id)
        if not player:
            return

        # Thêm vào queue tìm trận
        self.searching_players.add(player_id)
        player.state = PlayerState.SEARCHING

        await self.send_to_player(player_id, {
            "type": "searching",
            "data": {"message": "Looking for opponent..."}
        })

        # Tìm đối thủ
        opponent_id = None
        for pid in self.searching_players:
            if pid != player_id:
                opponent_id = pid
                break

        if opponent_id:
            # Tìm thấy đối thủ
            self.searching_players.discard(player_id)
            self.searching_players.discard(opponent_id)

            # Tạo trận đấu
            match_id = str(uuid.uuid4())[:8]
            match = Match(
                id=match_id,
                player1_id=player_id,
                player2_id=opponent_id,
                game_mode="pvp",
                status="in_progress"
            )
            match.scores[player_id] = 0
            match.scores[opponent_id] = 0

            self.matches[match_id] = match

            # Cập nhật trạng thái player
            player.state = PlayerState.IN_MATCH
            player.current_match = match_id
            player.score = 0

            opponent = self.players[opponent_id]
            opponent.state = PlayerState.IN_MATCH
            opponent.current_match = match_id
            opponent.score = 0

            # Thông báo cho cả hai
            await self.send_to_player(player_id, {
                "type": "match_found",
                "data": {
                    "match_id": match_id,
                    "opponent": opponent.username,
                    "you_are": "player1"
                }
            })

            await self.send_to_player(opponent_id, {
                "type": "match_found",
                "data": {
                    "match_id": match_id,
                    "opponent": player.username,
                    "you_are": "player2"
                }
            })

            logger.info(f"Match {match_id}: {player.username} vs {opponent.username}")

    async def _handle_cancel_search(self, player_id: str):
        """Hủy tìm trận"""
        self.searching_players.discard(player_id)
        if player_id in self.players:
            self.players[player_id].state = PlayerState.IDLE
            await self.send_to_player(player_id, {
                "type": "search_cancelled",
                "data": {}
            })

    async def _handle_join_match(self, player_id: str, match_id: str):
        """Tham gia trận đấu có sẵn"""
        if match_id not in self.matches:
            await self.send_to_player(player_id, {
                "type": "error",
                "data": {"message": "Match not found"}
            })
            return

        match = self.matches[match_id]
        if match.status != "waiting":
            await self.send_to_player(player_id, {
                "type": "error",
                "data": {"message": "Match already started"}
            })
            return

        # Join as player 2
        match.player2_id = player_id
        match.status = "in_progress"
        match.scores[player_id] = 0

        player = self.players[player_id]
        player.state = PlayerState.IN_MATCH
        player.current_match = match_id
        player.score = 0

        opponent = self.players[match.player1_id]

        # Notify both
        await self.send_to_player(player_id, {
            "type": "match_found",
            "data": {
                "match_id": match_id,
                "opponent": opponent.username,
                "you_are": "player2"
            }
        })

        await self.send_to_player(match.player1_id, {
            "type": "opponent_joined",
            "data": {"opponent": player.username}
        })

    async def _handle_game_state(self, player_id: str, data: dict):
        """Đồng bộ game state"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        if not player.current_match:
            return

        # Gửi state cho đối thủ
        await self._notify_opponent(player.current_match, player_id, "opponent_state", data)

    async def _handle_player_action(self, player_id: str, data: dict):
        """Xử lý action của người chơi"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        if not player.current_match:
            return

        # Gửi action cho đối thủ
        await self._notify_opponent(player.current_match, player_id, "opponent_action", data)

    async def _handle_score_update(self, player_id: str, data: dict):
        """Cập nhật điểm số"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        if not player.current_match:
            return

        match = self.matches.get(player.current_match)
        if not match:
            return

        # Cập nhật điểm
        score = data.get("score", 0)
        match.scores[player_id] = score
        player.score = score

        # Gửi cho đối thủ
        await self._notify_opponent(player.current_match, player_id, "score_update", {
            "player_id": player_id,
            "score": score,
            "scores": match.scores
        })

    async def _handle_match_end(self, player_id: str, data: dict):
        """Kết thúc trận đấu"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        if not player.current_match:
            return

        match = self.matches.get(player.current_match)
        if not match:
            return

        winner_id = data.get("winner_id")
        match.winner_id = winner_id
        match.status = "finished"

        # Thông báo cho cả hai
        await self.broadcast_to_match(player.current_match, {
            "type": "match_ended",
            "data": {
                "winner_id": winner_id,
                "scores": match.scores
            }
        })

        # Cleanup
        for pid in [match.player1_id, match.player2_id]:
            if pid in self.players:
                self.players[pid].state = PlayerState.IDLE
                self.players[pid].current_match = None

        logger.info(f"Match {player.current_match} ended. Winner: {winner_id}")

    async def _handle_chat(self, player_id: str, data: dict):
        """Xử lý chat message"""
        if player_id not in self.players:
            return

        player = self.players[player_id]
        if not player.current_match:
            return

        message = data.get("message", "")
        if not message:
            return

        # Gửi cho đối thủ
        await self._notify_opponent(player.current_match, player_id, "chat_message", {
            "player_id": player_id,
            "username": player.username,
            "message": message,
            "timestamp": time.time()
        })


async def handle_client(websocket, path, server: GameServer):
    """Xử lý kết nối client"""
    player_id = None
    try:
        # Đợi message đầu tiên là auth
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type")

            if msg_type == "auth":
                # Xác thực người chơi
                player_id = data.get("player_id", str(uuid.uuid4()))
                username = data.get("username", f"Player_{player_id[:4]}")

                server.add_player(player_id, username, websocket)

                await websocket.send(json.dumps({
                    "type": "authenticated",
                    "data": {"player_id": player_id, "username": username}
                }))

                logger.info(f"Player {username} authenticated")

            elif msg_type == "game_action":
                if player_id:
                    await server.handle_message(player_id, data)

            elif msg_type == "disconnect":
                break

    except Exception as e:
        logger.error(f"Client error: {e}")

    finally:
        if player_id:
            server.remove_player(websocket)


async def main():
    """Khởi động server"""
    import argparse

    parser = argparse.ArgumentParser(description="DinoRacer Multiplayer Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind")
    args = parser.parse_args()

    server = GameServer()

    logger.info(f"Starting DinoRacer Multiplayer Server on {args.host}:{args.port}")

    async with websockets.serve(
        lambda ws, path: handle_client(ws, path, server),
        args.host,
        args.port
    ):
        logger.info("Server started successfully!")
        logger.info(f"Connect clients to: ws://{args.host}:{args.port}")

        # Keep running
        await asyncio.Future()


if __name__ == "__main__":
    try:
        import websockets
        asyncio.run(main())
    except ImportError:
        print("Please install websockets: pip install websockets")
