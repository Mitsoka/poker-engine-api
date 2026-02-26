from fastapi import WebSocket, WebSocketException, status
from sqlalchemy.orm import Session
import logging
from typing import Optional

from core.security.jwt import decode_token
from core.enums import TokenType
from db.models import User

logger = logging.getLogger(__name__)

async def get_current_user_ws(
    websocket: WebSocket,
    session: Session
) -> Optional[User]:
    """
    Obtém o usuário atual a partir do token no cookie do WebSocket
    """
    # Tentar obter token do cookie ou query parameter
    access_token = websocket.cookies.get("access_token")
    
    if not access_token:
        # Tentar obter do header Sec-WebSocket-Protocol ou query string
        query_params = websocket.query_params
        access_token = query_params.get("token")
    
    if not access_token:
        logger.warning("No access token found in WebSocket connection")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Token de autenticação não fornecido"
        )
    
    try:
        # Decodificar token
        payload = decode_token(access_token)
        
        if payload.get("type") != TokenType.ACCESS.value:
            logger.warning(f"Invalid token type: {payload.get('type')}")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Tipo de token inválido"
            )
        
        user_id = int(payload.get("sub"))
        
        # Buscar usuário no banco
        user = session.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            logger.warning(f"User not found or inactive: {user_id}")
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Usuário não encontrado ou inativo"
            )
        
        return user
        
    except ValueError as e:
        logger.error(f"Error parsing user ID: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="ID de usuário inválido"
        )
    except Exception as e:
        logger.error(f"Unexpected error in authentication: {e}")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Erro de autenticação"
        )