import csv
import json
import re
from pathlib import Path
from typing import Any

from smolagents import tool

from agent_tools.summarize_multiqc import (
    summarize_multiqc_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results" / "agent_runs"

VALID_RUN_NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
VALID_SAMPLE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")

REQUIRED_CONCORDANCE_COLUMNS = {
    "type",
    "TP",
    "FP",
    "FN",
    "RECALL",
    "PRECISION",
}


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _parse_integer(
    value: str,
    field: str,
    row_number: int,
) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid integer in {field} at row {row_number}: "
            f"{value}"
        ) from error


def _parse_float(
    value: str,
    field: str,
    row_number: int,
) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(
            f"Invalid number in {field} at row {row_number}: "
            f"{value}"
        ) from error


def read_concordance_file(
    path: Path,
    allowed_root: Path,
) -> dict[str, Any]:
    """Read one raw or filtered concordance table."""

    path = path.resolve()
    allowed_root = allowed_root.resolve()

    result: dict[str, Any] = {
        "valid": False,
        "source": str(path),
        "rows": [],
        "errors": [],
    }

    if not _is_within(path, allowed_root):
        result["errors"].append(
            "Concordance path is outside the approved run directory."
        )
        return result

    if not path.is_file():
        result["errors"].append(
            f"Concordance file does not exist: {path}"
        )
        return result

    try:
        with path.open(
            newline="",
            encoding="utf-8",
        ) as handle:
            reader = csv.DictReader(
                handle,
                delimiter="\t",
            )

            if reader.fieldnames is None:
                result["errors"].append(
                    "Concordance file has no header."
                )
                return result

            missing_columns = (
                REQUIRED_CONCORDANCE_COLUMNS
                - set(reader.fieldnames)
            )

            if missing_columns:
                result["errors"].append(
                    "Concordance file is missing required columns: "
                    f"{sorted(missing_columns)}"
                )
                return result

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                variant_type = (
                    row.get("type") or ""
                ).strip()

                if not variant_type:
                    result["errors"].append(
                        f"Missing variant type at row {row_number}."
                    )
                    continue

                try:
                    parsed_row = {
                        "type": variant_type,
                        "true_positives": _parse_integer(
                            row["TP"],
                            "TP",
                            row_number,
                        ),
                        "false_positives": _parse_integer(
                            row["FP"],
                            "FP",
                            row_number,
                        ),
                        "false_negatives": _parse_integer(
                            row["FN"],
                            "FN",
                            row_number,
                        ),
                        "recall": _parse_float(
                            row["RECALL"],
                            "RECALL",
                            row_number,
                        ),
                        "precision": _parse_float(
                            row["PRECISION"],
                            "PRECISION",
                            row_number,
                        ),
                    }

                except ValueError as error:
                    result["errors"].append(str(error))
                    continue

                result["rows"].append(parsed_row)

    except (OSError, csv.Error) as error:
        result["errors"].append(
            f"Could not read concordance file: {error}"
        )
        return result

    if not result["rows"]:
        result["errors"].append(
            "Concordance file contains no valid result rows."
        )

    result["valid"] = len(result["errors"]) == 0
    return result


def _find_concordance_files(
    evaluation_directory: Path,
    stage: str,
    expected_sample: str,
) -> list[Path]:
    pattern = f"*.{stage}.concordance.tsv"

    matches = sorted(
        path
        for path in evaluation_directory.glob(pattern)
        if path.is_file()
    )

    if expected_sample:
        expected_name = (
            f"{expected_sample}.{stage}.concordance.tsv"
        )

        matches = [
            path
            for path in matches
            if path.name == expected_name
        ]

    return matches


def get_qc_summary_data(
    run_name: str,
    expected_sample: str = "",
    results_root: Path | None = None,
) -> dict[str, Any]:
    """Combine MultiQC and truth-concordance evidence."""

    if results_root is None:
        results_root = RESULTS_ROOT

    results_root = results_root.resolve()

    report: dict[str, Any] = {
        "valid": False,
        "run_name": run_name,
        "expected_sample": expected_sample or None,
        "run_directory": None,
        "multiqc": None,
        "concordance": {
            "raw": [],
            "filtered": [],
        },
        "qc_decision": "not_evaluated",
        "errors": [],
        "warnings": [],
    }

    if not VALID_RUN_NAME.fullmatch(run_name):
        report["errors"].append(
            "Run name must begin with a lowercase letter, contain "
            "only lowercase letters, numbers and hyphens, and have "
            "between 3 and 40 characters."
        )
        return report

    if (
        expected_sample
        and not VALID_SAMPLE_NAME.fullmatch(expected_sample)
    ):
        report["errors"].append(
            "Expected sample contains unsupported characters."
        )
        return report

    run_directory = (results_root / run_name).resolve()
    report["run_directory"] = str(run_directory)

    if not _is_within(run_directory, results_root):
        report["errors"].append(
            "Run directory is outside the approved results root."
        )
        return report

    if not run_directory.is_dir():
        report["errors"].append(
            f"Run directory does not exist: {run_directory}"
        )
        return report

    multiqc_directory = run_directory / "report"

    multiqc_report = summarize_multiqc_data(
        multiqc_path=str(multiqc_directory),
        expected_sample=expected_sample,
        allowed_root=run_directory,
    )

    report["multiqc"] = multiqc_report

    if not multiqc_report["valid"]:
        report["errors"].extend(
            f"MultiQC: {error}"
            for error in multiqc_report["errors"]
        )

    report["warnings"].extend(
        f"MultiQC: {warning}"
        for warning in multiqc_report["warnings"]
    )

    evaluation_directory = (
        run_directory / "evaluation"
    )

    for stage in ("raw", "filtered"):
        concordance_files = _find_concordance_files(
            evaluation_directory=evaluation_directory,
            stage=stage,
            expected_sample=expected_sample,
        )

        if not concordance_files:
            sample_message = (
                f" for sample {expected_sample}"
                if expected_sample
                else ""
            )

            report["errors"].append(
                f"No {stage} concordance file was found"
                f"{sample_message}."
            )
            continue

        for concordance_path in concordance_files:
            concordance_report = read_concordance_file(
                path=concordance_path,
                allowed_root=run_directory,
            )

            report["concordance"][stage].append(
                concordance_report
            )

            if not concordance_report["valid"]:
                report["errors"].extend(
                    f"{stage.capitalize()} concordance: {error}"
                    for error in concordance_report["errors"]
                )

    report["warnings"].append(
        "No scientific pass/fail thresholds were applied. "
        "Review the recorded metrics against an approved "
        "scientific contract."
    )

    report["valid"] = len(report["errors"]) == 0
    return report


@tool
def get_qc_summary(
    run_name: str,
    expected_sample: str = "",
) -> str:
    """
    Read QC and concordance evidence from a completed pipeline run.

    The tool combines MultiQC metrics with raw and filtered
    truth-concordance tables. It reports recorded evidence but does
    not make clinical interpretations or invent scientific pass/fail
    thresholds.

    Args:
        run_name: Approved run name, for example
            phase8-monitoring-test.
        expected_sample: Sample identifier to summarize. Use an empty
            string to return all available samples.

    Returns:
        A JSON report containing MultiQC metrics, raw concordance,
        filtered concordance, errors, and warnings.
    """

    report = get_qc_summary_data(
        run_name=run_name,
        expected_sample=expected_sample,
    )

    return json.dumps(report, indent=2)