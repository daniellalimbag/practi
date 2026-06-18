# practi backend

FastAPI RAG service for the practi chatbot.

## Requirements

- Python **3.11** (see `runtime.txt` for Render)
- Groq API key

## Setup

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy env file and add your key:

```powershell
copy .env.example .env
```

Edit `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Run locally

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# Optional: Ingest documents (persists to ./chroma_db)
python ingest.py

# Run API (will build index if ./chroma_db is missing)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- Chat: `POST http://localhost:8000/api/chat`

Example request:

```json
{
  "message": "What should I do before day one?",
  "history": []
}
```

## Knowledge base

Place documents in `backend/docs/`.

**Supported formats:** `.pdf`, `.docx`, `.pptx`, `.md`, `.txt`

**Naming convention:**

- `A` = announcement, `S` = slides
- One document on a date: `<A|S>_<YYYYMMDD>.<ext>`
- Multiple on the same date: `<A|S>_<YYYYMMDD>_<Number>.<ext>`

Examples:

- `A_20260617.pdf` — announcement, 17 June 2026
- `S_20260617_01.pptx` — first slides deck that day
- `S_20260617_02.pptx` — second slides deck that day

Type and date are stored in metadata and returned in `sources[].type` and `sources[].date`.

### Date-aware retrieval

Each chat request includes a **query date** (the user's local date from the frontend, or today on the server). Retrieval only includes documents whose filename date is **on or before** that date, so future or outdated-after-query-date docs are excluded.

Re-run ingest after changing docs so `doc_date` metadata is present in `chroma_db/`:

```powershell
python ingest.py
```

### Rebuilding the index

If you add or change files, you can rebuild the index by running:

```powershell
python ingest.py
```

Alternatively, delete the `backend/chroma_db/` folder and restart the server.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

Tests mock Groq and do not require a real API key.

## Deploy to Render

1. Create a **Web Service** with root directory `backend`.
2. Render uses Python 3.11 from `runtime.txt`.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Environment variables:**
   - `GROQ_API_KEY` (required)
   - `CORS_ORIGINS` (your Vercel URL, e.g. `https://your-app.vercel.app`)

**Notes:**

- First deploy may take several minutes while `sentence-transformers` downloads the embedding model.
- Chroma is persisted to disk at `backend/chroma_db/`. The index is loaded on startup; if missing, it is rebuilt from `backend/docs/`.
- Use `GET /health` as the Render health check path.

## API contract

```text
POST /api/chat
Request:  { "message": string, "history": [...], "query_date": "YYYY-MM-DD" (optional) }
Response: { "answer": string, "sources": [...], "query_date": string }
```
