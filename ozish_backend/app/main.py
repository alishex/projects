from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, coach, food, push, reminders, weight, workouts
from app.services.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="Ozish API", root_path="/ozish-api", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(food.router)
app.include_router(weight.router)
app.include_router(workouts.router)
app.include_router(push.router)
app.include_router(reminders.router)
app.include_router(coach.router)


@app.get("/health")
def health():
    return {"status": "ok"}
