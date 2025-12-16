from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import tasks
from .api import chat

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks-legacy"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(chat.router, prefix="/chat", tags=["chat-legacy"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Todo App Backend!"}