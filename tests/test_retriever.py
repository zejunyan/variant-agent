import json

import numpy as np
import pytest

from rag.retriever import KnowledgeBaseRetriever


class FakeQueryEncoder:
    def encode(
        self,
        texts,
        convert_to_numpy,
        normalize_embeddings,
        show_progress_bar,
    ):
        query = texts[0].lower()

        if "reference" in query:
            vector = [1.0, 0.0]
        elif "fastq" in query:
            vector = [0.0, 1.0]
        else:
            vector = [0.7071068, 0.7071068]

        return np.array([vector], dtype=np.float32)


def create_test_index(index_directory):
    index_directory.mkdir()

    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype=np.float32,
    )

    chunks = [
        {
            "chunk_id": "reference:0001",
            "document_id": "reference",
            "title": "Reference requirements",
            "section": "Required files",
            "source": "reference.md",
            "text": "The pipeline uses a GRCh38 reference.",
            "metadata": {
                "reference_build": "GRCh38",
            },
        },
        {
            "chunk_id": "inputs:0001",
            "document_id": "inputs",
            "title": "Input requirements",
            "section": "FASTQ files",
            "source": "inputs.md",
            "text": "Paired R1 and R2 FASTQ files are required.",
            "metadata": {},
        },
    ]

    manifest = {
        "model_name": "fake-model",
        "document_count": 2,
        "chunk_count": 2,
        "embedding_dimensions": 2,
        "normalized": True,
    }

    np.save(
        index_directory / "embeddings.npy",
        embeddings,
    )

    (index_directory / "chunks.json").write_text(
        json.dumps(chunks),
        encoding="utf-8",
    )

    (index_directory / "manifest.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )


def test_reference_query_returns_reference_first(tmp_path):
    index_directory = tmp_path / "index"
    create_test_index(index_directory)

    retriever = KnowledgeBaseRetriever(
        index_directory=index_directory,
        encoder=FakeQueryEncoder(),
    )

    report = retriever.search(
        "Which reference does the pipeline use?",
        top_k=2,
    )

    assert report["result_count"] == 2
    assert report["results"][0]["chunk_id"] == "reference:0001"
    assert report["results"][0]["score"] == pytest.approx(1.0)


def test_fastq_query_returns_fastq_first(tmp_path):
    index_directory = tmp_path / "index"
    create_test_index(index_directory)

    retriever = KnowledgeBaseRetriever(
        index_directory=index_directory,
        encoder=FakeQueryEncoder(),
    )

    report = retriever.search(
        "Which FASTQ files are required?",
        top_k=1,
    )

    assert report["result_count"] == 1
    assert report["results"][0]["chunk_id"] == "inputs:0001"


def test_minimum_score_can_remove_results(tmp_path):
    index_directory = tmp_path / "index"
    create_test_index(index_directory)

    retriever = KnowledgeBaseRetriever(
        index_directory=index_directory,
        encoder=FakeQueryEncoder(),
    )

    report = retriever.search(
        "reference",
        top_k=2,
        minimum_score=0.5,
    )

    assert report["result_count"] == 1
    assert report["results"][0]["source"] == "reference.md"


def test_empty_query_is_rejected(tmp_path):
    index_directory = tmp_path / "index"
    create_test_index(index_directory)

    retriever = KnowledgeBaseRetriever(
        index_directory=index_directory,
        encoder=FakeQueryEncoder(),
    )

    with pytest.raises(ValueError, match="Query cannot be empty"):
        retriever.search("   ")


def test_invalid_top_k_is_rejected(tmp_path):
    index_directory = tmp_path / "index"
    create_test_index(index_directory)

    retriever = KnowledgeBaseRetriever(
        index_directory=index_directory,
        encoder=FakeQueryEncoder(),
    )

    with pytest.raises(
        ValueError,
        match="top_k must be greater than zero",
    ):
        retriever.search("reference", top_k=0)


def test_missing_index_is_rejected(tmp_path):
    with pytest.raises(
        FileNotFoundError,
        match="index is incomplete",
    ):
        KnowledgeBaseRetriever(
            index_directory=tmp_path / "missing",
            encoder=FakeQueryEncoder(),
        )