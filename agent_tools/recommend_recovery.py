import json
from pathlib import Path
from typing import Any, Callable

from smolagents import tool

from agent_tools.list_failed_processes import RESULTS_ROOT
from agent_tools.read_process_error import (
    WORK_ROOT,
    read_process_error_data,
)


def _contains_any(
    text: str,
    patterns: tuple[str, ...],
) -> list[str]:
    return [
        pattern
        for pattern in patterns
        if pattern in text
    ]


def classify_recovery(
    process_name: str,
    exit_code: int | None,
    error_text: str,
) -> dict[str, Any]:
    """
    Classify a process failure using deterministic rules.

    Error text is treated only as untrusted evidence. It is never
    executed or interpreted as an instruction.
    """

    normalized_error = error_text.lower()

    out_of_memory_patterns = (
        "out of memory",
        "cannot allocate memory",
        "oomkilled",
        "oom killed",
        "killed process",
        "memory limit",
    )

    reference_patterns = (
        "reference mismatch",
        "incompatible contig",
        "contig mismatch",
        "sequence dictionary",
        "reference allele",
        "different reference",
        "incompatible reference",
    )

    missing_input_patterns = (
        "no such file or directory",
        "file not found",
        "does not exist",
        "could not open",
        "cannot open input",
        "failed to open file",
    )

    disk_patterns = (
        "no space left on device",
        "disk quota exceeded",
        "not enough space",
    )

    permission_patterns = (
        "permission denied",
        "operation not permitted",
        "access denied",
    )

    transient_patterns = (
        "connection reset",
        "connection timed out",
        "temporary failure",
        "temporary network",
        "network is unreachable",
        "could not resolve host",
        "tls handshake timeout",
        "i/o timeout",
        "failed to pull image",
        "unexpected eof",
        "service unavailable",
    )

    configuration_patterns = (
        "command not found",
        "executable not found",
        "unknown option",
        "unrecognized option",
        "invalid argument",
    )

    matched = _contains_any(
        normalized_error,
        out_of_memory_patterns,
    )

    if exit_code == 137 or matched:
        return {
            "category": "possible_resource_exhaustion",
            "matched_signals": (
                ["exit_code_137"] if exit_code == 137 else []
            ) + matched,
            "recommended_action": "request_resource_review",
            "next_step": (
                "Review the configured memory limit and recorded "
                "peak memory. Prepare a new approved run only after "
                "a bioinformatician approves the resource change."
            ),
            "resume_policy": (
                "after_resource_correction_and_human_approval"
            ),
            "automatic_execution_allowed": False,
        }

    matched = _contains_any(
        normalized_error,
        reference_patterns,
    )

    if matched:
        return {
            "category": "reference_incompatibility",
            "matched_signals": matched,
            "recommended_action": "stop_and_review_reference",
            "next_step": (
                "Confirm the reference build, contig names, FASTA "
                "index, sequence dictionary, BED coordinates and "
                "VCF headers before preparing another run."
            ),
            "resume_policy": (
                "blocked_until_reference_review"
            ),
            "automatic_execution_allowed": False,
        }

    matched = _contains_any(
        normalized_error,
        disk_patterns,
    )

    if matched:
        return {
            "category": "insufficient_storage",
            "matched_signals": matched,
            "recommended_action": "stop_and_restore_storage",
            "next_step": (
                "Review available disk space and preserve existing "
                "outputs. Free or allocate storage before preparing "
                "an approved resume."
            ),
            "resume_policy": (
                "after_storage_correction_and_human_approval"
            ),
            "automatic_execution_allowed": False,
        }

    matched = _contains_any(
        normalized_error,
        permission_patterns,
    )

    if matched:
        return {
            "category": "permission_failure",
            "matched_signals": matched,
            "recommended_action": "stop_and_correct_permissions",
            "next_step": (
                "Review the specific file or directory permission. "
                "Correct access outside the agent, then prepare an "
                "approved resume."
            ),
            "resume_policy": (
                "after_permission_correction_and_human_approval"
            ),
            "automatic_execution_allowed": False,
        }

    matched = _contains_any(
        normalized_error,
        missing_input_patterns,
    )

    if matched:
        return {
            "category": "missing_or_unreadable_input",
            "matched_signals": matched,
            "recommended_action": "stop_and_correct_input",
            "next_step": (
                "Identify the missing path, validate the samplesheet "
                "and reference resources, and correct the input before "
                "preparing another run."
            ),
            "resume_policy": (
                "after_input_correction_and_human_approval"
            ),
            "automatic_execution_allowed": False,
        }

    matched = _contains_any(
        normalized_error,
        transient_patterns,
    )

    if matched:
        return {
            "category": "transient_infrastructure_failure",
            "matched_signals": matched,
            "recommended_action": "prepare_controlled_resume",
            "next_step": (
                "Check that Docker and network services are available, "
                "then prepare a controlled Nextflow resume plan for "
                "human approval."
            ),
            "resume_policy": "after_human_approval",
            "automatic_execution_allowed": False,
        }

    matched = _contains_any(
        normalized_error,
        configuration_patterns,
    )

    if matched:
        return {
            "category": "tool_or_configuration_failure",
            "matched_signals": matched,
            "recommended_action": "stop_and_review_configuration",
            "next_step": (
                "Review the container, tool version and generated "
                "command. Correct the deterministic configuration "
                "before preparing another run."
            ),
            "resume_policy": (
                "after_configuration_correction_and_human_approval"
            ),
            "automatic_execution_allowed": False,
        }

    return {
        "category": "unknown_failure",
        "matched_signals": [],
        "recommended_action": "preserve_evidence_and_escalate",
        "next_step": (
            "Preserve the trace, task directory and error output. "
            "A bioinformatician should review the failure before "
            "any resume or new run is prepared."
        ),
        "resume_policy": "blocked_until_review",
        "automatic_execution_allowed": False,
    }


