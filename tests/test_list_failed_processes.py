from agent_tools.list_failed_processes import (
    list_failed_processes_data,
)


TRACE_HEADER = (
    "task_id\thash\tnative_id\tname\tstatus\texit\t"
    "duration\trealtime\tpeak_rss\tpeak_vmem\n"
)


def write_trace(
    results_root,
    run_name,
    rows,
):
    run_directory = results_root / run_name
    run_directory.mkdir(parents=True)

    trace_path = run_directory / "nextflow_trace.tsv"
    trace_path.write_text(
        TRACE_HEADER + "".join(rows),
        encoding="utf-8",
    )

    return trace_path


def test_failed_process_is_returned(tmp_path):
    results_root = tmp_path / "results"

    write_trace(
        results_root,
        "test-run",
        [
            (
                "1\taa/111\t100\tFASTQC (sample01)\t"
                "COMPLETED\t0\t5s\t4s\t100 MB\t200 MB\n"
            ),
            (
                "2\tbb/222\t101\tGATK_HAPLOTYPECALLER "
                "(sample01)\tFAILED\t1\t20s\t18s\t"
                "2 GB\t4 GB\n"
            ),
        ],
    )

    report = list_failed_processes_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["process_count"] == 2
    assert report["failed_count"] == 1

    failed = report["failed_processes"][0]

    assert failed["name"] == (
        "GATK_HAPLOTYPECALLER (sample01)"
    )
    assert failed["status"] == "FAILED"
    assert failed["exit_code"] == 1
    assert failed["hash"] == "bb/222"
    assert failed["peak_rss"] == "2 GB"


def test_nonzero_exit_is_treated_as_failure(tmp_path):
    results_root = tmp_path / "results"

    write_trace(
        results_root,
        "test-run",
        [
            (
                "1\taa/111\t100\tSAMTOOLS_SORT "
                "(sample01)\tCOMPLETED\t137\t10s\t9s\t"
                "1 GB\t2 GB\n"
            ),
        ],
    )

    report = list_failed_processes_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["failed_count"] == 1
    assert (
        report["failed_processes"][0]["exit_code"]
        == 137
    )


def test_completed_trace_has_no_failures(tmp_path):
    results_root = tmp_path / "results"

    write_trace(
        results_root,
        "test-run",
        [
            (
                "1\taa/111\t100\tFASTQC (sample01)\t"
                "COMPLETED\t0\t5s\t4s\t100 MB\t200 MB\n"
            ),
        ],
    )

    report = list_failed_processes_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["failed_count"] == 0
    assert report["failed_processes"] == []
    assert report["warnings"]


def test_missing_trace_is_reported(tmp_path):
    report = list_failed_processes_data(
        run_name="missing-run",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert report["failed_count"] == 0
    assert "does not exist" in report["errors"][0]


def test_missing_required_column_is_rejected(tmp_path):
    results_root = tmp_path / "results"
    run_directory = results_root / "test-run"
    run_directory.mkdir(parents=True)

    (
        run_directory / "nextflow_trace.tsv"
    ).write_text(
        "task_id\tname\texit\n"
        "1\tFASTQC (sample01)\t0\n",
        encoding="utf-8",
    )

    report = list_failed_processes_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["valid"] is False
    assert "missing required columns" in report["errors"][0]


def test_unsafe_run_name_is_rejected(tmp_path):
    report = list_failed_processes_data(
        run_name="../../secret",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert "Run name must begin" in report["errors"][0]