from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    username = Column(String, nullable=False, index=True)
    ip = Column(String, nullable=True)

    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    jti = Column(String, nullable=False, unique=True, index=True)
    
    created_at = Column(DateTime, server_default=func.now())
    expire_at = Column(DateTime)