from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import tasks

app = FastAPI()

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount router at /api/v1 (recommended)
app.include_router(tasks.router, prefix="/api/v1")

# Also mount at /tasks for backward compatibility with frontend
app.include_router(tasks.router, prefix="/tasks", tags=["tasks-legacy"])

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Todo App Backend!"}


@app.on_event("startup")
async def startup_event():
    routes = [{"path": route.path, "name": route.name} for route in app.routes]
    print("Registered routes:", routes)