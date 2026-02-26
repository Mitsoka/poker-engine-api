from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Adiciona uma nova conexão WebSocket"""
        self.active_connections.add(websocket)
        logger.debug(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove uma conexão WebSocket"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.debug(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_to(self, websocket: WebSocket, message: dict):
        """Envia mensagem para um WebSocket específico"""
        try:
            await websocket.send_json(message)
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Error sending to websocket: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Envia mensagem para todos os WebSockets conectados"""
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.add(connection)
        
        # Limpar conexões desconectadas
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_except(self, exclude_websocket: WebSocket, message: dict):
        """Envia mensagem para todos exceto um WebSocket específico"""
        disconnected = set()
        
        for connection in self.active_connections:
            if connection == exclude_websocket:
                continue
                
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.add(connection)
        
        for conn in disconnected:
            self.disconnect(conn)