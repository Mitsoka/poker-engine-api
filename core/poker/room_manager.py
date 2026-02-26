from typing import Dict, Optional, Any
from core.websocket.ws import ConnectionManager
from core.poker.poker_session import PokerGameSession
import logging


class GameRoomManager:
    def __init__(self):
        self.rooms: dict[str, dict] = {}  
    
    def create_room(self, room_id: str) -> dict:
        self.rooms[room_id] = {
            "connection_manager": ConnectionManager(),
            "game_session": None,
            "players": {},
            "player_stacks": []
        }
        return self.rooms[room_id]
    
    def get_room(self, room_id: str) -> Optional[dict]:
        return self.rooms.get(room_id)
    
    def remove_room(self, room_id: str):
        if room_id in self.rooms:
            del self.rooms[room_id]
