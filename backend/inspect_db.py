"""
Inspect the persisted Chroma index without loading embedding models.

Usage:
  python inspect_db.py stats
  python inspect_db.py sample [--limit 5]
  python inspect_db.py search MOA
  python inspect_db.py file A_20260617.pdf
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

COLLECTION_NAME = "practi_kb"


def get_collection():
    if not settings.CHROMA_DB_DIR.exists():
        raise SystemExit(
            f"No index found at {settings.CHROMA_DB_DIR}. Run: python ingest.py"
        )

    client = chromadb.PersistentClient(
        path=str(settings.CHROMA_DB_DIR),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    return client.get_collection(COLLECTION_NAME)


def cmd_stats(col) -> None:
    data = col.get(include=["metadatas"])
    metas = data.get("metadatas") or []
    by_file = Counter(
        Path(str(m.get("source", "unknown"))).name for m in metas
    )
    by_date = Counter(m.get("doc_date", "unknown") for m in metas)
    by_type = Counter(m.get("doc_type_label", "unknown") for m in metas)

    print(f"Index path:   {settings.CHROMA_DB_DIR}")
    print(f"Collection:   {COLLECTION_NAME}")
    print(f"Total chunks: {col.count()}")
    print(f"Source files: {len(by_file)}")
    print()
    print("Chunks per file:")
    for name, count in by_file.most_common():
        print(f"  {count:4d}  {name}")
    print()
    print("Chunks by date:")
    for date, count in sorted(by_date.items()):
        print(f"  {count:4d}  {date}")
    print()
    print("Chunks by type:")
    for label, count in by_type.most_common():
        print(f"  {count:4d}  {label}")


def cmd_sample(col, limit: int) -> None:
    data = col.get(limit=limit, include=["documents", "metadatas"])
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    for i, (text, meta) in enumerate(zip(docs, metas), start=1):
        source = Path(str(meta.get("source", "unknown"))).name
        print(f"--- chunk {i} ---")
        print(f"file: {source}")
        print(f"date: {meta.get('doc_date')} | type: {meta.get('doc_type_label')}")
        preview = (text or "").strip().replace("\n", " ")
        print(f"text: {preview[:500]}{'…' if len(preview) > 500 else ''}")
        print()


def cmd_search(col, needle: str, limit: int) -> None:
    data = col.get(include=["documents", "metadatas"])
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []
    needle_lower = needle.lower()

    hits: list[tuple[dict, str]] = []
    for meta, text in zip(metas, docs):
        if needle_lower in (text or "").lower():
            hits.append((meta, text or ""))

    print(f'Found {len(hits)} chunk(s) containing "{needle}"')
    for meta, text in hits[:limit]:
        source = Path(str(meta.get("source", "unknown"))).name
        preview = text.strip().replace("\n", " ")
        print(f"- {source} | date={meta.get('doc_date')}")
        print(f"  {preview[:300]}{'…' if len(preview) > 300 else ''}")
        print()


def cmd_file(col, filename: str, limit: int) -> None:
    data = col.get(include=["documents", "metadatas"])
    docs = data.get("documents") or []
    metas = data.get("metadatas") or []

    hits: list[tuple[dict, str]] = []
    for meta, text in zip(metas, docs):
        source = Path(str(meta.get("source", "unknown"))).name
        if source == filename or filename in source:
            hits.append((meta, text or ""))

    print(f'Found {len(hits)} chunk(s) from "{filename}"')
    for i, (meta, text) in enumerate(hits[:limit], start=1):
        preview = text.strip().replace("\n", " ")
        print(f"--- chunk {i} ---")
        print(f"date: {meta.get('doc_date')} | type: {meta.get('doc_type_label')}")
        print(f"{preview[:700]}{'…' if len(preview) > 700 else ''}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Practi Chroma index")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("stats", help="Show chunk counts by file/date/type")

    sample_p = sub.add_parser("sample", help="Show sample chunks")
    sample_p.add_argument("--limit", type=int, default=5)

    search_p = sub.add_parser("search", help="Keyword search in stored text")
    search_p.add_argument("needle")
    search_p.add_argument("--limit", type=int, default=10)

    file_p = sub.add_parser("file", help="Show chunks from one source file")
    file_p.add_argument("filename")
    file_p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    col = get_collection()

    if args.command == "stats":
        cmd_stats(col)
    elif args.command == "sample":
        cmd_sample(col, args.limit)
    elif args.command == "search":
        cmd_search(col, args.needle, args.limit)
    elif args.command == "file":
        cmd_file(col, args.filename, args.limit)


if __name__ == "__main__":
    main()
