import gzip
from pathlib import Path

import pytest

import agent_tools.pipeline_launcher as launcher


def create_test_environment(tmp_path, monkeypatch):
    project_root = tmp_path
    input_root = project_root / "test_data" / "human_grch38"
    reads = input_root / "reads"
    reference_dir = input_root / "reference"
    truth_dir = input_root / "truth"
    pipeline_dir = project_root / "pipeline"

    reads.mkdir(parents=True)
    reference_dir.mkdir(parents=True)
    truth_dir.mkdir(parents=True)
    pipeline_dir.mkdir(parents=True)

    read1 = reads / "sample_R1.fastq.gz"
    read2 = reads / "sample_R2.fastq.gz"

    fastq_content = (
        "@read1\n"
        "ACGT\n"
        "+\n"
        "IIII\n"
    )

    with gzip.open(read1, "wt") as handle:
        handle.write(fastq_content)

    with gzip.open(read2, "wt") as handle:
        handle.write(fastq_content)

    samplesheet = input_root / "samplesheet.csv"
    samplesheet.write_text(
        "sample_id,read1,read2\n"
        f"sample01,{read1},{read2}\n",
        encoding="utf-8",
    )

    pipeline = pipeline_dir / "main.nf"
    pipeline.write_text(
        "nextflow.enable.dsl = 2\nworkflow {}\n",
        encoding="utf-8",
    )

    reference = reference_dir / "chr20.fa"
    reference.write_text(
        ">chr20\nACGT\n",
        encoding="utf-8",
    )

    Path(f"{reference}.fai").write_text(
        "chr20\t4\t7\t4\t5\n",
        encoding="utf-8",
    )

    truth = truth_dir / "human_test.truth.vcf.gz"
    truth.write_bytes(b"truth")

    Path(f"{truth}.tbi").write_bytes(b"index")

    callable_bed = truth_dir / "human_test.callable.bed"
    callable_bed.write_text(
        "chr20\t0\t4\n",
        encoding="utf-8",
    )

    results_root = project_root / "results" / "agent_runs"
    audit_root = project_root / "execution_logs"

    monkeypatch.setattr(
        launcher,
        "PROJECT_ROOT",
        project_root,
    )
    monkeypatch.setattr(
        launcher,
        "APPROVED_INPUT_ROOT",
        input_root,
    )
    monkeypatch.setattr(
        launcher,
        "RESULTS_ROOT",
        results_root,
    )
    monkeypatch.setattr(
        launcher,
        "AUDIT_ROOT",
        audit_root,
    )
    monkeypatch.setattr(
        launcher,
        "ALLOWED_WORKFLOWS",
        {
            "germline_test": pipeline,
        },
    )
    monkeypatch.setattr(
        launcher,
        "ALLOWED_REFERENCES",
        {
            "GRCh38": {
                "reference": reference,
                "truth": truth,
                "callable": callable_bed,
            }
        },
    )

    return {
        "project_root": project_root,
        "input_root": input_root,
        "samplesheet": samplesheet,
        "results_root": results_root,
        "audit_root": audit_root,
    }


def valid_arguments(environment):
    return {
        "samplesheet": str(environment["samplesheet"]),
        "workflow": "germline_test",
        "profile": "test",
        "reference_build": "GRCh38",
        "run_name": "demo-001",
    }


def test_valid_plan_is_prepared(tmp_path, monkeypatch):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    report = launcher.prepare_pipeline_run_data(
        **valid_arguments(environment)
    )

    assert report["valid"] is True
    assert report["execution_allowed"] is False
    assert report["sample_count"] == 1
    assert report["plan_id"]
    assert report["command"][0:2] == [
        "nextflow",
        "run",
    ]
    assert "--reference" in report["command"]


def test_unknown_workflow_is_rejected(tmp_path, monkeypatch):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    arguments = valid_arguments(environment)
    arguments["workflow"] = "somatic"

    report = launcher.prepare_pipeline_run_data(
        **arguments
    )

    assert report["valid"] is False
    assert "not allowed" in report["errors"][0]


def test_unknown_reference_is_rejected(tmp_path, monkeypatch):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    arguments = valid_arguments(environment)
    arguments["reference_build"] = "hg19"

    report = launcher.prepare_pipeline_run_data(
        **arguments
    )

    assert report["valid"] is False
    assert any(
        "Reference build is not allowed" in error
        for error in report["errors"]
    )


def test_command_injection_run_name_is_rejected(
    tmp_path,
    monkeypatch,
):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    arguments = valid_arguments(environment)
    arguments["run_name"] = "demo;rm-rf"

    report = launcher.prepare_pipeline_run_data(
        **arguments
    )

    assert report["valid"] is False
    assert any(
        "Run name must begin" in error
        for error in report["errors"]
    )


def test_samplesheet_outside_approved_root_is_rejected(
    tmp_path,
    monkeypatch,
):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    outside = tmp_path / "outside.csv"
    outside.write_text(
        "sample_id,read1,read2\n",
        encoding="utf-8",
    )

    arguments = valid_arguments(environment)
    arguments["samplesheet"] = str(outside)

    report = launcher.prepare_pipeline_run_data(
        **arguments
    )

    assert report["valid"] is False
    assert any(
        "outside the approved" in error
        for error in report["errors"]
    )


def test_existing_output_is_not_overwritten(
    tmp_path,
    monkeypatch,
):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    existing_output = (
        environment["results_root"] / "demo-001"
    )
    existing_output.mkdir(parents=True)

    report = launcher.prepare_pipeline_run_data(
        **valid_arguments(environment)
    )

    assert report["valid"] is False
    assert any(
        "already exists" in error
        for error in report["errors"]
    )


def test_execution_requires_matching_approval(
    tmp_path,
    monkeypatch,
):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    report = launcher.execute_pipeline_run_data(
        **valid_arguments(environment),
        approval="wrong-approval",
    )

    assert report["executed"] is False
    assert report["valid"] is False
    assert any(
        "approval" in error.lower()
        for error in report["errors"]
    )


def test_approved_execution_calls_fixed_command(
    tmp_path,
    monkeypatch,
):
    environment = create_test_environment(
        tmp_path,
        monkeypatch,
    )

    arguments = valid_arguments(environment)

    plan = launcher.prepare_pipeline_run_data(
        **arguments
    )

    captured = {}

    class CompletedProcess:
        returncode = 0

    def fake_runner(command, cwd, check):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["check"] = check
        return CompletedProcess()

    report = launcher.execute_pipeline_run_data(
        **arguments,
        approval=f"APPROVE-{plan['plan_id']}",
        runner=fake_runner,
    )

    assert report["executed"] is True
    assert report["exit_code"] == 0
    assert report["status"] == "completed"

    assert captured["command"] == plan["command"]
    assert captured["cwd"] == environment["project_root"]
    assert captured["check"] is False

    audit_path = Path(report["audit_path"])

    assert audit_path.exists()
    assert (
        environment["results_root"] / "demo-001"
    ).exists()