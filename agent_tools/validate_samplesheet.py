import csv
import json
import os
import re
from pathlib import Path

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = {"sample_id", "read1", "read2"}
VALID_FASTQ_SUFFIXES = (".fastq.gz", ".fq.gz")
VALID_SAMPLE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


def _is_within(path: Path, allowed_root: Path) -> bool:
    """Return True when path is inside allowed_root."""
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _resolve_input_path(value: str, samplesheet_dir: Path) -> Path:
    """Resolve absolute paths or paths relative to the samplesheet."""
    path = Path(value).expanduser()

    if not path.is_absolute():
        path = samplesheet_dir / path

    return path.resolve()


def _looks_like_gzip(path: Path) -> bool:
    """Check the two-byte gzip signature without reading the full file."""
    try:
        with path.open("rb") as handle:
            return handle.read(2) == b"\x1f\x8b"
    except OSError:
        return False


def validate_samplesheet_data(
    samplesheet_path: str,
    allowed_root: Path | None = None,
) -> dict:
    """
    Deterministically validate a paired-end FASTQ samplesheet.

    This core function does not use an LLM.
    """
    report = {
        "valid": False,
        "samplesheet": samplesheet_path,
        "sample_count": 0,
        "samples": [],
        "errors": [],
        "warnings": [],
    }

    path = Path(samplesheet_path).expanduser().resolve()

    if allowed_root is not None:
        allowed_root = allowed_root.resolve()

        if not _is_within(path, allowed_root):
            report["errors"].append(
                f"Samplesheet is outside the allowed directory: "
                f"{allowed_root}"
            )
            return report

    if not path.exists():
        report["errors"].append(
            f"Samplesheet does not exist: {path}"
        )
        return report

    if not path.is_file():
        report["errors"].append(
            f"Samplesheet path is not a file: {path}"
        )
        return report

    if not os.access(path, os.R_OK):
        report["errors"].append(
            f"Samplesheet is not readable: {path}"
        )
        return report

    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)

            if reader.fieldnames is None:
                report["errors"].append(
                    "Samplesheet has no header."
                )
                return report

            fieldnames = {
                field.strip()
                for field in reader.fieldnames
                if field is not None
            }

            missing_columns = REQUIRED_COLUMNS - fieldnames

            if missing_columns:
                report["errors"].append(
                    "Missing required columns: "
                    + ", ".join(sorted(missing_columns))
                )
                return report

            rows = list(reader)

    except (OSError, csv.Error) as error:
        report["errors"].append(
            f"Could not read samplesheet: {error}"
        )
        return report

    if not rows:
        report["errors"].append(
            "Samplesheet contains no sample rows."
        )
        return report

    seen_sample_ids = set()

    for row_number, row in enumerate(rows, start=2):
        sample_id = (row.get("sample_id") or "").strip()
        read1_value = (row.get("read1") or "").strip()
        read2_value = (row.get("read2") or "").strip()

        row_errors = []

        if not sample_id:
            row_errors.append("sample_id is empty")
        elif not VALID_SAMPLE_ID.fullmatch(sample_id):
            row_errors.append(
                "sample_id contains unsupported characters"
            )
        elif sample_id in seen_sample_ids:
            row_errors.append(
                f"duplicate sample_id: {sample_id}"
            )
        else:
            seen_sample_ids.add(sample_id)

        if not read1_value:
            row_errors.append("read1 is empty")

        if not read2_value:
            row_errors.append("read2 is empty")

        read1 = None
        read2 = None

        if read1_value:
            read1 = _resolve_input_path(
                read1_value,
                path.parent,
            )

        if read2_value:
            read2 = _resolve_input_path(
                read2_value,
                path.parent,
            )

        for label, fastq_path in (
            ("read1", read1),
            ("read2", read2),
        ):
            if fastq_path is None:
                continue

            if allowed_root is not None and not _is_within(
                fastq_path,
                allowed_root,
            ):
                row_errors.append(
                    f"{label} is outside the allowed directory"
                )
                continue

            if not fastq_path.exists():
                row_errors.append(
                    f"{label} does not exist: {fastq_path}"
                )
                continue

            if not fastq_path.is_file():
                row_errors.append(
                    f"{label} is not a file: {fastq_path}"
                )
                continue

            if not os.access(fastq_path, os.R_OK):
                row_errors.append(
                    f"{label} is not readable: {fastq_path}"
                )

            if not str(fastq_path).endswith(
                VALID_FASTQ_SUFFIXES
            ):
                row_errors.append(
                    f"{label} must end in .fastq.gz or .fq.gz"
                )
            elif not _looks_like_gzip(fastq_path):
                row_errors.append(
                    f"{label} is not a valid gzip file"
                )

        if read1 is not None and read2 is not None:
            if read1 == read2:
                row_errors.append(
                    "read1 and read2 point to the same file"
                )

        if row_errors:
            for error in row_errors:
                report["errors"].append(
                    f"Row {row_number}: {error}"
                )
        else:
            report["samples"].append({
                "sample_id": sample_id,
                "read1": str(read1),
                "read2": str(read2),
            })

    report["sample_count"] = len(report["samples"])
    report["valid"] = len(report["errors"]) == 0

    return report


@tool
def validate_samplesheet(samplesheet_path: str) -> str:
    """
    Validate a paired-end sequencing samplesheet.

    The samplesheet and FASTQ files must be located inside the
    variant-agent project. The required columns are sample_id,
    read1, and read2.

    Args:
        samplesheet_path: Path to the CSV samplesheet to validate.

    Returns:
        A JSON report containing validation status, valid samples,
        errors, and warnings.
    """
    report = validate_samplesheet_data(
        samplesheet_path=samplesheet_path,
        allowed_root=PROJECT_ROOT,
    )

    return json.dumps(report, indent=2)