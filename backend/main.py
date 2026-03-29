import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from database import Base, engine  # noqa: E402
from routers import roadmap  # noqa: E402

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Career Roadmap Generator")

origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
if not origins:
    raise ValueError("ALLOWED_ORIGINS is not set")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roadmap.router)


@app.get("/health")
def health():
    return {"status": "ok"}
