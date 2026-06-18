# practi 🎓

RAG chatbot for **practicum and internship** students. The stack is a **Next.js** frontend (Vercel) and a **FastAPI** backend (Render) that answers from a local knowledge base under `backend/docs`.

## Architecture

| Piece        | Technology                                                                 |
| ------------ | ---------------------------------------------------------------------------- |
| Frontend     | Next.js (App Router), Tailwind CSS, `NEXT_PUBLIC_API_URL` → backend         |
| Backend      | FastAPI, LangChain, Groq (`llama3-8b-8192`), ChromaDB (in-memory), ST embeds |
| Embeddings   | `sentence-transformers/all-MiniLM-L6-v2`                                     |
| Vector store | Chroma persisted to `backend/chroma_db/` (rebuilt if missing)         |

## Repository layout

```text
/backend
    app/              # FastAPI application modules
    main.py         # Entry point & routes
    rag.py          # RAG logic
    schemas.py      # Pydantic models
    config.py       # Settings & env
  ingest.py         # Standalone ingestion script
  docs/             # Knowledge base
  requirements.txt
  runtime.txt       # Python 3.11 for Render
  README.md         # Backend setup, testing, deploy
/frontend           # Next.js app
README.md
LICENSE
```

## Local development

### Backend

Use **Python 3.11**. See [backend/README.md](backend/README.md) for full setup.

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# edit .env and set GROQ_API_KEY
python ingest.py  # Optional: pre-ingest docs
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```powershell
cd frontend
copy .env.example .env.local
# set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Testing

### Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

## Knowledge base

Add files to `backend/docs/` using this naming convention:

- `A` = announcement, `S` = slides
- One per date: `<A|S>_<YYYYMMDD>.<ext>` (e.g. `A_20260617.pdf`)
- Multiple same date: `<A|S>_<YYYYMMDD>_<Number>.<ext>` (e.g. `S_20260617_01.pptx`)

Supported: `.pdf`, `.docx`, `.pptx`, `.md`, `.txt`

## Deploy

### Backend (Render)

1. New **Web Service**, root directory **`backend`**.
2. Python **3.11** via `backend/runtime.txt`.
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Health check path:** `/health`
6. **Environment variables:**
   - `GROQ_API_KEY`
   - `CORS_ORIGINS` (your Vercel URL)

### Frontend (Vercel)

1. New project, root directory **`frontend`**.
2. **Environment variable:** `NEXT_PUBLIC_API_URL` = your Render backend URL.

Ensure `CORS_ORIGINS` on the backend includes your Vercel domain.

## License

MIT — see [LICENSE](./LICENSE).
