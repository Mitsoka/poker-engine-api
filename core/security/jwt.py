import uuid
from datetime import datetime, timedelta

from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException

from core.config import settings
from core.enums import TokenType


def create_token(user_id: int, token_type: TokenType):
    
    if token_type == TokenType.ACCESS:
        exp = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXP)
    else:
        exp = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXP)
        
    jti = str(uuid.uuid4())
    
    payload = {
        "sub": str(user_id),
        "type": token_type.value,
        "jti": jti,
        "exp": exp,
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return token, jti, exp
    

def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Faça login novamente"
        )

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )
    
    