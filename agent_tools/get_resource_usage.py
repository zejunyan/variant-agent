import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results" / "agent_runs"

VALID_RUN_NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")

SIZE_MULTIPLIERS = {
    "B": 1,
    "KB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
    "KIB": 1024,
    "MIB": 1024**2,
    "GIB": 1024**3,
    "TIB": 1024**4,
}


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def parse_size_to_bytes(value: str | None) -> int | None:
    """Convert a Nextflow memory value into bytes."""

    if value is None:
        return None

    value = value.strip()

    if not value or value == "-":
        return None

    parts = value.upper().split()

    if len(parts) == 1:
        try:
            return int(float(parts[0]))
        except ValueError:
            return None

    if len(parts) != 2:
        return None

    number, unit = parts

    if unit not in SIZE_MULTIPLIERS:
        return None

    try:
        return int(
            float(number) * SIZE_MULTIPLIERS[unit]
        )
    except ValueError:
        return None


def get_resource_usage_data(
    run_name: str,
    results_root: Path | None = None,
) -> dict[str, Any]:
    """Read process resource metrics from a Nextflow trace."""

    if results_root is None:
        results_root = RESULTS_ROOT

    results_root = results_root.resolve()

    report: dict[str, Any] = {
        "valid": False,
        "run_name": run_name,
        "trace_path": None,
        "process_count": 0,
        "status_counts": {},
        "processes": [],
        "largest_peak_rss": None,
        "largest_peak_vmem": None,
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

    if not trace_path.is_file():
        report["errors"].append(
            f"Nextflow trace file does not exist: {trace_path}"
        )
        return report

    status_counter: Counter[str] = Counter()

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

            available_resource_columns = {
                "duration",
                "realtime",
                "%cpu",
                "peak_rss",
                "peak_vmem",
                "rchar",
                "wchar",
            }.intersection(reader.fieldnames)

            if not available_resource_columns:
                report["warnings"].append(
                    "Trace contains no standard resource columns."
                )

            for row_number, row in enumerate(
                reader,
                start=2,
            ):
                name = (row.get("name") or "").strip()
                status = (
                    row.get("status") or ""
                ).strip().upper()

                if not name:
                    report["warnings"].append(
                        f"Trace row {row_number} has no process name."
                    )
                    continue

                if not status:
                    status = "UNKNOWN"

                status_counter[status] += 1

                peak_rss = (
                    row.get("peak_rss") or ""
                ).strip() or None

                peak_vmem = (
                    row.get("peak_vmem") or ""
                ).strip() or None

                process = {
                    "name": name,
                    "status": status,
                    "task_id": (
                        row.get("task_id") or ""
                    ).strip() or None,
                    "hash": (
                        row.get("hash") or ""
                    ).strip() or None,
                    "exit_code": (
                        row.get("exit") or ""
                    ).strip() or None,
                    "duration": (
                        row.get("duration") or ""
                    ).strip() or None,
                    "realtime": (
                        row.get("realtime") or ""
                    ).strip() or None,
                    "cpu_percent": (
                        row.get("%cpu") or ""
                    ).strip() or None,
                    "peak_rss": peak_rss,
                    "peak_rss_bytes": parse_size_to_bytes(
                        peak_rss
                    ),
                    "peak_vmem": peak_vmem,
                    "peak_vmem_bytes": parse_size_to_bytes(
                        peak_vmem
                    ),
                    "read_characters": (
                        row.get("rchar") or ""
                    ).strip() or None,
                    "written_characters": (
                        row.get("wchar") or ""
                    ).strip() or None,
                }

                report["processes"].append(process)

    except (OSError, csv.Error) as error:
        report["errors"].append(
            f"Could not read Nextflow trace: {error}"
        )
        return report

    report["process_count"] = len(report["processes"])
    report["status_counts"] = dict(status_counter)

    rss_candidates = [
        process
        for process in report["processes"]
        if process["peak_rss_bytes"] is not None
    ]

    if rss_candidates:
        largest = max(
            rss_candidates,
            key=lambda process: process["peak_rss_bytes"],
        )

        report["largest_peak_rss"] = {
            "name": largest["name"],
            "peak_rss": largest["peak_rss"],
            "peak_rss_bytes": largest["peak_rss_bytes"],
        }

    vmem_candidates = [
        process
        for process in report["processes"]
        if process["peak_vmem_bytes"] is not None
    ]

    if vmem_candidates:
        largest = max(
            vmem_candidates,
            key=lambda process: process["peak_vmem_bytes"],
        )

        report["largest_peak_vmem"] = {
            "name": largest["name"],
            "peak_vmem": largest["peak_vmem"],
            "peak_vmem_bytes": largest["peak_vmem_bytes"],
        }

    if not report["processes"]:
        report["warnings"].append(
            "Nextflow trace contains no process rows."
        )

    report["valid"] = True
    return report


@tool
def get_resource_usage(run_name: str) -> str:
    """
    Read resource usage from a controlled Nextflow run.

    This tool reports process duration, CPU usage, peak resident
    memory, peak virtual memory, and I/O values recorded in the
    Nextflow trace. It does not change resource requests or rerun
    any process.

    Args:
        run_name: Approved run name, for example
            phase8-monitoring-test.

    Returns:
        A JSON report containing per-process resource metrics,
        status counts, the largest memory users, errors, and warnings.
    """

    report = get_resource_usage_data(
        run_name=run_name
    )

    return json.dumps(report, indent=2)