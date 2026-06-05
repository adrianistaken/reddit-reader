# Reddit Match Thread Recap

A private web app and CLI for turning Reddit Dota 2 match threads into compact markdown recaps for a Custom GPT workflow.

The web app wraps the existing `reddit_recap.py` behavior so the generated markdown stays close to the local script output.

## Features

- HTTP Basic Auth for the whole hosted app
- Paste a Reddit thread URL and generate markdown
- Shows title, subreddit, source URL, and sampled comment count
- Copy markdown to clipboard
- Download a safe `.md` filename based on the Reddit title
- No accounts, database, storage, or OpenAI API integration

## Environment

Copy `.env.example` and fill in real values:

```bash
cp .env.example .env
```

Required:

```env
APP_USERNAME=
APP_PASSWORD=
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=
```

Optional if your Reddit app setup needs script-user credentials:

```env
REDDIT_USERNAME=
REDDIT_PASSWORD=
```

Do not commit real `.env` files.

## Local Web App

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend, in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. API requests proxy to `http://127.0.0.1:8000`.

For production-like local serving from FastAPI:

```bash
cd frontend
npm install
npm run build

cd ../backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. Basic Auth protects the built frontend and `/api/recap`.

## CLI Usage

The original CLI still works:

```bash
python reddit_recap.py "https://www.reddit.com/r/DotA2/comments/abc123/match_thread_ti_finals/"
```

Fast mode:

```bash
python reddit_recap.py "https://www.reddit.com/r/DotA2/comments/abc123/..." --mode fast
```

Custom sample budget:

```bash
python reddit_recap.py "https://..." --max-comments 40 --top 15 --controversial 15 --new 10
```

Outputs are written to `./outputs/`.

## API

`POST /api/recap`

Request:

```json
{
  "url": "https://www.reddit.com/r/DotA2/comments/..."
}
```

Response:

```json
{
  "title": "Post title here",
  "subreddit": "DotA2",
  "url": "https://reddit.com/r/DotA2/comments/...",
  "comment_count": 60,
  "markdown": "# Reddit Recap...",
  "filename": "2026-05-30_blast-slam-vii-thread.md"
}
```

## Deployment

Render works as a single Python web service:

1. Add the environment variables from `.env.example`.
2. Use a build command that installs Python and frontend dependencies, then builds Vue:

```bash
pip install -r backend/requirements.txt && cd frontend && npm install && npm run build
```

3. Use this start command:

```bash
cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

FastAPI serves both `/api/recap` and the built frontend from `frontend/dist`.
