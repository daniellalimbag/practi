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

**Naming convention:** `<Date>_<Number>.<ext>`

Examples:

- `2026-06-17_01.pdf`
- `2026-06-17_02.docx`

The date is stored in metadata and returned in `sources[].date`.

Restart the server after adding or changing files so Chroma rebuilds from disk.

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
- Chroma is in-memory; the index is rebuilt on every process start from `backend/docs`.
- Use `GET /health` as the Render health check path.

## API contract

```text
POST /api/chat
Request:  { "message": string, "history": [{ "role": "user"|"assistant", "content": string }] }
Response: { "answer": string, "sources": [{ "source": string, "excerpt": string, "date": string|null }] }
```
