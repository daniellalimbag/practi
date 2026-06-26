# practi 🎓

RAG chatbot for **practicum and internship** students. The stack is a **Next.js** frontend (Vercel) and a **FastAPI** backend (Render) that answers from a local knowledge base under `backend/docs`.

## Architecture

| Piece | Technology |
| ----- | ---------- |
| Frontend | Next.js, Tailwind CSS |
| Backend | FastAPI, LangChain, Groq or Ollama, ChromaDB |

## Local development

**Backend:**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

- **Local LLM:** install Ollama, pull a model, select **Local** in the sidebar. No `.env` needed.
- **Cloud LLM:** set `GROQ_API_KEY` in `backend/.env`, select **Cloud** in the sidebar.
- **Docs:** add files to `backend/docs/`, then run `python ingest.py` once.

See [backend/README.md](backend/README.md) for setup, ingest, and deploy details.

## Deploy

- **Backend (Render):** root `backend`, env `GROQ_API_KEY` + `CORS_ORIGINS`
- **Frontend (Vercel):** root `frontend`, env `NEXT_PUBLIC_API_URL`

## License

MIT — see [LICENSE](./LICENSE).
