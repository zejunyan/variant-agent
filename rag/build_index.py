import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from rag.document_loader import (
    chunk_documents,
    load_markdown_documents,
)


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def create_search_text(chunk: dict[str, Any]) -> str:
    """Combine chunk context and content for embedding."""

    return (
        f"Title: {chunk['title']}\n"
        f"Section: {chunk['section']}\n"
        f"Content: {chunk['text']}"
    )


def build_index(
    documents_directory: str | Path,
    index_directory: str | Path,
    model_name: str = DEFAULT_MODEL,
    encoder: Any | None = None,
) -> dict[str, Any]:
    """Create and save a local embedding index."""

    documents_directory = Path(documents_directory).resolve()
    index_directory = Path(index_directory).resolve()

    documents = load_markdown_documents(documents_directory)
    chunks = chunk_documents(documents)

    if not documents:
        raise ValueError("No Markdown documents were found")

    if not chunks:
        raise ValueError("No text chunks were generated")

    if encoder is None:
        encoder = SentenceTransformer(model_name)

    search_texts = [
        create_search_text(chunk)
        for chunk in chunks
    ]

    embeddings = encoder.encode(
        search_texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    if embeddings.ndim != 2:
        raise ValueError("Encoder must return a two-dimensional array")

    if embeddings.shape[0] != len(chunks):
        raise ValueError(
            "The number of embeddings does not match "
            "the number of chunks"
        )

    index_directory.mkdir(parents=True, exist_ok=True)

    embeddings_path = index_directory / "embeddings.npy"
    chunks_path = index_directory / "chunks.json"
    manifest_path = index_directory / "manifest.json"

    np.save(embeddings_path, embeddings)

    chunks_path.write_text(
        json.dumps(
            chunks,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    manifest = {
        "model_name": model_name,
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "embedding_dimensions": int(embeddings.shape[1]),
        "normalized": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents_directory": str(documents_directory),
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the local knowledge-base embedding index."
    )

    parser.add_argument(
        "--documents",
        default="knowledge_base/documents",
        help="Directory containing Markdown documents.",
    )

    parser.add_argument(
        "--index",
        default="knowledge_base/index",
        help="Directory where the index will be saved.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Sentence-transformers embedding model.",
    )

    args = parser.parse_args()

    manifest = build_index(
        documents_directory=args.documents,
        index_directory=args.index,
        model_name=args.model,
    )

    print("\nIndex successfully created:")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()