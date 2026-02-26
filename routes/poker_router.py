from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import logging

from deps import get_db
from core.websocket.deps_ws import get_current_user_ws
from core.websocket.ws import ConnectionManager
from core.poker.room_manager import GameRoomManager  # <-- Import da classe gerenciadora
from db.models import User

router = APIRouter(prefix="/game", tags=["Poker"])

logger = logging.getLogger(__name__)

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

room_manager = GameRoomManager()

@router.websocket("/poker/{room_id}")
async def poker_websocket(
    websocket: WebSocket, 
    room_id: str,
    db: Session = Depends(get_db)
):
    await websocket.accept()
    
    try:
        user = await get_current_user_ws(websocket, db)
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        logger.error(f"Auth failed: {e}")
        return
    
    room = room_manager.get_room(room_id)
    if not room:
        room = room_manager.create_room(room_id)
    
    conn_manager = room["connection_manager"]
    await conn_manager.connect(websocket)
    
    player_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "join":
                chips = data.get("chips", 1000)
                
                player_id = len(room["players"])
                room["players"][websocket] = {
                    "player_id": player_id,
                    "chips": chips,
                    "user_id": user.id,
                    "username": user.username
                }
                room["player_stacks"].append(chips)
                
                await conn_manager.send_to(websocket, {
                    "type": "joined",
                    "player_id": player_id,
                    "players_count": len(room["players"])
                })
                
                await conn_manager.broadcast_except(websocket, {
                    "type": "player_joined",
                    "player_id": player_id,
                    "players_count": len(room["players"])
                })
            
            elif action == "start":
                if len(room["players"]) < 2:
                    await conn_manager.send_to(websocket, {
                        "type": "error",
                        "message": "Mínimo de 2 jogadores necessário"
                    })
                    continue
                
                first_player = next(iter(room["players"].values()))
                if first_player["player_id"] != 0:
                    await conn_manager.send_to(websocket, {
                        "type": "error",
                        "message": "Apenas o primeiro jogador pode iniciar a partida"
                    })
                    continue
                
                room["game_session"] = PokerGameSession(
                    player_count=len(room["players"]),
                    starting_stacks=tuple(room["player_stacks"]),
                    small_blind=50,
                    big_blind=100
                )
                
                game_state = room["game_session"].get_game_state()
                
                await conn_manager.broadcast({
                    "type": "game_started",
                    "state": game_state
                })
            
            elif action == "move" and room["game_session"]:
                player_info = room["players"].get(websocket)
                if not player_info:
                    continue
                
                current_player = room["game_session"].get_current_player()
                if current_player != player_info["player_id"]:
                    await conn_manager.send_to(websocket, {
                        "type": "error",
                        "message": "Não é seu turno"
                    })
                    continue
                
                move = data.get("move")
                amount = data.get("amount", 0)
                
                try:
                    move_result = room["game_session"].process_move(
                        player_id=player_info["player_id"],
                        move=move,
                        amount=amount
                    )
                    
                    if move_result["success"]:
                        
                        game_state = room["game_session"].get_game_state()
                        
                        if room["game_session"].is_hand_complete():
                            hand_result = room["game_session"].get_hand_result()
                            await conn_manager.broadcast({
                                "type": "hand_complete",
                                "state": game_state,
                                "result": hand_result
                            })
                        else:
                            await conn_manager.broadcast({
                                "type": "update",
                                "state": game_state
                            })
                    else:
                        await conn_manager.send_to(websocket, {
                            "type": "error",
                            "message": move_result["error"]
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing move: {e}")
                    await conn_manager.send_to(websocket, {
                        "type": "error",
                        "message": "Erro interno ao processar jogada"
                    })
            
            elif action == "get_state" and room["game_session"]:
                game_state = room["game_session"].get_game_state(player_id)
                await conn_manager.send_to(websocket, {
                    "type": "state",
                    "state": game_state
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
        conn_manager.disconnect(websocket)
        
        if websocket in room["players"]:
            del room["players"][websocket]
       
        if len(room["players"]) == 0:
            room_manager.remove_room(room_id)
        else:
            await conn_manager.broadcast({
                "type": "player_left",
                "players_count": len(room["players"])
            })
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        conn_manager.disconnect(websocket)