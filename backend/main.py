import os

from dotenv import load_dotenv

load_dotenv()

_missing = [v for v in ("DATABASE_URL", "GEMINI_API_KEY", "ALLOWED_ORIGINS") if not os.getenv(v)]
if _missing:
    raise ValueError(f"Required environment variables are not set: {', '.join(_missing)}")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from db.database import Base, get_engine  # noqa: E402
from routers import roadmap  # noqa: E402

Base.metadata.create_all(bind=get_engine())

app = FastAPI(title="Career Roadmap Generator")

origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

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
