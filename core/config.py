from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Minha API Insana"
    VERSION: str = "1.0.0"
    
    DATABASE_URL: str

    SECRET_KEY: str
    ALGORITHM: str

    ACCESS_TOKEN_EXP: int = 30   # minutos
    REFRESH_TOKEN_EXP: int = 30  # dias

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()