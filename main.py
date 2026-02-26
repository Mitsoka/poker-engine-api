from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from db.database import Base, db
   

app = FastAPI()


from routes.auth import auth
from routes.poker_router import router

app.include_router(auth)
app.include_router(router)



Base.metadata.create_all(bind=db)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7700", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



if __name__ == "__main__":
	uvicorn.run("main:app", host="0.0.0.0", port=8000)