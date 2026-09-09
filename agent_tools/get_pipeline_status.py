import json
import re
from pathlib import Path
from typing import Any

from smolagents import tool


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = PROJECT_ROOT / "execution_logs"
RESULTS_ROOT = PROJECT_ROOT / "results" / "agent_runs"

VALID_RUN_NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")

ALLOWED_RECORDED_STATUSES = {
    "running",
    "completed",
    "failed",
    "failed_to_start",
}

EXPECTED_OUTPUT_PATTERNS = {
    "multiqc_report": "report/multiqc_report.html",
    "pass_vcf": "variants/*.pass.vcf.gz",
    "filtered_concordance": (
        "evaluation/*.filtered.concordance.tsv"
    ),
}


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def get_pipeline_status_data(
    run_name: str,
    audit_root: Path | None = None,
    results_root: Path | None = None,
) -> dict[str, Any]:
    """Inspect the recorded state of a controlled pipeline run."""

    if audit_root is None:
        audit_root = AUDIT_ROOT

    if results_root is None:
        results_root = RESULTS_ROOT

    audit_root = audit_root.resolve()
    results_root = results_root.resolve()

    report: dict[str, Any] = {
        "valid": False,
        "run_name": run_name,
        "pipeline_status": "unknown",
        "recorded_status": None,
        "technical_success": None,
        "exit_code": None,
        "started_at": None,
        "completed_at": None,
        "sample_count": None,
        "workflow": None,
        "profile": None,
        "reference_build": None,
        "audit_path": None,
        "output_directory": None,
        "expected_outputs": {},
        "missing_outputs": [],
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

    audit_path = (audit_root / f"{run_name}.json").resolve()
    output_directory = (results_root / run_name).resolve()

    report["audit_path"] = str(audit_path)
    report["output_directory"] = str(output_directory)

    if not _is_within(audit_path, audit_root):
        report["errors"].append(
            "Resolved audit path is outside the approved audit root."
        )
        return report

    if not _is_within(output_directory, results_root):
        report["errors"].append(
            "Resolved output path is outside the approved results root."
        )
        return report

    if not audit_path.is_file():
        report["errors"].append(
            f"No audit record was found for run: {run_name}"
        )
        return report

    try:
        audit_record = json.loads(
            audit_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        report["errors"].append(
            f"Could not read audit record: {error}"
        )
        return report

    if audit_record.get("run_name") != run_name:
        report["errors"].append(
            "Audit record run name does not match the requested run."
        )
        return report

    recorded_status = audit_record.get("status")

    if recorded_status not in ALLOWED_RECORDED_STATUSES:
        report["errors"].append(
            f"Audit record contains an unsupported status: "
            f"{recorded_status}"
        )
        return report

    report.update(
        {
            "valid": True,
            "recorded_status": recorded_status,
            "pipeline_status": recorded_status,
            "exit_code": audit_record.get("exit_code"),
            "started_at": audit_record.get("started_at"),
            "completed_at": audit_record.get("completed_at"),
            "sample_count": audit_record.get("sample_count"),
            "workflow": audit_record.get("workflow"),
            "profile": audit_record.get("profile"),
            "reference_build": audit_record.get(
                "reference_build"
            ),
        }
    )

    recorded_output = audit_record.get("output_directory")

    if recorded_output:
        recorded_output_path = Path(
            recorded_output
        ).expanduser().resolve()

        if recorded_output_path != output_directory:
            report["warnings"].append(
                "The output directory recorded in the audit log "
                "does not match the approved run output directory."
            )

    for label, pattern in EXPECTED_OUTPUT_PATTERNS.items():
        matches = sorted(output_directory.glob(pattern))

        report["expected_outputs"][label] = [
            str(path)
            for path in matches
            if path.is_file()
        ]

        if not report["expected_outputs"][label]:
            report["missing_outputs"].append(label)

    if recorded_status == "completed":
        if audit_record.get("exit_code") != 0:
            report["pipeline_status"] = (
                "inconsistent_audit_record"
            )
            report["technical_success"] = False
            report["errors"].append(
                "Run is recorded as completed but its exit code "
                "is not zero."
            )

        elif report["missing_outputs"]:
            report["pipeline_status"] = (
                "completed_with_missing_outputs"
            )
            report["technical_success"] = False
            report["warnings"].append(
                "The run completed with exit code zero, but one or "
                "more expected outputs are missing."
            )

        else:
            report["technical_success"] = True

    elif recorded_status in {"failed", "failed_to_start"}:
        report["technical_success"] = False

    elif recorded_status == "running":
        report["technical_success"] = None

        if report["missing_outputs"]:
            report["warnings"].append(
                "Missing outputs may be expected while the pipeline "
                "is still running."
            )

    return report


@tool
def get_pipeline_status(run_name: str) -> str:
    """
    Inspect the status of a controlled pipeline run.

    This tool reads the Phase 7 audit record and checks for essential
    pipeline outputs. It does not launch, resume, stop, or modify the
    pipeline.

    Args:
        run_name: Approved run name, for example
            phase7-execution-test.

    Returns:
        A JSON status report containing the recorded state, exit code,
        timestamps, expected outputs, errors, and warnings.
    """

    report = get_pipeline_status_data(run_name=run_name)

    return json.dumps(report, indent=2)