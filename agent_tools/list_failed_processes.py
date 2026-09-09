import csv
import json
import re
from pathlib import Path
from typing import Any

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results" / "agent_runs"

VALID_RUN_NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")

FAILED_STATUSES = {
    "FAILED",
    "ABORTED",
}


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _parse_exit_code(value: str | None) -> int | None:
    if value is None:
        return None

    value = value.strip()

    if not value or value == "-":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def list_failed_processes_data(
    run_name: str,
    results_root: Path | None = None,
) -> dict[str, Any]:
    """Read a Nextflow trace and identify failed tasks."""

    if results_root is None:
        results_root = RESULTS_ROOT

    results_root = results_root.resolve()

    report: dict[str, Any] = {
        "valid": False,
        "run_name": run_name,
        "trace_path": None,
        "process_count": 0,
        "failed_count": 0,
        "failed_processes": [],
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

    run_directory = (results_root / run_name).resolve()
    trace_path = (
        run_directory / "nextflow_trace.tsv"
    ).resolve()

    report["trace_path"] = str(trace_path)

    if not _is_within(run_directory, results_root):
        report["errors"].append(
            "Run directory is outside the approved results root."
        )
        return report

    if not _is_within(trace_path, results_root):
        report["errors"].append(
            "Trace path is outside the approved results root."
        )
        return report

    if not trace_path.is_file():
        report["errors"].append(
            f"Nextflow trace file does not exist: {trace_path}"
        )
        return report

    try:
        with trace_path.open(
            newline="",
            encoding="utf-8",
        ) as handle:
            reader = csv.DictReader(
                handle,
                delimiter="\t",
            )

            if reader.fieldnames is None:
                report["errors"].append(
                    "Nextflow trace has no header."
                )
                return report

            required_columns = {
                "name",
                "status",
            }

            missing_columns = (
                required_columns - set(reader.fieldnames)
            )

            if missing_columns:
                report["errors"].append(
                    "Nextflow trace is missing required columns: "
                    f"{sorted(missing_columns)}"
                )
                return report

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                process_name = (
                    row.get("name") or ""
                ).strip()

                status = (
                    row.get("status") or ""
                ).strip().upper()

                exit_code = _parse_exit_code(
                    row.get("exit")
                )

                if not process_name:
                    report["warnings"].append(
                        f"Trace row {row_number} has no process name."
                    )
                    continue

                report["process_count"] += 1

                failed = (
                    status in FAILED_STATUSES
                    or (
                        exit_code is not None
                        and exit_code != 0
                    )
                )

                if not failed:
                    continue

                report["failed_processes"].append(
                    {
                        "name": process_name,
                        "status": status or None,
                        "exit_code": exit_code,
                        "task_id": (
                            row.get("task_id") or ""
                        ).strip() or None,
                        "hash": (
                            row.get("hash") or ""
                        ).strip() or None,
                        "native_id": (
                            row.get("native_id") or ""
                        ).strip() or None,
                        "duration": (
                            row.get("duration") or ""
                        ).strip() or None,
                        "realtime": (
                            row.get("realtime") or ""
                        ).strip() or None,
                        "peak_rss": (
                            row.get("peak_rss") or ""
                        ).strip() or None,
                        "peak_vmem": (
                            row.get("peak_vmem") or ""
                        ).strip() or None,
                    }
                )

    except (OSError, csv.Error) as error:
        report["errors"].append(
            f"Could not read Nextflow trace: {error}"
        )
        return report

    report["failed_count"] = len(
        report["failed_processes"]
    )
    report["valid"] = True

    if report["process_count"] == 0:
        report["warnings"].append(
            "Nextflow trace contains no process rows."
        )

    elif report["failed_count"] == 0:
        report["warnings"].append(
            "No failed processes were found in the trace."
        )

    return report


@tool
def list_failed_processes(run_name: str) -> str:
    """
    List failed processes from a controlled Nextflow run.

    This tool reads the run's Nextflow trace file and returns tasks
    with FAILED or ABORTED status, or a nonzero exit code. It does
    not modify, resume, or rerun the pipeline.

    Args:
        run_name: Approved run name, for example
            phase8-monitoring-test.

    Returns:
        A JSON report containing failed process names, statuses,
        exit codes, task hashes, resource values, errors, and warnings.
    """

    report = list_failed_processes_data(
        run_name=run_name
    )

    return json.dumps(report, indent=2)