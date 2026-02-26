from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from deps import get_db, get_current_user
from core.security.password import hash_pwd, verify_pwd
from core.security.jwt import create_token, decode_token
from core.security.cookies import CookieManager
from schemas import RegistScm, LoginScm
from db.models import User, RefreshToken
from core.enums import TokenType 


auth = APIRouter(prefix="/auth", tags=["Autenticação"])


@auth.post("/register")
async def register(data: RegistScm, request: Request, session: Session = Depends(get_db)):
	
	if session.query(User).filter(User.email == data.email).first():
	   raise HTTPException(status_code=409, detail="Esse e-mail já existe.")
		
	password_crypt = hash_pwd(data.password)
	
	new_user = User(
	email=data.email,
	password=password_crypt, 
	username=data.username,
	ip=request.client.host if request.client else None
	)
	session.add(new_user)
	session.commit()
	session.refresh(new_user)
	
	
	access_token, access_jti, access_exp = create_token(new_user.id, TokenType.ACCESS)
	refresh_token, refresh_jti, refresh_exp = create_token(new_user.id, TokenType.REFRESH)
	
	refresh_db = RefreshToken(
	user_id=new_user.id,
	jti=refresh_jti,
	expire_at=refresh_exp
	)
	session.add(refresh_db)
	session.commit()
	session.refresh(refresh_db)
	
	res = JSONResponse(
	content={"msg": "Registro concluído"},
	status_code=201
    )
    
	CookieManager.set_all(res, access_token, refresh_token)
	return res
	
	

@auth.post("/login")
async def login(data: LoginScm, session: Session = Depends(get_db)):
    
    user = session.query(User).filter(User.email==data.email).first()
    
    if not user or not verify_pwd(data.password, user.password):
        raise HTTPException(status_code=401, detail="E-mail ou senha invalido")
        
    access_token, access_jti, access_exp = create_token(user.id, TokenType.ACCESS)
    refresh_token, refresh_jti, refresh_exp = create_token(user.id, TokenType.REFRESH)
    
    refresh_db = RefreshToken(
	user_id=user.id,
	jti=refresh_jti,
	expire_at=refresh_exp
	)
    session.add(refresh_db)
    session.commit()
    session.refresh(refresh_db)
    
    res = JSONResponse(
    content={"msg": "Login concluído"},
    status_code=200
    )
    
    CookieManager.set_all(res, access_token, refresh_token)
    
    return res
    
    

@auth.post("/logout")
async def logout(request: Request, user: User = Depends(get_current_user), session: Session = Depends(get_db)):
	
	refresh = request.cookies.get("refresh_token")  
	
	if not refresh:
	   raise HTTPException(status_code=401, detail="Token ausente")
	   
	payload = decode_token(refresh)
	
	if payload.get("type") != TokenType.REFRESH.value:
		raise HTTPException(status_code=401, detail="Token inválido")	
	
	user_id = int(payload.get("sub"))
	jti = payload.get("jti")
	
	refresh_db = session.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.jti == jti, RefreshToken.expire_at > datetime.utcnow()).first()  
	
	if not refresh_db:
		raise HTTPException(status_code=401, detail="Token invalido")  
		
	session.delete(refresh_db)
	session.commit()  
	
	res = JSONResponse(  
    content={"msg": "Logout concluído"},  
    status_code=200  
)

	CookieManager.delete_all(res)
	
	return res
	

@auth.post("/auto-refresh")
async def auto_refresh(request: Request, session: Session = Depends(get_db)):

    refresh = request.cookies.get("refresh_token")

    if not refresh:
        raise HTTPException(status_code=401, detail="Token ausente")

    payload = decode_token(refresh)

    if payload.get("type") != TokenType.REFRESH.value:
        raise HTTPException(status_code=401, detail="Token inválido")

    user_id = int(payload.get("sub"))
    jti = payload.get("jti")

    refresh_db = session.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.jti == jti,
        RefreshToken.expire_at > datetime.utcnow()
    ).first()

    if not refresh_db:
        raise HTTPException(status_code=401, detail="Token inválido")

    session.delete(refresh_db)

    access_token, access_jti, access_exp = create_token(user_id, TokenType.ACCESS)
    new_refresh_token, new_refresh_jti, new_refresh_exp = create_token(user_id, TokenType.REFRESH)

    new_refresh_db = RefreshToken(
        user_id=user_id,
        jti=new_refresh_jti,
        expire_at=new_refresh_exp
    )

    session.add(new_refresh_db)
    session.commit()
    session.refresh(new_refresh_db)

    res = JSONResponse(
        content={"msg": "Token renovado"},
        status_code=200
    )

    CookieManager.set_all(res, access_token, new_refresh_token)

    return res