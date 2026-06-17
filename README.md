# PractiGuide 🎓

RAG chatbot for **practicum and internship** students. The stack is a **Next.js** frontend (Vercel) and a **FastAPI** backend (Render) that answers from a local knowledge base under `backend/docs`.

## Architecture

| Piece        | Technology                                                                 |
| ------------ | ---------------------------------------------------------------------------- |
| Frontend     | Next.js (App Router), Tailwind CSS, `NEXT_PUBLIC_API_URL` → backend         |
| Backend      | FastAPI, LangChain, Groq (`llama3-8b-8192`), ChromaDB (in-memory), ST embeds |
| Embeddings   | `sentence-transformers/all-MiniLM-L6-v2`                                     |
| Vector store | Chroma rebuilt from `backend/docs` on each process start                     |

## Repository layout

```text
/backend
  main.py           # FastAPI app + RAG
  requirements.txt
  docs/             # Knowledge base (.md / .txt)
/frontend           # Next.js app
README.md
LICENSE
```

## Local development

### 1. Backend

1. Create a virtual environment and install dependencies. Use **Python 3.10+** (3.11 recommended); older runtimes may lack prebuilt wheels for some dependencies (for example `greenlet` on Windows without the C++ build tools).

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # macOS / Linux
   pip install -r requirements.txt
   ```

2. Copy `backend/.env.example` to `backend/.env` and set `GROQ_API_KEY` (from [Groq Console](https://console.groq.com/)).

3. Run the API (first run downloads the embedding model):

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Optional: set `CORS_ORIGINS` (comma-separated) if the frontend is not on `localhost:3000`.

- Health: `GET http://localhost:8000/health`
- Chat: `POST http://localhost:8000/api/chat` with JSON body:

  ```json
  {
    "message": "What should I do before day one?",
    "history": [{ "role": "user", "content": "Hi" }]
  }
  ```

### 2. Frontend

1. Install and configure:

   ```bash
   cd frontend
   cp .env.example .env.local
   ```

   Set `NEXT_PUBLIC_API_URL` in `.env.local` to your backend URL (e.g. `http://localhost:8000`).

2. Run:

   ```bash
   npm install
   npm run dev
   ```

Open [http://localhost:3000](http://localhost:3000).

## Deploy

### Backend (Render)

1. New **Web Service**, connect this repo, root directory **`backend`**.
2. Ensure Render uses **Python 3.11** (this repo includes `backend/runtime.txt`).
3. **Build command:** `pip install -r requirements.txt`
4. **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. **Environment variables:**
   - `GROQ_API_KEY` — required
   - `CORS_ORIGINS` — your Vercel URL(s), e.g. `https://your-project.vercel.app` (comma-separated if multiple)

Render sets `PORT` automatically. The first boot may take longer while `sentence-transformers` downloads the model.

### Frontend (Vercel)

1. New project, root directory **`frontend`**, framework **Next.js**.
2. **Environment variable:** `NEXT_PUBLIC_API_URL` = your Render service URL (no trailing slash required), e.g. `https://practiguide-api.onrender.com`

Redeploy after changing env vars. Ensure `CORS_ORIGINS` on the backend includes your Vercel domain.

## Knowledge base

Add or edit Markdown (`.md`) or plain text (`.txt`) files under `backend/docs`. Restart the backend process so Chroma is rebuilt from disk.

## License

MIT — see [LICENSE](./LICENSE).
