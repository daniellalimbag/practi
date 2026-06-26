# practi backend

FastAPI RAG service for the practi chatbot.

## Requirements

- Python **3.11**
- **Local:** [Ollama](https://ollama.com/) running with a pulled model (e.g. `ollama pull llama3.1:8b`)
- **Cloud / deploy:** Groq API key

## Setup

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional: `copy .env.example .env` — only needed for **Groq** (`GROQ_API_KEY`) or production `CORS_ORIGINS`. Local Ollama works without a `.env` file; pick **Local** in the frontend sidebar.

## Run locally

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Health: `GET http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

Run `python ingest.py` after adding or changing files in `backend/docs/`. **Stop the backend first** (uvicorn locks `chroma_db/` on Windows).

## LLM providers

| Mode | How | API key? |
|------|-----|----------|
| **Local** | Select **Local** in the frontend sidebar | No |
| **Cloud** | Select **Cloud** in the sidebar, or set `GROQ_API_KEY` in `.env` | Yes (Groq) |

Each chat request tells the backend which provider to use. Ollama defaults (`localhost:11434`, `llama3.1:8b`) are built in — no `.env` required for local mode.

## Knowledge base

Place documents in `backend/docs/`.

**Formats:** `.pdf`, `.docx`, `.pptx`, `.md`, `.txt`

**Naming convention:**

- `A` = announcement, `S` = slides
- One document on a date: `<A|S>_<YYYYMMDD>.<ext>`
- Multiple on the same date: `<A|S>_<YYYYMMDD>_<Number>.<ext>`

Examples:

- `A_20260617.pdf` — announcement, 17 June 2026
- `S_20260617_01.pptx` — first slides deck that day
- `S_20260617_02.pptx` — second slides deck that day

After changing docs: `python ingest.py`

### Vision ingest (images in PDF/DOCX/PPTX)

By default, ingest sends images to a **vision model** and stores the extracted text in Chroma. This captures screenshots, diagrams, and image-only slides.

1. Pull a vision model (Ollama default):
   ```powershell
   ollama pull llama3.2-vision
   ```
2. Run ingest (slow — one vision call per image):
   ```powershell
   python ingest.py
   ```

| Setting | Default | Purpose |
|---------|---------|---------|
| `ENABLE_VISION_INGEST` | `true` | Toggle vision at ingest |
| `VISION_PROVIDER` | `ollama` | `ollama` or `groq` |
| `OLLAMA_VISION_MODEL` | `llama3.2-vision` | Local vision model |
| `GROQ_VISION_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` | Groq vision model |

To skip vision (faster ingest): set `ENABLE_VISION_INGEST=false` in `.env`.

Debug the index: `python inspect_db.py search "your phrase"`

## Tests

```powershell
pytest -v
```

## Deploy to Render

1. Root directory: `backend`
2. Build: `pip install -r requirements.txt`
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Health check: `/health`
5. Env: `GROQ_API_KEY`, `CORS_ORIGINS` (your Vercel URL)

Ollama is local-only; Render cannot reach Ollama on your machine.
