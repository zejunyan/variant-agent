from agent_tools.read_process_error import (
    read_process_error_data,
)


TRACE_HEADER = (
    "task_id\thash\tnative_id\tname\tstatus\texit\t"
    "duration\trealtime\tpeak_rss\tpeak_vmem\n"
)


def create_failed_task(
    results_root,
    work_root,
    run_name="failed-run",
    task_hash="ab/123def",
    error_text="The process failed.",
):
    result_directory = results_root / run_name
    result_directory.mkdir(parents=True)

    trace = result_directory / "nextflow_trace.tsv"
    trace.write_text(
        TRACE_HEADER
        + (
            f"1\t{task_hash}\t100\t"
            "GATK_HAPLOTYPECALLER (sample01)\t"
            "FAILED\t1\t20s\t18s\t2 GB\t4 GB\n"
        ),
        encoding="utf-8",
    )

    hash_prefix, task_prefix = task_hash.split("/", 1)

    task_directory = (
        work_root
        / run_name
        / hash_prefix
        / f"{task_prefix}7890"
    )
    task_directory.mkdir(parents=True)

    (task_directory / ".command.err").write_text(
        error_text,
        encoding="utf-8",
    )

    return task_directory


def test_reads_failed_process_error(tmp_path):
    results_root = tmp_path / "results"
    work_root = tmp_path / "work"

    task_directory = create_failed_task(
        results_root,
        work_root,
    )

    report = read_process_error_data(
        run_name="failed-run",
        task_hash="ab/123def",
        results_root=results_root,
        work_root=work_root,
    )

    assert report["valid"] is True
    assert report["process_name"] == (
        "GATK_HAPLOTYPECALLER (sample01)"
    )
    assert report["status"] == "FAILED"
    assert report["exit_code"] == 1
    assert report["error_text"] == "The process failed."
    assert report["task_directory"] == str(
        task_directory.resolve()
    )


def test_error_output_is_truncated_from_the_end(tmp_path):
    results_root = tmp_path / "results"
    work_root = tmp_path / "work"

    error_text = ("beginning-" * 100) + ("final-error-" * 30)

    create_failed_task(
        results_root,
        work_root,
        error_text=error_text,
    )

    report = read_process_error_data(
        run_name="failed-run",
        task_hash="ab/123def",
        max_characters=200,
        results_root=results_root,
        work_root=work_root,
    )

    assert report["valid"] is True
    assert report["truncated"] is True
    assert len(report["error_text"]) <= 200
    assert report["error_text"].endswith("final-error-")


def test_nonfailed_hash_is_rejected(tmp_path):
    results_root = tmp_path / "results"
    work_root = tmp_path / "work"

    create_failed_task(
        results_root,
        work_root,
    )

    report = read_process_error_data(
        run_name="failed-run",
        task_hash="cd/987abc",
        results_root=results_root,
        work_root=work_root,
    )

    assert report["valid"] is False
    assert "not listed as a failed process" in (
        report["errors"][0]
    )


def test_missing_error_file_is_reported(tmp_path):
    results_root = tmp_path / "results"
    work_root = tmp_path / "work"

    task_directory = create_failed_task(
        results_root,
        work_root,
    )

    (task_directory / ".command.err").unlink()

    report = read_process_error_data(
        run_name="failed-run",
        task_hash="ab/123def",
        results_root=results_root,
        work_root=work_root,
    )

    assert report["valid"] is False
    assert "does not exist" in report["errors"][0]


def test_invalid_task_hash_is_rejected(tmp_path):
    report = read_process_error_data(
        run_name="failed-run",
        task_hash="../../secret",
        results_root=tmp_path / "results",
        work_root=tmp_path / "work",
    )

    assert report["valid"] is False
    assert "Nextflow format" in report["errors"][0]


def test_invalid_character_limit_is_rejected(tmp_path):
    report = read_process_error_data(
        run_name="failed-run",
        task_hash="ab/123def",
        max_characters=50,
        results_root=tmp_path / "results",
        work_root=tmp_path / "work",
    )

    assert report["valid"] is False
    assert "max_characters must be between" in (
        report["errors"][0]
    )