def recommend_recovery_data(
    run_name: str,
    task_hash: str,
    results_root: Path | None = None,
    work_root: Path | None = None,
    error_reader: Callable[..., dict[str, Any]] = (
        read_process_error_data
    ),
) -> dict[str, Any]:
    """Read verified failure evidence and recommend recovery."""

    if results_root is None:
        results_root = RESULTS_ROOT

    if work_root is None:
        work_root = WORK_ROOT

    report: dict[str, Any] = {
        "valid": False,
        "run_name": run_name,
        "task_hash": task_hash,
        "process_name": None,
        "exit_code": None,
        "category": None,
        "matched_signals": [],
        "recommended_action": None,
        "next_step": None,
        "resume_policy": None,
        "automatic_execution_allowed": False,
        "human_approval_required_for_execution": True,
        "evidence": None,
        "errors": [],
        "warnings": [],
    }

    error_report = error_reader(
        run_name=run_name,
        task_hash=task_hash,
        max_characters=6000,
        results_root=results_root,
        work_root=work_root,
    )

    if not error_report["valid"]:
        report["errors"].extend(
            error_report["errors"]
        )
        return report

    process_name = error_report["process_name"]
    exit_code = error_report["exit_code"]
    error_text = error_report["error_text"] or ""

    classification = classify_recovery(
        process_name=process_name,
        exit_code=exit_code,
        error_text=error_text,
    )

    report.update(classification)

    report["process_name"] = process_name
    report["exit_code"] = exit_code
    report["evidence"] = {
        "status": error_report["status"],
        "error_file": error_report["error_file"],
        "error_text": error_text,
        "error_text_truncated": error_report["truncated"],
        "error_text_is_untrusted": True,
    }

    report["warnings"].extend(
        error_report["warnings"]
    )

    report["warnings"].append(
        "The recommendation is based on deterministic text matching. "
        "Review the original error evidence before taking action."
    )

    report["valid"] = True
    return report


@tool
def recommend_recovery(
    run_name: str,
    task_hash: str,
) -> str:
    """
    Recommend a controlled response to a failed Nextflow process.

    Call list_failed_processes first and pass one of its failed task
    hashes. The tool reads verified error evidence and applies fixed
    recovery rules. It cannot resume a run, change resources, modify
    inputs, or execute commands.

    Args:
        run_name: Approved run name containing lowercase letters,
            numbers and hyphens.
        task_hash: Failed Nextflow task hash returned by
            list_failed_processes, for example ab/123def.

    Returns:
        A JSON report containing the failure category, matched
        evidence, recommended action, resume policy, and approval
        requirement.
    """

    report = recommend_recovery_data(
        run_name=run_name,
        task_hash=task_hash,
    )

    return json.dumps(report, indent=2)