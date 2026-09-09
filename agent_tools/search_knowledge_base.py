import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from smolagents import tool

from rag.retriever import KnowledgeBaseRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INDEX_DIRECTORY = PROJECT_ROOT / "knowledge_base" / "index"

DEFAULT_MINIMUM_SCORE = 0.20
MAX_RESULTS = 5


@lru_cache(maxsize=1)
def get_retriever() -> KnowledgeBaseRetriever:
    """Load and cache the project knowledge-base retriever."""

    return KnowledgeBaseRetriever(
        index_directory=INDEX_DIRECTORY,
    )


def search_knowledge_base_data(
    query: str,
    top_k: int = 3,
    retriever: Any | None = None,
) -> dict[str, Any]:
    """
    Search the local knowledge base without using an LLM.

    A retriever can be injected during testing to avoid loading
    the real embedding model.
    """

    query = query.strip()

    if not query:
        return {
            "valid": False,
            "query": query,
            "result_count": 0,
            "results": [],
            "errors": ["Search query cannot be empty."],
            "warnings": [],
        }

    if top_k < 1 or top_k > MAX_RESULTS:
        return {
            "valid": False,
            "query": query,
            "result_count": 0,
            "results": [],
            "errors": [
                f"top_k must be between 1 and {MAX_RESULTS}."
            ],
            "warnings": [],
        }

    if retriever is None:
        try:
            retriever = get_retriever()
        except (FileNotFoundError, ValueError, OSError) as error:
            return {
                "valid": False,
                "query": query,
                "result_count": 0,
                "results": [],
                "errors": [
                    f"Could not load knowledge-base index: {error}"
                ],
                "warnings": [],
            }

    try:
        search_result = retriever.search(
            query=query,
            top_k=top_k,
            minimum_score=DEFAULT_MINIMUM_SCORE,
        )
    except (ValueError, OSError) as error:
        return {
            "valid": False,
            "query": query,
            "result_count": 0,
            "results": [],
            "errors": [
                f"Knowledge-base search failed: {error}"
            ],
            "warnings": [],
        }

    results = search_result["results"]
    warnings: list[str] = []

    if not results:
        warnings.append(
            "No sufficiently relevant knowledge-base evidence "
            "was found. Do not invent an answer."
        )

    return {
        "valid": True,
        "query": query,
        "result_count": len(results),
        "model_name": search_result.get("model_name"),
        "results": results,
        "errors": [],
        "warnings": warnings,
    }


@tool
def search_knowledge_base(
    query: str,
    top_k: int = 3,
) -> str:
    """
    Search the local variant-calling project knowledge base.

    Use this tool for questions about the pipeline stages, input
    requirements, reference requirements, QC interpretation, and
    documented troubleshooting procedures. Base the answer only on
    returned evidence and identify the source document. If no result
    is returned, state that the knowledge base does not contain enough
    information.

    Args:
        query: A focused question or search phrase.
        top_k: Number of evidence chunks to return. Allowed values
            are integers from 1 to 5.

    Returns:
        A JSON report containing ranked evidence chunks, similarity
        scores, source filenames, section names, errors, and warnings.
    """

    report = search_knowledge_base_data(
        query=query,
        top_k=top_k,
    )

    return json.dumps(report, indent=2)