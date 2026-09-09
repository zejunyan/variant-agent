import gzip
import json
import os
import re
from pathlib import Path
from typing import TextIO

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _open_vcf(path: Path) -> TextIO:
    if path.name.endswith(".vcf.gz"):
        return gzip.open(path, "rt", encoding="utf-8")

    return path.open("r", encoding="utf-8")


def _extract_angle_bracket_value(
    line: str,
    key: str,
) -> str | None:
    match = re.search(
        rf'(?:<|,){re.escape(key)}=("[^"]*"|[^,>]+)',
        line,
    )

    if match:
        return match.group(1).strip('"')

    return None


def inspect_vcf_header_data(
    vcf_path: str,
    expected_sample: str = "",
    expected_contig: str = "chr20",
    allowed_root: Path | None = None,
) -> dict:
    """
    Inspect VCF metadata without using an LLM.
    """
    report = {
        "valid": False,
        "vcf": vcf_path,
        "compressed": False,
        "index": None,
        "index_exists": False,
        "fileformat": None,
        "references": [],
        "sources": [],
        "contigs": [],
        "filters": [],
        "samples": [],
        "expected_sample": expected_sample or None,
        "expected_sample_present": None,
        "expected_contig": expected_contig or None,
        "expected_contig_present": None,
        "errors": [],
        "warnings": [],
    }

    path = Path(vcf_path).expanduser().resolve()
    report["vcf"] = str(path)

    if allowed_root is not None:
        allowed_root = allowed_root.resolve()

        if not _is_within(path, allowed_root):
            report["errors"].append(
                f"VCF is outside the allowed directory: "
                f"{allowed_root}"
            )
            return report

    if not path.exists():
        report["errors"].append(
            f"VCF does not exist: {path}"
        )
        return report

    if not path.is_file():
        report["errors"].append(
            f"VCF path is not a file: {path}"
        )
        return report

    if not os.access(path, os.R_OK):
        report["errors"].append(
            f"VCF is not readable: {path}"
        )
        return report

    if path.name.endswith(".vcf.gz"):
        report["compressed"] = True
        possible_indexes = [
            Path(f"{path}.tbi"),
            Path(f"{path}.csi"),
        ]
    elif path.name.endswith(".vcf"):
        possible_indexes = [
            Path(f"{path}.idx"),
        ]
    else:
        report["warnings"].append(
            "File does not use a standard .vcf or .vcf.gz suffix."
        )
        possible_indexes = []

    for index_path in possible_indexes:
        if index_path.exists():
            report["index"] = str(index_path)
            report["index_exists"] = True
            break

    if report["compressed"] and not report["index_exists"]:
        report["warnings"].append(
            "Compressed VCF has no .tbi or .csi index."
        )

    column_header_found = False

    try:
        with _open_vcf(path) as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.rstrip("\n")

                if line.startswith("##fileformat="):
                    report["fileformat"] = line.split(
                        "=",
                        maxsplit=1,
                    )[1]

                elif line.startswith("##reference="):
                    report["references"].append(
                        line.split("=", maxsplit=1)[1]
                    )

                elif line.startswith("##source="):
                    report["sources"].append(
                        line.split("=", maxsplit=1)[1]
                    )

                elif line.startswith("##contig=<"):
                    contig_id = _extract_angle_bracket_value(
                        line,
                        "ID",
                    )

                    contig_length = _extract_angle_bracket_value(
                        line,
                        "length",
                    )

                    if contig_id is None:
                        report["warnings"].append(
                            f"Could not parse contig ID on "
                            f"header line {line_number}."
                        )
                        continue

                    parsed_contig = {
                        "id": contig_id,
                        "length": None,
                    }

                    if contig_length is not None:
                        try:
                            parsed_contig["length"] = int(
                                contig_length
                            )
                        except ValueError:
                            report["warnings"].append(
                                f"Invalid contig length for "
                                f"{contig_id}."
                            )

                    report["contigs"].append(parsed_contig)

                elif line.startswith("##FILTER=<"):
                    filter_id = _extract_angle_bracket_value(
                        line,
                        "ID",
                    )

                    description = _extract_angle_bracket_value(
                        line,
                        "Description",
                    )

                    if filter_id is not None:
                        report["filters"].append({
                            "id": filter_id,
                            "description": description,
                        })

                elif line.startswith("#CHROM"):
                    fields = line.split("\t")

                    if len(fields) < 8:
                        report["errors"].append(
                            "The #CHROM header contains fewer "
                            "than eight required VCF columns."
                        )
                    else:
                        report["samples"] = fields[9:]

                    column_header_found = True
                    break

                elif not line.startswith("#"):
                    report["errors"].append(
                        "Encountered a variant record before "
                        "the #CHROM header."
                    )
                    break

    except (OSError, UnicodeDecodeError, gzip.BadGzipFile) as error:
        report["errors"].append(
            f"Could not read VCF header: {error}"
        )
        return report

    if report["fileformat"] is None:
        report["errors"].append(
            "VCF fileformat declaration is missing."
        )

    if not column_header_found:
        report["errors"].append(
            "VCF #CHROM column header is missing."
        )

    if not report["contigs"]:
        report["warnings"].append(
            "VCF header contains no contig declarations."
        )

    if not report["references"]:
        report["warnings"].append(
            "VCF header contains no reference metadata."
        )

    if not report["sources"]:
        report["warnings"].append(
            "VCF header contains no source metadata."
        )

    if len(report["samples"]) != len(set(report["samples"])):
        report["errors"].append(
            "VCF header contains duplicate sample names."
        )

    if expected_sample:
        report["expected_sample_present"] = (
            expected_sample in report["samples"]
        )

        if not report["expected_sample_present"]:
            report["errors"].append(
                f"Expected sample is absent: {expected_sample}"
            )

    if expected_contig:
        contig_ids = {
            contig["id"]
            for contig in report["contigs"]
        }

        report["expected_contig_present"] = (
            expected_contig in contig_ids
        )

        if not report["expected_contig_present"]:
            report["errors"].append(
                f"Expected contig is absent: {expected_contig}"
            )

    report["valid"] = len(report["errors"]) == 0
    return report


@tool
def inspect_vcf_header(
    vcf_path: str,
    expected_sample: str = "",
    expected_contig: str = "chr20",
) -> str:
    """
    Inspect the metadata header of a VCF file.

    The tool reports the VCF version, references, sources, contigs,
    filters, samples, and index status. It does not modify the VCF
    or interpret clinical significance.

    Args:
        vcf_path: Path to a .vcf or .vcf.gz file.
        expected_sample: Sample name expected in the VCF header.
            Use an empty string when no specific sample is required.
        expected_contig: Contig expected in the VCF header.

    Returns:
        A JSON report containing VCF metadata, validation errors,
        and warnings.
    """
    report = inspect_vcf_header_data(
        vcf_path=vcf_path,
        expected_sample=expected_sample,
        expected_contig=expected_contig,
        allowed_root=PROJECT_ROOT,
    )

    return json.dumps(report, indent=2)
