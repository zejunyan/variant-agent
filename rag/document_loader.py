from pathlib import Path
from typing import Any


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Separate simple YAML-style metadata from Markdown content."""

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) != 3:
        return {}, text

    metadata_text = parts[1]
    body = parts[2].lstrip()

    metadata: dict[str, str] = {}

    for line in metadata_text.splitlines():
        line = line.strip()

        if not line or ":" not in line:
            continue

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")

    return metadata, body


def load_markdown_documents(
    documents_directory: str | Path,
) -> list[dict[str, Any]]:
    """Load all Markdown documents from one directory."""

    directory = Path(documents_directory).resolve()

    if not directory.exists():
        raise FileNotFoundError(
            f"Knowledge-base directory does not exist: {directory}"
        )

    if not directory.is_dir():
        raise ValueError(
            f"Knowledge-base path is not a directory: {directory}"
        )

    documents: list[dict[str, Any]] = []

    for path in sorted(directory.glob("*.md")):
        raw_text = path.read_text(encoding="utf-8")
        metadata, body = parse_front_matter(raw_text)

        if not body.strip():
            continue

        document_id = metadata.get("document_id", path.stem)
        title = metadata.get("title", path.stem.replace("_", " ").title())

        documents.append(
            {
                "document_id": document_id,
                "title": title,
                "source": path.name,
                "path": str(path),
                "text": body.strip(),
                "metadata": metadata,
            }
        )

    return documents


def split_markdown_sections(
    text: str,
    default_section: str,
) -> list[dict[str, str]]:
    """Split Markdown while preserving its heading hierarchy."""

    sections: list[dict[str, str]] = []
    heading_hierarchy: dict[int, str] = {}
    current_heading = default_section
    current_lines: list[str] = []

    def save_current_section() -> None:
        content = "\n".join(current_lines).strip()

        if content:
            sections.append(
                {
                    "section": current_heading,
                    "text": content,
                }
            )

    def format_heading() -> str:
        levels = sorted(heading_hierarchy)

        # Exclude the document's H1 title when lower headings exist.
        if len(levels) > 1 and 1 in levels:
            levels.remove(1)

        if not levels:
            return default_section

        return " > ".join(
            heading_hierarchy[level]
            for level in levels
        )

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("#"):
            save_current_section()

            heading_level = len(stripped) - len(
                stripped.lstrip("#")
            )
            heading_text = stripped.lstrip("#").strip()

            # Remove headings that belonged to a previous branch.
            for level in list(heading_hierarchy):
                if level >= heading_level:
                    del heading_hierarchy[level]

            heading_hierarchy[heading_level] = heading_text
            current_heading = format_heading()
            current_lines = []
        else:
            current_lines.append(line)

    save_current_section()

    return sections

def split_text_by_words(
    text: str,
    max_words: int = 180,
    overlap_words: int = 30,
) -> list[str]:
    """Split text into overlapping word-based chunks."""

    if max_words <= 0:
        raise ValueError("max_words must be greater than zero")

    if overlap_words < 0:
        raise ValueError("overlap_words cannot be negative")

    if overlap_words >= max_words:
        raise ValueError("overlap_words must be smaller than max_words")

    words = text.split()

    if not words:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        start = end - overlap_words

    return chunks


def chunk_documents(
    documents: list[dict[str, Any]],
    max_words: int = 180,
    overlap_words: int = 30,
) -> list[dict[str, Any]]:
    """Convert loaded documents into searchable chunks."""

    chunks: list[dict[str, Any]] = []

    for document in documents:
        sections = split_markdown_sections(
            text=document["text"],
            default_section=document["title"],
        )

        chunk_number = 1

        for section in sections:
            section_chunks = split_text_by_words(
                text=section["text"],
                max_words=max_words,
                overlap_words=overlap_words,
            )

            for chunk_text in section_chunks:
                chunks.append(
                    {
                        "chunk_id": (
                            f"{document['document_id']}:{chunk_number:04d}"
                        ),
                        "document_id": document["document_id"],
                        "title": document["title"],
                        "section": section["section"],
                        "source": document["source"],
                        "text": chunk_text,
                        "metadata": document["metadata"],
                    }
                )

                chunk_number += 1

    return chunks