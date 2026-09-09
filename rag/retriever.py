import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


class KnowledgeBaseRetriever:
    """Search a local embedding-based knowledge base."""

    def __init__(
        self,
        index_directory: str | Path,
        encoder: Any | None = None,
    ) -> None:
        self.index_directory = Path(index_directory).resolve()

        self.embeddings_path = (
            self.index_directory / "embeddings.npy"
        )
        self.chunks_path = self.index_directory / "chunks.json"
        self.manifest_path = self.index_directory / "manifest.json"

        self._validate_index_files()

        self.embeddings = np.load(self.embeddings_path)

        self.chunks = json.loads(
            self.chunks_path.read_text(encoding="utf-8")
        )

        self.manifest = json.loads(
            self.manifest_path.read_text(encoding="utf-8")
        )

        self._validate_index_contents()

        if encoder is None:
            model_name = self.manifest["model_name"]
            encoder = SentenceTransformer(model_name)

        self.encoder = encoder

    def _validate_index_files(self) -> None:
        required_files = [
            self.embeddings_path,
            self.chunks_path,
            self.manifest_path,
        ]

        missing_files = [
            str(path)
            for path in required_files
            if not path.is_file()
        ]

        if missing_files:
            raise FileNotFoundError(
                "Knowledge-base index is incomplete. "
                f"Missing files: {missing_files}"
            )

    def _validate_index_contents(self) -> None:
        if self.embeddings.ndim != 2:
            raise ValueError(
                "Stored embeddings must be a two-dimensional array"
            )

        if len(self.chunks) != self.embeddings.shape[0]:
            raise ValueError(
                "The number of stored chunks does not match "
                "the number of embeddings"
            )

        if self.manifest.get("chunk_count") != len(self.chunks):
            raise ValueError(
                "Manifest chunk count does not match the index"
            )

        if not self.manifest.get("normalized"):
            raise ValueError(
                "The retriever requires normalized embeddings"
            )

    def search(
        self,
        query: str,
        top_k: int = 3,
        minimum_score: float | None = None,
    ) -> dict[str, Any]:
        """Return the chunks most similar to the query."""

        query = query.strip()

        if not query:
            raise ValueError("Query cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        query_embedding = self.encoder.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        query_embedding = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        if query_embedding.ndim != 2:
            raise ValueError(
                "Query encoder must return a two-dimensional array"
            )

        if query_embedding.shape[0] != 1:
            raise ValueError(
                "Query encoder must return exactly one embedding"
            )

        if query_embedding.shape[1] != self.embeddings.shape[1]:
            raise ValueError(
                "Query embedding dimension does not match "
                "the stored index"
            )

        # The vectors are normalized, so their dot product is
        # cosine similarity.
        scores = self.embeddings @ query_embedding[0]

        ranked_indices = np.argsort(scores)[::-1]

        results: list[dict[str, Any]] = []

        for index in ranked_indices:
            score = float(scores[index])

            if minimum_score is not None and score < minimum_score:
                continue

            chunk = self.chunks[int(index)]

            results.append(
                {
                    "rank": len(results) + 1,
                    "score": round(score, 6),
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "title": chunk["title"],
                    "section": chunk["section"],
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "metadata": chunk.get("metadata", {}),
                }
            )

            if len(results) == min(top_k, len(self.chunks)):
                break

        return {
            "query": query,
            "result_count": len(results),
            "model_name": self.manifest["model_name"],
            "results": results,
        }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search the local project knowledge base."
    )

    parser.add_argument(
        "query",
        help="Question or search query.",
    )

    parser.add_argument(
        "--index",
        default="knowledge_base/index",
        help="Knowledge-base index directory.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Maximum number of results.",
    )

    parser.add_argument(
        "--minimum-score",
        type=float,
        default=None,
        help="Optional minimum cosine-similarity score.",
    )

    args = parser.parse_args()

    retriever = KnowledgeBaseRetriever(args.index)

    result = retriever.search(
        query=args.query,
        top_k=args.top_k,
        minimum_score=args.minimum_score,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()