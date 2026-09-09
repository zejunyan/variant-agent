import csv
import json
import math
import os
from pathlib import Path

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _parse_value(value: str):
    value = value.strip()

    if not value or value.lower() == "nan":
        return None

    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return value


def _find_data_directory(path: Path) -> Path | None:
    """
    Accept either multiqc_report_data or its parent report directory.
    """
    if (
        path.is_dir()
        and (path / "multiqc_general_stats.txt").exists()
    ):
        return path

    nested = path / "multiqc_report_data"

    if nested.is_dir():
        return nested

    return None


def _matches_sample(row_name: str, expected_sample: str) -> bool:
    if not expected_sample:
        return True

    return (
        row_name == expected_sample
        or row_name.startswith(f"{expected_sample}.")
        or row_name.startswith(f"{expected_sample}_")
    )


def summarize_multiqc_data(
    multiqc_path: str,
    expected_sample: str = "",
    allowed_root: Path | None = None,
) -> dict:
    """
    Read structured MultiQC output without using an LLM.
    """
    report = {
        "valid": False,
        "input_path": multiqc_path,
        "data_directory": None,
        "expected_sample": expected_sample or None,
        "matched_rows": [],
        "metrics": {},
        "software_versions": {},
        "errors": [],
        "warnings": [],
    }

    input_path = Path(multiqc_path).expanduser().resolve()
    report["input_path"] = str(input_path)

    if allowed_root is not None:
        allowed_root = allowed_root.resolve()

        if not _is_within(input_path, allowed_root):
            report["errors"].append(
                f"MultiQC path is outside the allowed directory: "
                f"{allowed_root}"
            )
            return report

    if not input_path.exists():
        report["errors"].append(
            f"MultiQC path does not exist: {input_path}"
        )
        return report

    if not input_path.is_dir():
        report["errors"].append(
            f"MultiQC path is not a directory: {input_path}"
        )
        return report

    data_directory = _find_data_directory(input_path)

    if data_directory is None:
        report["errors"].append(
            "Could not find multiqc_report_data or "
            "multiqc_general_stats.txt."
        )
        return report

    report["data_directory"] = str(data_directory)

    general_stats = (
        data_directory / "multiqc_general_stats.txt"
    )

    if not os.access(general_stats, os.R_OK):
        report["errors"].append(
            f"MultiQC general statistics are not readable: "
            f"{general_stats}"
        )
        return report

    try:
        with general_stats.open(
            newline="",
            encoding="utf-8",
        ) as handle:
            reader = csv.DictReader(
                handle,
                delimiter="\t",
            )

            if not reader.fieldnames:
                report["errors"].append(
                    "MultiQC general statistics have no header."
                )
                return report

            if "Sample" not in reader.fieldnames:
                report["errors"].append(
                    "MultiQC general statistics are missing "
                    "the Sample column."
                )
                return report

            for row in reader:
                row_name = (row.get("Sample") or "").strip()

                if not row_name:
                    continue

                if not _matches_sample(
                    row_name,
                    expected_sample,
                ):
                    continue

                parsed_metrics = {
                    key: _parse_value(value or "")
                    for key, value in row.items()
                    if key != "Sample"
                    and _parse_value(value or "") is not None
                }

                report["matched_rows"].append(row_name)
                report["metrics"][row_name] = parsed_metrics

    except (OSError, csv.Error) as error:
        report["errors"].append(
            f"Could not read MultiQC statistics: {error}"
        )
        return report

    if not report["matched_rows"]:
        if expected_sample:
            report["errors"].append(
                f"No MultiQC rows matched sample: "
                f"{expected_sample}"
            )
        else:
            report["errors"].append(
                "MultiQC general statistics contain no sample rows."
            )

        return report

    versions_path = (
        data_directory / "multiqc_software_versions.txt"
    )

    if versions_path.exists():
        try:
            with versions_path.open(
                newline="",
                encoding="utf-8",
            ) as handle:
                reader = csv.DictReader(
                    handle,
                    delimiter="\t",
                )

                for row in reader:
                    row_name = (row.get("Sample") or "").strip()

                    if not row_name:
                        continue

                    versions = {
                        key: value.strip()
                        for key, value in row.items()
                        if key != "Sample"
                        and value
                        and value.strip()
                    }

                    if versions:
                        report["software_versions"][
                            row_name
                        ] = versions

        except (OSError, csv.Error) as error:
            report["warnings"].append(
                f"Could not read software versions: {error}"
            )
    else:
        report["warnings"].append(
            "MultiQC software-version table is missing."
        )

    report["valid"] = len(report["errors"]) == 0
    return report


@tool
def summarize_multiqc(
    multiqc_path: str,
    expected_sample: str = "",
) -> str:
    """
    Summarize structured metrics from a MultiQC report directory.

    The tool reads MultiQC general statistics and software versions.
    It reports existing evidence but does not diagnose disease,
    reinterpret sequencing data, or modify report files.

    Args:
        multiqc_path: Path to a MultiQC report directory or its
            multiqc_report_data directory.
        expected_sample: Base sample name whose related MultiQC rows
            should be returned. Use an empty string for all samples.

    Returns:
        A JSON report containing matched samples, available metrics,
        software versions, errors, and warnings.
    """
    report = summarize_multiqc_data(
        multiqc_path=multiqc_path,
        expected_sample=expected_sample,
        allowed_root=PROJECT_ROOT,
    )

    return json.dumps(report, indent=2)