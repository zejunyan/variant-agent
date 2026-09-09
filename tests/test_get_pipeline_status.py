import json

from agent_tools.get_pipeline_status import (
    get_pipeline_status_data,
)


def write_audit(
    audit_root,
    results_root,
    run_name="test-run",
    status="completed",
    exit_code=0,
):
    audit_root.mkdir(parents=True, exist_ok=True)

    record = {
        "plan_id": "test-plan",
        "run_name": run_name,
        "workflow": "germline_test",
        "profile": "test",
        "reference_build": "GRCh38",
        "samplesheet": "/test/samplesheet.csv",
        "sample_count": 1,
        "output_directory": str(results_root / run_name),
        "command": ["nextflow", "run", "main.nf"],
        "started_at": "2026-09-09T10:00:00+00:00",
        "completed_at": "2026-09-09T10:05:00+00:00",
        "status": status,
        "exit_code": exit_code,
    }

    (audit_root / f"{run_name}.json").write_text(
        json.dumps(record),
        encoding="utf-8",
    )


def create_expected_outputs(results_root, run_name):
    run_directory = results_root / run_name

    report_directory = run_directory / "report"
    variants_directory = run_directory / "variants"
    evaluation_directory = run_directory / "evaluation"

    report_directory.mkdir(parents=True)
    variants_directory.mkdir(parents=True)
    evaluation_directory.mkdir(parents=True)

    (report_directory / "multiqc_report.html").write_text(
        "report",
        encoding="utf-8",
    )

    (
        variants_directory / "sample.pass.vcf.gz"
    ).write_bytes(b"vcf")

    (
        evaluation_directory
        / "sample.filtered.concordance.tsv"
    ).write_text(
        "type\tTP\tFP\tFN\n",
        encoding="utf-8",
    )


def test_completed_run_with_outputs_is_successful(tmp_path):
    audit_root = tmp_path / "execution_logs"
    results_root = tmp_path / "results" / "agent_runs"

    write_audit(audit_root, results_root)
    create_expected_outputs(results_root, "test-run")

    report = get_pipeline_status_data(
        run_name="test-run",
        audit_root=audit_root,
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["pipeline_status"] == "completed"
    assert report["technical_success"] is True
    assert report["exit_code"] == 0
    assert report["missing_outputs"] == []


def test_completed_run_with_missing_outputs_is_flagged(
    tmp_path,
):
    audit_root = tmp_path / "execution_logs"
    results_root = tmp_path / "results" / "agent_runs"

    write_audit(audit_root, results_root)

    report = get_pipeline_status_data(
        run_name="test-run",
        audit_root=audit_root,
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["pipeline_status"] == (
        "completed_with_missing_outputs"
    )
    assert report["technical_success"] is False
    assert "multiqc_report" in report["missing_outputs"]


def test_failed_run_is_reported(tmp_path):
    audit_root = tmp_path / "execution_logs"
    results_root = tmp_path / "results" / "agent_runs"

    write_audit(
        audit_root,
        results_root,
        status="failed",
        exit_code=1,
    )

    report = get_pipeline_status_data(
        run_name="test-run",
        audit_root=audit_root,
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["pipeline_status"] == "failed"
    assert report["technical_success"] is False
    assert report["exit_code"] == 1


def test_running_state_is_not_called_successful(tmp_path):
    audit_root = tmp_path / "execution_logs"
    results_root = tmp_path / "results" / "agent_runs"

    write_audit(
        audit_root,
        results_root,
        status="running",
        exit_code=None,
    )

    report = get_pipeline_status_data(
        run_name="test-run",
        audit_root=audit_root,
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["pipeline_status"] == "running"
    assert report["technical_success"] is None


def test_missing_audit_record_returns_unknown(tmp_path):
    report = get_pipeline_status_data(
        run_name="missing-run",
        audit_root=tmp_path / "execution_logs",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert report["pipeline_status"] == "unknown"
    assert "No audit record" in report["errors"][0]


def test_unsafe_run_name_is_rejected(tmp_path):
    report = get_pipeline_status_data(
        run_name="../../secret",
        audit_root=tmp_path / "execution_logs",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert report["pipeline_status"] == "unknown"
    assert "Run name must begin" in report["errors"][0]


def test_malformed_audit_record_is_rejected(tmp_path):
    audit_root = tmp_path / "execution_logs"
    audit_root.mkdir()

    (audit_root / "test-run.json").write_text(
        "not valid JSON",
        encoding="utf-8",
    )

    report = get_pipeline_status_data(
        run_name="test-run",
        audit_root=audit_root,
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert "Could not read audit record" in report["errors"][0]