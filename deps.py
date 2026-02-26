from fastapi import Depends, Request, HTTPException
from sqlalchemy.orm import Session
from db.database import SessionLocal
from db.models import User
from core.security.jwt import decode_token
from core.enums import TokenType


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()        
        

def get_current_user(request: Request, session: Session = Depends(get_db)):
    
    access_token = request.cookies.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Não autenticado"
        )

    payload = decode_token(access_token)

    if payload.get("type") != TokenType.ACCESS.value:
        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    user_id = int(payload.get("sub"))

    user = session.query(User).filter(
        User.id == user_id,
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuário não autorizado"
        )

    return user