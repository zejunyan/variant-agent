from agent_tools.search_knowledge_base import (
    search_knowledge_base_data,
)


class FakeRetriever:
    def __init__(self, results=None, error=None):
        self.results = results or []
        self.error = error
        self.received_query = None
        self.received_top_k = None
        self.received_minimum_score = None

    def search(
        self,
        query,
        top_k,
        minimum_score,
    ):
        if self.error is not None:
            raise self.error

        self.received_query = query
        self.received_top_k = top_k
        self.received_minimum_score = minimum_score

        return {
            "query": query,
            "result_count": len(self.results),
            "model_name": "fake-model",
            "results": self.results,
        }


def example_result():
    return {
        "rank": 1,
        "score": 0.91,
        "chunk_id": "input-requirements:0003",
        "document_id": "input-requirements",
        "title": "Pipeline input requirements",
        "section": "Reference files",
        "source": "input_requirements.md",
        "text": (
            "The reference requires a FASTA index and "
            "sequence dictionary."
        ),
        "metadata": {
            "reference_build": "GRCh38",
        },
    }


def test_search_returns_structured_evidence():
    retriever = FakeRetriever(
        results=[example_result()]
    )

    report = search_knowledge_base_data(
        query="Which reference files are required?",
        top_k=3,
        retriever=retriever,
    )

    assert report["valid"] is True
    assert report["result_count"] == 1
    assert report["errors"] == []

    result = report["results"][0]

    assert result["source"] == "input_requirements.md"
    assert result["section"] == "Reference files"
    assert result["score"] == 0.91

    assert retriever.received_query == (
        "Which reference files are required?"
    )
    assert retriever.received_top_k == 3
    assert retriever.received_minimum_score == 0.20


def test_empty_query_is_rejected():
    report = search_knowledge_base_data(
        query="   ",
        retriever=FakeRetriever(),
    )

    assert report["valid"] is False
    assert report["result_count"] == 0
    assert "cannot be empty" in report["errors"][0]


def test_top_k_below_range_is_rejected():
    report = search_knowledge_base_data(
        query="reference",
        top_k=0,
        retriever=FakeRetriever(),
    )

    assert report["valid"] is False
    assert "between 1 and 5" in report["errors"][0]


def test_top_k_above_range_is_rejected():
    report = search_knowledge_base_data(
        query="reference",
        top_k=6,
        retriever=FakeRetriever(),
    )

    assert report["valid"] is False
    assert "between 1 and 5" in report["errors"][0]


def test_no_results_produces_warning():
    report = search_knowledge_base_data(
        query="What is the clinical diagnosis?",
        retriever=FakeRetriever(results=[]),
    )

    assert report["valid"] is True
    assert report["result_count"] == 0
    assert report["warnings"]
    assert "Do not invent" in report["warnings"][0]


def test_retriever_error_is_reported():
    retriever = FakeRetriever(
        error=ValueError("Invalid embedding dimensions")
    )

    report = search_knowledge_base_data(
        query="reference requirements",
        retriever=retriever,
    )

    assert report["valid"] is False
    assert report["result_count"] == 0
    assert "search failed" in report["errors"][0]
    assert "Invalid embedding dimensions" in report["errors"][0]