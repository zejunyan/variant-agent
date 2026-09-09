import json
import re
from pathlib import Path
from typing import Any

from smolagents import tool

from agent_tools.list_failed_processes import (
    RESULTS_ROOT,
    list_failed_processes_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = PROJECT_ROOT / "work" / "agent_runs"

VALID_RUN_NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
VALID_TASK_HASH = re.compile(
    r"^[0-9a-fA-F]{2}/[0-9a-fA-F]{3,}$"
)

MIN_CHARACTERS = 200
MAX_CHARACTERS = 10_000


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _find_task_directory(
    work_root: Path,
    run_name: str,
    task_hash: str,
) -> tuple[Path | None, list[str]]:
    """Find the full Nextflow task directory from a trace hash."""

    errors: list[str] = []

    hash_prefix, task_prefix = task_hash.split("/", 1)

    run_work_directory = (
        work_root / run_name
    ).resolve()

    hash_directory = (
        run_work_directory / hash_prefix
    ).resolve()

    if not _is_within(hash_directory, run_work_directory):
        return None, [
            "Resolved task path is outside the approved run work "
            "directory."
        ]

    if not hash_directory.is_dir():
        return None, [
            f"Nextflow hash directory does not exist: "
            f"{hash_directory}"
        ]

    matches = [
        path.resolve()
        for path in hash_directory.glob(f"{task_prefix}*")
        if path.is_dir()
    ]

    matches = [
        path
        for path in matches
        if _is_within(path, run_work_directory)
    ]

    if not matches:
        errors.append(
            f"No Nextflow task directory matched hash: {task_hash}"
        )
        return None, errors

    if len(matches) > 1:
        errors.append(
            f"Task hash is ambiguous and matched multiple "
            f"directories: {task_hash}"
        )
        return None, errors

    return matches[0], errors


def read_process_error_data(
    run_name: str,
    task_hash: str,
    max_characters: int = 4000,
    results_root: Path | None = None,
    work_root: Path | None = None,
) -> dict[str, Any]:
    """Read the error output of one failed Nextflow task."""

    if results_root is None:
        results_root = RESULTS_ROOT

    if work_root is None:
        work_root = WORK_ROOT

    results_root = results_root.resolve()
    work_root = work_root.resolve()

    report: dict[str, Any] = {
        "valid": False,
        "run_name": run_name,
        "task_hash": task_hash,
        "process_name": None,
        "status": None,
        "exit_code": None,
        "task_directory": None,
        "error_file": None,
        "error_text": None,
        "truncated": False,
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

    if not VALID_TASK_HASH.fullmatch(task_hash):
        report["errors"].append(
            "Task hash must use the Nextflow format aa/bbbbb, "
            "containing hexadecimal characters only."
        )
        return report

    if (
        max_characters < MIN_CHARACTERS
        or max_characters > MAX_CHARACTERS
    ):
        report["errors"].append(
            f"max_characters must be between {MIN_CHARACTERS} "
            f"and {MAX_CHARACTERS}."
        )
        return report

    failure_report = list_failed_processes_data(
        run_name=run_name,
        results_root=results_root,
    )

    if not failure_report["valid"]:
        report["errors"].extend(
            failure_report["errors"]
        )
        return report

    matching_failure = next(
        (
            process
            for process in failure_report["failed_processes"]
            if process.get("hash") == task_hash
        ),
        None,
    )

    if matching_failure is None:
        report["errors"].append(
            "The requested task hash is not listed as a failed "
            "process in this run's trace."
        )
        return report

    report["process_name"] = matching_failure["name"]
    report["status"] = matching_failure["status"]
    report["exit_code"] = matching_failure["exit_code"]

    task_directory, path_errors = _find_task_directory(
        work_root=work_root,
        run_name=run_name,
        task_hash=task_hash,
    )

    if path_errors:
        report["errors"].extend(path_errors)
        return report

    report["task_directory"] = str(task_directory)

    error_file = (task_directory / ".command.err").resolve()
    report["error_file"] = str(error_file)

    run_work_directory = (
        work_root / run_name
    ).resolve()

    if not _is_within(error_file, run_work_directory):
        report["errors"].append(
            "Resolved error file is outside the approved work "
            "directory."
        )
        return report

    if not error_file.is_file():
        report["errors"].append(
            f"Nextflow process error file does not exist: "
            f"{error_file}"
        )
        return report

    try:
        error_text = error_file.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError as error:
        report["errors"].append(
            f"Could not read process error file: {error}"
        )
        return report

    if len(error_text) > max_characters:
        error_text = error_text[-max_characters:]
        report["truncated"] = True
        report["warnings"].append(
            "Only the final portion of the error output was "
            "returned."
        )

    report["error_text"] = error_text.strip()
    report["valid"] = True

    if not report["error_text"]:
        report["warnings"].append(
            "The process error file is empty."
        )

    return report


@tool
def read_process_error(
    run_name: str,
    task_hash: str,
    max_characters: int = 4000,
) -> str:
    """
    Read the error output for a failed Nextflow process.

    Call list_failed_processes first and use a task hash returned by
    that tool. This tool only reads `.command.err` for a task recorded
    as failed in the selected run. It does not execute, modify, resume,
    or delete anything.

    Args:
        run_name: Approved run name containing lowercase letters,
            numbers and hyphens.
        task_hash: Failed task hash returned by
            list_failed_processes, for example ab/123def.
        max_characters: Maximum number of error characters to return.
            Allowed values are integers from 200 to 10000.

    Returns:
        A JSON report containing the process name, status, exit code,
        task directory, bounded error text, errors, and warnings.
    """

    report = read_process_error_data(
        run_name=run_name,
        task_hash=task_hash,
        max_characters=max_characters,
    )

    return json.dumps(report, indent=2)