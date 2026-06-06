import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .auth import require_basic_auth
from .recap_service import RecapError, build_recap


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env", override=False)

frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.environ.get("FRONTEND_ORIGIN", "").split(",")
    if origin.strip()
]
allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *frontend_origins,
    "https://aware-youth-production-dc75.up.railway.app",
]

app = FastAPI(
    title="Reddit Match Thread Recap",
    dependencies=[Depends(require_basic_auth)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)


class RecapRequest(BaseModel):
    url: str


class RecapResponse(BaseModel):
    title: str
    subreddit: str
    url: str
    comment_count: int
    markdown: str
    filename: str


@app.post("/api/recap", response_model=RecapResponse)
def recap(payload: RecapRequest):
    try:
        return build_recap(payload.url)
    except RecapError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = FRONTEND_DIST / path
        if path and target.is_file():
            return FileResponse(target)
        return FileResponse(FRONTEND_DIST / "index.html")
