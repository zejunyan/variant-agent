import pytest

from rag.document_loader import (
    chunk_documents,
    load_markdown_documents,
    parse_front_matter,
    split_text_by_words,
)


def test_parse_front_matter():
    text = """---
document_id: test-document
title: Test document
status: reviewed
---

# Introduction

This is a test document.
"""

    metadata, body = parse_front_matter(text)

    assert metadata["document_id"] == "test-document"
    assert metadata["title"] == "Test document"
    assert metadata["status"] == "reviewed"
    assert "# Introduction" in body


def test_load_markdown_documents(tmp_path):
    document_path = tmp_path / "example.md"

    document_path.write_text(
        """---
document_id: example
title: Example document
---

# Example

Example content.
""",
        encoding="utf-8",
    )

    documents = load_markdown_documents(tmp_path)

    assert len(documents) == 1
    assert documents[0]["document_id"] == "example"
    assert documents[0]["title"] == "Example document"
    assert documents[0]["source"] == "example.md"
    assert "Example content" in documents[0]["text"]


def test_empty_markdown_document_is_ignored(tmp_path):
    document_path = tmp_path / "empty.md"
    document_path.write_text("", encoding="utf-8")

    documents = load_markdown_documents(tmp_path)

    assert documents == []


def test_missing_directory_raises_error(tmp_path):
    missing_directory = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        load_markdown_documents(missing_directory)


def test_split_text_creates_overlap():
    text = "one two three four five six seven eight"

    chunks = split_text_by_words(
        text,
        max_words=5,
        overlap_words=2,
    )

    assert chunks == [
        "one two three four five",
        "four five six seven eight",
    ]


def test_invalid_overlap_is_rejected():
    with pytest.raises(ValueError):
        split_text_by_words(
            "example text",
            max_words=10,
            overlap_words=10,
        )


def test_chunk_documents_preserves_source_information():
    documents = [
        {
            "document_id": "pipeline",
            "title": "Pipeline",
            "source": "pipeline.md",
            "path": "/example/pipeline.md",
            "text": (
                "# Inputs\n\n"
                "The pipeline requires paired FASTQ files.\n\n"
                "## Reference\n\n"
                "The reference build is GRCh38."
            ),
            "metadata": {
                "reference_build": "GRCh38",
            },
        }
    ]

    chunks = chunk_documents(
        documents,
        max_words=20,
        overlap_words=2,
    )

    assert len(chunks) == 2

    assert chunks[0]["chunk_id"] == "pipeline:0001"
    assert chunks[0]["section"] == "Inputs"
    assert chunks[0]["source"] == "pipeline.md"

    assert chunks[1]["chunk_id"] == "pipeline:0002"
    assert chunks[1]["section"] == "Reference"
    assert chunks[1]["metadata"]["reference_build"] == "GRCh38"