from pathlib import Path

from agent_tools.recommend_recovery import (
    classify_recovery,
    recommend_recovery_data,
)


def test_exit_137_requests_resource_review():
    result = classify_recovery(
        process_name="GATK_HAPLOTYPECALLER",
        exit_code=137,
        error_text="Process was killed.",
    )

    assert result["category"] == (
        "possible_resource_exhaustion"
    )
    assert result["recommended_action"] == (
        "request_resource_review"
    )
    assert result["automatic_execution_allowed"] is False


def test_reference_mismatch_stops_recovery():
    result = classify_recovery(
        process_name="GATK_GENOTYPEGVCFS",
        exit_code=1,
        error_text=(
            "Input contains an incompatible contig and "
            "reference mismatch."
        ),
    )

    assert result["category"] == (
        "reference_incompatibility"
    )
    assert result["resume_policy"] == (
        "blocked_until_reference_review"
    )


def test_missing_input_requires_correction():
    result = classify_recovery(
        process_name="FASTQC",
        exit_code=1,
        error_text=(
            "No such file or directory: sample_R1.fastq.gz"
        ),
    )

    assert result["category"] == (
        "missing_or_unreadable_input"
    )
    assert result["recommended_action"] == (
        "stop_and_correct_input"
    )


def test_network_failure_can_prepare_resume():
    result = classify_recovery(
        process_name="FASTQC",
        exit_code=1,
        error_text=(
            "Failed to pull image: connection timed out"
        ),
    )

    assert result["category"] == (
        "transient_infrastructure_failure"
    )
    assert result["recommended_action"] == (
        "prepare_controlled_resume"
    )
    assert result["resume_policy"] == (
        "after_human_approval"
    )


def test_disk_failure_requires_storage_correction():
    result = classify_recovery(
        process_name="SAMTOOLS_SORT",
        exit_code=1,
        error_text="No space left on device",
    )

    assert result["category"] == "insufficient_storage"
    assert result["automatic_execution_allowed"] is False


def test_unknown_failure_is_escalated():
    result = classify_recovery(
        process_name="UNKNOWN_PROCESS",
        exit_code=1,
        error_text="Unexpected scientific software failure",
    )

    assert result["category"] == "unknown_failure"
    assert result["recommended_action"] == (
        "preserve_evidence_and_escalate"
    )
    assert result["resume_policy"] == (
        "blocked_until_review"
    )


def test_recommendation_uses_verified_error_report():
    def fake_error_reader(**kwargs):
        assert kwargs["run_name"] == "failed-run"
        assert kwargs["task_hash"] == "ab/123def"

        return {
            "valid": True,
            "run_name": "failed-run",
            "task_hash": "ab/123def",
            "process_name": "SAMTOOLS_SORT (sample01)",
            "status": "FAILED",
            "exit_code": 137,
            "error_file": "/safe/work/.command.err",
            "error_text": "Killed due to out of memory.",
            "truncated": False,
            "errors": [],
            "warnings": [],
        }

    report = recommend_recovery_data(
        run_name="failed-run",
        task_hash="ab/123def",
        results_root=Path("/safe/results"),
        work_root=Path("/safe/work"),
        error_reader=fake_error_reader,
    )

    assert report["valid"] is True
    assert report["process_name"] == (
        "SAMTOOLS_SORT (sample01)"
    )
    assert report["category"] == (
        "possible_resource_exhaustion"
    )
    assert report["evidence"]["error_text_is_untrusted"] is True
    assert report["automatic_execution_allowed"] is False
    assert (
        report["human_approval_required_for_execution"]
        is True
    )


def test_invalid_error_evidence_prevents_recommendation():
    def fake_error_reader(**kwargs):
        return {
            "valid": False,
            "errors": [
                "Task hash is not a failed process."
            ],
        }

    report = recommend_recovery_data(
        run_name="failed-run",
        task_hash="ab/123def",
        results_root=Path("/safe/results"),
        work_root=Path("/safe/work"),
        error_reader=fake_error_reader,
    )

    assert report["valid"] is False
    assert report["category"] is None
    assert report["recommended_action"] is None
    assert report["automatic_execution_allowed"] is False
    assert "not a failed process" in report["errors"][0]