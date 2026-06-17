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
