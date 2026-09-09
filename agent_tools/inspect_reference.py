import json
import os
from pathlib import Path

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# GRCh38 chromosome 20 length
EXPECTED_GRCH38_CHR20_LENGTH = 64_444_167


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def inspect_reference_data(
    reference_path: str,
    allowed_root: Path | None = None,
) -> dict:
    """
    Inspect a FASTA reference and its existing index.

    This function is deterministic and does not use an LLM.
    """
    report = {
        "valid": False,
        "reference": reference_path,
        "fai_index": None,
        "sequence_dictionary": None,
        "contig_count": 0,
        "total_length": 0,
        "contigs": [],
        "has_chr20": False,
        "matches_grch38_chr20_test_reference": False,
        "errors": [],
        "warnings": [],
    }

    reference = Path(reference_path).expanduser().resolve()

    if allowed_root is not None:
        allowed_root = allowed_root.resolve()

        if not _is_within(reference, allowed_root):
            report["errors"].append(
                f"Reference is outside the allowed directory: "
                f"{allowed_root}"
            )
            return report

    if not reference.exists():
        report["errors"].append(
            f"Reference does not exist: {reference}"
        )
        return report

    if not reference.is_file():
        report["errors"].append(
            f"Reference is not a file: {reference}"
        )
        return report

    if not os.access(reference, os.R_OK):
        report["errors"].append(
            f"Reference is not readable: {reference}"
        )
        return report

    if reference.suffix not in {".fa", ".fasta", ".fna"}:
        report["warnings"].append(
            "Reference does not use a standard FASTA extension."
        )

    fai_path = Path(f"{reference}.fai")
    report["fai_index"] = str(fai_path)

    dictionary_path = reference.with_suffix(".dict")
    report["sequence_dictionary"] = str(dictionary_path)

    if not fai_path.exists():
        report["errors"].append(
            f"FASTA index does not exist: {fai_path}"
        )
        return report

    if not os.access(fai_path, os.R_OK):
        report["errors"].append(
            f"FASTA index is not readable: {fai_path}"
        )
        return report

    try:
        with reference.open(encoding="utf-8") as handle:
            first_line = handle.readline().strip()
    except OSError as error:
        report["errors"].append(
            f"Could not read reference: {error}"
        )
        return report

    if not first_line.startswith(">"):
        report["errors"].append(
            "Reference does not begin with a FASTA header."
        )
        return report

    fasta_first_contig = first_line[1:].split()[0]

    seen_contigs = set()

    try:
        with fai_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                fields = line.rstrip().split("\t")

                if len(fields) < 5:
                    report["errors"].append(
                        f"Invalid FASTA index row {line_number}."
                    )
                    continue

                contig_name = fields[0]

                try:
                    contig_length = int(fields[1])
                except ValueError:
                    report["errors"].append(
                        f"Invalid contig length on index row "
                        f"{line_number}."
                    )
                    continue

                if contig_length <= 0:
                    report["errors"].append(
                        f"Non-positive contig length on index row "
                        f"{line_number}."
                    )
                    continue

                if contig_name in seen_contigs:
                    report["errors"].append(
                        f"Duplicate contig in FASTA index: "
                        f"{contig_name}"
                    )
                    continue

                seen_contigs.add(contig_name)

                report["contigs"].append({
                    "name": contig_name,
                    "length": contig_length,
                })

    except OSError as error:
        report["errors"].append(
            f"Could not read FASTA index: {error}"
        )
        return report

    if not report["contigs"]:
        report["errors"].append(
            "FASTA index contains no valid contigs."
        )
        return report

    if fasta_first_contig != report["contigs"][0]["name"]:
        report["errors"].append(
            "The first FASTA contig does not match the first "
            "FASTA-index contig."
        )

    report["contig_count"] = len(report["contigs"])
    report["total_length"] = sum(
        contig["length"]
        for contig in report["contigs"]
    )

    contig_lengths = {
        contig["name"]: contig["length"]
        for contig in report["contigs"]
    }

    report["has_chr20"] = "chr20" in contig_lengths

    report["matches_grch38_chr20_test_reference"] = (
        report["contig_count"] == 1
        and contig_lengths.get("chr20")
        == EXPECTED_GRCH38_CHR20_LENGTH
    )

    if not dictionary_path.exists():
        report["warnings"].append(
            "GATK sequence dictionary is not stored beside the "
            "reference. The current Nextflow processes create it "
            "inside their task directories."
        )

    if report["matches_grch38_chr20_test_reference"]:
        report["warnings"].append(
            "The contig name and length match the approved GRCh38 "
            "chr20 test reference, but sequence identity is not "
            "proven without a checksum."
        )

    report["valid"] = len(report["errors"]) == 0

    return report


@tool
def inspect_reference(reference_path: str) -> str:
    """
    Inspect a FASTA reference and report its indexed contigs.

    The tool checks whether the reference and its FASTA index exist,
    reports contig names and lengths, and assesses compatibility with
    the approved GRCh38 chromosome 20 learning reference.

    Args:
        reference_path: Path to the reference FASTA file.

    Returns:
        A JSON report containing reference metadata, compatibility,
        errors, and warnings.
    """
    report = inspect_reference_data(
        reference_path=reference_path,
        allowed_root=PROJECT_ROOT,
    )

    return json.dumps(report, indent=2)