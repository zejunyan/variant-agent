import argparse
import hashlib
import json
import re
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from smolagents import tool

from agent_tools.validate_samplesheet import (
    validate_samplesheet_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = PROJECT_ROOT / "pipeline" / "main.nf"
APPROVED_INPUT_ROOT = PROJECT_ROOT / "test_data" / "human_grch38"
RESULTS_ROOT = PROJECT_ROOT / "results" / "agent_runs"
AUDIT_ROOT = PROJECT_ROOT / "execution_logs"

ALLOWED_WORKFLOWS = {
    "germline_test": PIPELINE_FILE,
}

ALLOWED_PROFILES = {
    "test",
}

ALLOWED_REFERENCES = {
    "GRCh38": {
        "reference": (
            APPROVED_INPUT_ROOT / "reference" / "chr20.fa"
        ),
        "truth": (
            APPROVED_INPUT_ROOT
            / "truth"
            / "human_test.truth.vcf.gz"
        ),
        "callable": (
            APPROVED_INPUT_ROOT
            / "truth"
            / "human_test.callable.bed"
        ),
    }
}

MAX_SAMPLES = 4
VALID_RUN_NAME = re.compile(r"^[a-z][a-z0-9-]{2,39}$")


def _is_within(path: Path, allowed_root: Path) -> bool:
    try:
        path.relative_to(allowed_root)
        return True
    except ValueError:
        return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_plan_id(plan_content: dict[str, Any]) -> str:
    serialized = json.dumps(
        plan_content,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()[:16]


def prepare_pipeline_run_data(
    samplesheet: str,
    workflow: str,
    profile: str,
    reference_build: str,
    run_name: str,
) -> dict[str, Any]:
    """
    Validate a proposed Nextflow run without executing it.
    """

    report: dict[str, Any] = {
        "valid": False,
        "execution_allowed": False,
        "plan_id": None,
        "workflow": workflow,
        "profile": profile,
        "reference_build": reference_build,
        "run_name": run_name,
        "samplesheet": samplesheet,
        "sample_count": None,
        "output_directory": None,
        "command": None,
        "command_display": None,
        "errors": [],
        "warnings": [],
    }

    if workflow not in ALLOWED_WORKFLOWS:
        report["errors"].append(
            f"Workflow is not allowed: {workflow}. "
            f"Allowed workflows: {sorted(ALLOWED_WORKFLOWS)}"
        )

    if profile not in ALLOWED_PROFILES:
        report["errors"].append(
            f"Profile is not allowed: {profile}. "
            f"Allowed profiles: {sorted(ALLOWED_PROFILES)}"
        )

    if reference_build not in ALLOWED_REFERENCES:
        report["errors"].append(
            f"Reference build is not allowed: {reference_build}. "
            f"Allowed references: {sorted(ALLOWED_REFERENCES)}"
        )

    if not VALID_RUN_NAME.fullmatch(run_name):
        report["errors"].append(
            "Run name must begin with a lowercase letter, contain "
            "only lowercase letters, numbers and hyphens, and have "
            "between 3 and 40 characters."
        )

    if report["errors"]:
        return report

    samplesheet_path = Path(samplesheet).expanduser()

    if not samplesheet_path.is_absolute():
        samplesheet_path = PROJECT_ROOT / samplesheet_path

    samplesheet_path = samplesheet_path.resolve()
    approved_root = APPROVED_INPUT_ROOT.resolve()

    if not _is_within(samplesheet_path, approved_root):
        report["errors"].append(
            "Samplesheet is outside the approved test-data directory: "
            f"{approved_root}"
        )
        return report

    validation = validate_samplesheet_data(
        samplesheet_path=str(samplesheet_path),
        allowed_root=approved_root,
    )

    if not validation["valid"]:
        report["errors"].extend(validation["errors"])
        return report

    sample_count = validation["sample_count"]
    report["sample_count"] = sample_count

    if sample_count > MAX_SAMPLES:
        report["errors"].append(
            f"Sample count {sample_count} exceeds the permitted "
            f"maximum of {MAX_SAMPLES}."
        )
        return report

    resources = ALLOWED_REFERENCES[reference_build]

    required_files = {
        "pipeline": ALLOWED_WORKFLOWS[workflow],
        "reference": resources["reference"],
        "reference_index": Path(
            f"{resources['reference']}.fai"
        ),
        "truth": resources["truth"],
        "truth_index": Path(
            f"{resources['truth']}.tbi"
        ),
        "callable": resources["callable"],
    }

    for label, path in required_files.items():
        if not path.is_file():
            report["errors"].append(
                f"Required {label} file does not exist: {path}"
            )

    if report["errors"]:
        return report

    output_directory = (
        RESULTS_ROOT / run_name
    ).resolve()

    work_directory = (
        PROJECT_ROOT
        / "work"
        / "agent_runs"
        / run_name
    ).resolve()

    trace_path = output_directory / "nextflow_trace.tsv"

    if not _is_within(output_directory, RESULTS_ROOT.resolve()):
        report["errors"].append(
            "Output directory is outside the approved results root."
        )
        return report

    if output_directory.exists():
        report["errors"].append(
            f"Output directory already exists: {output_directory}. "
            "Choose a new run name; automatic overwriting is prohibited."
        )
        return report

    command = [
        "nextflow",
        "run",
        "-work-dir",
        str(work_directory),
        str(ALLOWED_WORKFLOWS[workflow]),
        "-profile",
        profile,
        "-name",
        run_name,
        "-with-trace",
        str(trace_path),
        "--input",
        str(samplesheet_path),
        "--reference",
        str(resources["reference"]),
        "--truth",
        str(resources["truth"]),
        "--callable",
        str(resources["callable"]),
        "--outdir",
        str(output_directory),
    ]

    plan_content = {
        "workflow": workflow,
        "profile": profile,
        "reference_build": reference_build,
        "run_name": run_name,
        "samplesheet": str(samplesheet_path),
        "sample_count": sample_count,
        "work_directory": str(work_directory),
        "trace_path": str(trace_path),
        "output_directory": str(output_directory),
        "command": command,
    }

    report.update(plan_content)
    report["plan_id"] = _make_plan_id(plan_content)
    report["command_display"] = shlex.join(command)
    report["valid"] = True

    # Planning succeeded, but execution still requires approval.
    report["execution_allowed"] = False
    report["warnings"].append(
        "This is a plan only. The pipeline has not been executed."
    )

    return report


def execute_pipeline_run_data(
    samplesheet: str,
    workflow: str,
    profile: str,
    reference_build: str,
    run_name: str,
    approval: str,
    runner: Callable[..., Any] = subprocess.run,
) -> dict[str, Any]:
    """
    Execute an approved plan using a fixed subprocess argument list.

    This function is deliberately not exposed as an LLM tool.
    """

    plan = prepare_pipeline_run_data(
        samplesheet=samplesheet,
        workflow=workflow,
        profile=profile,
        reference_build=reference_build,
        run_name=run_name,
    )

    if not plan["valid"]:
        return {
            **plan,
            "executed": False,
            "exit_code": None,
        }

    expected_approval = f"APPROVE-{plan['plan_id']}"

    if approval != expected_approval:
        plan["errors"].append(
            "Execution approval is missing or does not match "
            "the current validated plan."
        )
        plan["warnings"].append(
            f"Required approval value: {expected_approval}"
        )
        return {
            **plan,
            "valid": False,
            "executed": False,
            "exit_code": None,
        }

    output_directory = Path(plan["output_directory"])
    audit_path = AUDIT_ROOT / f"{run_name}.json"

    if audit_path.exists():
        plan["errors"].append(
            f"Audit record already exists: {audit_path}"
        )
        return {
            **plan,
            "valid": False,
            "executed": False,
            "exit_code": None,
        }

    output_directory.mkdir(parents=True, exist_ok=False)
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)

    audit_record = {
        "plan_id": plan["plan_id"],
        "run_name": run_name,
        "workflow": workflow,
        "profile": profile,
        "reference_build": reference_build,
        "samplesheet": plan["samplesheet"],
        "sample_count": plan["sample_count"],
        "output_directory": plan["output_directory"],
        "work_directory": plan["work_directory"],
        "trace_path": plan["trace_path"],
        "command": plan["command"],
        "started_at": _utc_now(),
        "completed_at": None,
        "status": "running",
        "exit_code": None,
    }

    audit_path.write_text(
        json.dumps(audit_record, indent=2),
        encoding="utf-8",
    )

    try:
        completed_process = runner(
            plan["command"],
            cwd=PROJECT_ROOT,
            check=False,
        )

        exit_code = completed_process.returncode

        audit_record["completed_at"] = _utc_now()
        audit_record["exit_code"] = exit_code
        audit_record["status"] = (
            "completed" if exit_code == 0 else "failed"
        )

        audit_path.write_text(
            json.dumps(audit_record, indent=2),
            encoding="utf-8",
        )

        return {
            **plan,
            "execution_allowed": True,
            "executed": True,
            "exit_code": exit_code,
            "status": audit_record["status"],
            "audit_path": str(audit_path),
        }

    except OSError as error:
        audit_record["completed_at"] = _utc_now()
        audit_record["status"] = "failed_to_start"
        audit_record["error"] = str(error)

        audit_path.write_text(
            json.dumps(audit_record, indent=2),
            encoding="utf-8",
        )

        return {
            **plan,
            "valid": False,
            "execution_allowed": True,
            "executed": False,
            "exit_code": None,
            "status": "failed_to_start",
            "audit_path": str(audit_path),
            "errors": [
                *plan["errors"],
                f"Pipeline could not start: {error}",
            ],
        }


@tool
def prepare_pipeline_run(
    samplesheet: str,
    workflow: str,
    profile: str,
    reference_build: str,
    run_name: str,
) -> str:
    """
    Prepare and validate a pipeline run without executing it.

    Use this tool to create a safe run plan. It cannot execute the
    pipeline. Only approved workflow, profile, reference and input
    locations are accepted.

    Args:
        samplesheet: Path to the paired-end CSV samplesheet.
        workflow: Approved workflow. Use germline_test.
        profile: Approved execution profile. Use test.
        reference_build: Approved reference. Use GRCh38.
        run_name: Unique lowercase run name containing only letters,
            numbers and hyphens, for example demo-001.

    Returns:
        A JSON run plan containing validation results, the fixed
        command, plan ID, errors and warnings.
    """

    report = prepare_pipeline_run_data(
        samplesheet=samplesheet,
        workflow=workflow,
        profile=profile,
        reference_build=reference_build,
        run_name=run_name,
    )

    return json.dumps(report, indent=2)


@tool
def execute_pipeline_run(
    samplesheet: str,
    workflow: str,
    profile: str,
    reference_build: str,
    run_name: str,
    approval: str,
) -> str:
    """Execute a validated pipeline run after exact human approval.

    Call prepare_pipeline_run first. Execution proceeds only when approval
    exactly matches APPROVE-<plan-id> for the same validated inputs.

    Args:
        samplesheet: Path to the paired-end CSV samplesheet.
        workflow: Approved workflow. Use germline_test.
        profile: Approved execution profile. Use test.
        reference_build: Approved reference. Use GRCh38.
        run_name: The same unique run name used to prepare the plan.
        approval: Exact human-provided APPROVE-<plan-id> value.

    Returns:
        JSON containing execution status, exit code, output directory,
        audit path, errors, and warnings.
    """

    report = execute_pipeline_run_data(
        samplesheet=samplesheet,
        workflow=workflow,
        profile=profile,
        reference_build=reference_build,
        run_name=run_name,
        approval=approval,
    )
    return json.dumps(report, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare or manually execute an approved pipeline run."
        )
    )

    parser.add_argument("--samplesheet", required=True)
    parser.add_argument("--workflow", default="germline_test")
    parser.add_argument("--profile", default="test")
    parser.add_argument("--reference-build", default="GRCh38")
    parser.add_argument("--run-name", required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute after validating the approval value.",
    )
    parser.add_argument(
        "--approval",
        default="",
        help="Exact APPROVE-<plan-id> value.",
    )

    args = parser.parse_args()

    if args.execute:
        report = execute_pipeline_run_data(
            samplesheet=args.samplesheet,
            workflow=args.workflow,
            profile=args.profile,
            reference_build=args.reference_build,
            run_name=args.run_name,
            approval=args.approval,
        )
    else:
        report = prepare_pipeline_run_data(
            samplesheet=args.samplesheet,
            workflow=args.workflow,
            profile=args.profile,
            reference_build=args.reference_build,
            run_name=args.run_name,
        )

    print(json.dumps(report, indent=2))

    if args.execute and (
        not report.get("executed")
        or report.get("exit_code") != 0
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
