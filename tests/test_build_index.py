import json

import numpy as np
import pytest

from rag.build_index import build_index, create_search_text


class FakeEncoder:
    """Deterministic encoder used only for testing."""

    def encode(
        self,
        texts,
        convert_to_numpy,
        normalize_embeddings,
        show_progress_bar,
    ):
        assert convert_to_numpy is True
        assert normalize_embeddings is True

        return np.array(
            [
                [
                    float(len(text)),
                    float(len(text.split())),
                    float(index + 1),
                ]
                for index, text in enumerate(texts)
            ],
            dtype=np.float32,
        )


def create_test_document(path):
    path.write_text(
        """---
document_id: reference-guide
title: Reference guide
reference_build: GRCh38
---

# Reference guide

## Required files

The reference requires a FASTA index and sequence dictionary.

## Compatibility

The BAM and VCF contigs must match the reference.
""",
        encoding="utf-8",
    )


def test_create_search_text_contains_context():
    chunk = {
        "title": "Reference guide",
        "section": "Required files",
        "text": "A FASTA index is required.",
    }

    result = create_search_text(chunk)

    assert "Title: Reference guide" in result
    assert "Section: Required files" in result
    assert "A FASTA index is required" in result


def test_build_index_creates_expected_files(tmp_path):
    documents_directory = tmp_path / "documents"
    index_directory = tmp_path / "index"
    documents_directory.mkdir()

    create_test_document(
        documents_directory / "reference.md"
    )

    manifest = build_index(
        documents_directory=documents_directory,
        index_directory=index_directory,
        model_name="fake-test-model",
        encoder=FakeEncoder(),
    )

    assert (index_directory / "embeddings.npy").exists()
    assert (index_directory / "chunks.json").exists()
    assert (index_directory / "manifest.json").exists()

    embeddings = np.load(index_directory / "embeddings.npy")

    assert embeddings.ndim == 2
    assert embeddings.shape == (2, 3)

    chunks = json.loads(
        (index_directory / "chunks.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(chunks) == 2
    assert chunks[0]["source"] == "reference.md"
    assert chunks[0]["section"] == "Required files"
    assert chunks[1]["section"] == "Compatibility"

    assert manifest["document_count"] == 1
    assert manifest["chunk_count"] == 2
    assert manifest["embedding_dimensions"] == 3
    assert manifest["model_name"] == "fake-test-model"


def test_build_index_rejects_empty_directory(tmp_path):
    documents_directory = tmp_path / "documents"
    documents_directory.mkdir()

    with pytest.raises(
        ValueError,
        match="No Markdown documents",
    ):
        build_index(
            documents_directory=documents_directory,
            index_directory=tmp_path / "index",
            encoder=FakeEncoder(),
        )