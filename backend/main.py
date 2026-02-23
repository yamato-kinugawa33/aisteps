from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import Base, engine
from routers import roadmap

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Career Roadmap Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(roadmap.router)


@app.get("/health")
def health():
    return {"status": "ok"}
