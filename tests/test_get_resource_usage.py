from agent_tools.get_resource_usage import (
    get_resource_usage_data,
    parse_size_to_bytes,
)


TRACE_HEADER = (
    "task_id\thash\tname\tstatus\texit\tduration\t"
    "realtime\t%cpu\tpeak_rss\tpeak_vmem\trchar\twchar\n"
)


def write_trace(results_root, run_name, rows):
    run_directory = results_root / run_name
    run_directory.mkdir(parents=True)

    (
        run_directory / "nextflow_trace.tsv"
    ).write_text(
        TRACE_HEADER + "".join(rows),
        encoding="utf-8",
    )


def test_parse_decimal_memory_units():
    assert parse_size_to_bytes("2 GB") == 2_000_000_000
    assert parse_size_to_bytes("500 MB") == 500_000_000


def test_parse_binary_memory_units():
    assert parse_size_to_bytes("2 GiB") == 2 * 1024**3
    assert parse_size_to_bytes("512 MiB") == 512 * 1024**2


def test_empty_memory_value_returns_none():
    assert parse_size_to_bytes("") is None
    assert parse_size_to_bytes("-") is None
    assert parse_size_to_bytes(None) is None


def test_resource_usage_is_summarized(tmp_path):
    results_root = tmp_path / "results"

    write_trace(
        results_root,
        "test-run",
        [
            (
                "1\taa/111\tFASTQC (sample01)\tCOMPLETED\t0\t"
                "5s\t4s\t120%\t100 MB\t200 MB\t1000\t500\n"
            ),
            (
                "2\tbb/222\tGATK_HAPLOTYPECALLER "
                "(sample01)\tCOMPLETED\t0\t20s\t18s\t180%\t"
                "2 GB\t4 GB\t2000\t1000\n"
            ),
        ],
    )

    report = get_resource_usage_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["process_count"] == 2
    assert report["status_counts"] == {
        "COMPLETED": 2,
    }

    assert report["largest_peak_rss"]["name"] == (
        "GATK_HAPLOTYPECALLER (sample01)"
    )
    assert report["largest_peak_rss"]["peak_rss"] == "2 GB"

    assert report["largest_peak_vmem"]["peak_vmem"] == (
        "4 GB"
    )


def test_failed_process_remains_visible(tmp_path):
    results_root = tmp_path / "results"

    write_trace(
        results_root,
        "test-run",
        [
            (
                "1\taa/111\tSAMTOOLS_SORT (sample01)\t"
                "FAILED\t137\t10s\t9s\t95%\t1 GB\t2 GB\t"
                "1000\t500\n"
            ),
        ],
    )

    report = get_resource_usage_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["status_counts"]["FAILED"] == 1
    assert report["processes"][0]["exit_code"] == "137"
    assert report["processes"][0]["peak_rss"] == "1 GB"


def test_missing_trace_is_reported(tmp_path):
    report = get_resource_usage_data(
        run_name="missing-run",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert "does not exist" in report["errors"][0]


def test_invalid_run_name_is_rejected(tmp_path):
    report = get_resource_usage_data(
        run_name="../../secret",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert "Run name must begin" in report["errors"][0]


def test_trace_missing_required_columns_is_rejected(
    tmp_path,
):
    results_root = tmp_path / "results"
    run_directory = results_root / "test-run"
    run_directory.mkdir(parents=True)

    (
        run_directory / "nextflow_trace.tsv"
    ).write_text(
        "task_id\tpeak_rss\n1\t1 GB\n",
        encoding="utf-8",
    )

    report = get_resource_usage_data(
        run_name="test-run",
        results_root=results_root,
    )

    assert report["valid"] is False
    assert "missing required columns" in report["errors"][0]