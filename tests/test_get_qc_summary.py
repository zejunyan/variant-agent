from agent_tools.get_qc_summary import (
    get_qc_summary_data,
    read_concordance_file,
)


def create_multiqc(run_directory):
    data_directory = (
        run_directory
        / "report"
        / "multiqc_report_data"
    )
    data_directory.mkdir(parents=True)

    (
        data_directory / "multiqc_general_stats.txt"
    ).write_text(
        "Sample\tpercent_duplicates\tmapped_passed\n"
        "human_test\t0.0\t198\n",
        encoding="utf-8",
    )

    (
        data_directory / "multiqc_software_versions.txt"
    ).write_text(
        "Sample\tSamtools\tFastQC\n"
        "human_test\t1.21\t0.12.1\n",
        encoding="utf-8",
    )


def create_concordance(
    run_directory,
    stage,
    content=None,
):
    evaluation_directory = (
        run_directory / "evaluation"
    )
    evaluation_directory.mkdir(parents=True, exist_ok=True)

    if content is None:
        content = (
            "type\tTP\tFP\tFN\tRECALL\tPRECISION\n"
            "SNP\t10\t0\t0\t1.0\t1.0\n"
            "INDEL\t0\t0\t0\t0.0\t0.0\n"
        )

    path = (
        evaluation_directory
        / f"human_test.{stage}.concordance.tsv"
    )

    path.write_text(content, encoding="utf-8")
    return path


def create_complete_run(results_root):
    run_directory = results_root / "test-run"
    run_directory.mkdir(parents=True)

    create_multiqc(run_directory)
    create_concordance(run_directory, "raw")
    create_concordance(run_directory, "filtered")

    return run_directory


def test_complete_qc_summary_is_valid(tmp_path):
    results_root = tmp_path / "results"
    create_complete_run(results_root)

    report = get_qc_summary_data(
        run_name="test-run",
        expected_sample="human_test",
        results_root=results_root,
    )

    assert report["valid"] is True
    assert report["qc_decision"] == "not_evaluated"
    assert report["errors"] == []

    assert report["multiqc"]["valid"] is True
    assert report["multiqc"]["matched_rows"] == [
        "human_test"
    ]

    raw_rows = (
        report["concordance"]["raw"][0]["rows"]
    )

    assert raw_rows[0] == {
        "type": "SNP",
        "true_positives": 10,
        "false_positives": 0,
        "false_negatives": 0,
        "recall": 1.0,
        "precision": 1.0,
    }

    filtered_rows = (
        report["concordance"]["filtered"][0]["rows"]
    )

    assert filtered_rows[0]["precision"] == 1.0


def test_missing_filtered_concordance_is_reported(
    tmp_path,
):
    results_root = tmp_path / "results"
    run_directory = results_root / "test-run"
    run_directory.mkdir(parents=True)

    create_multiqc(run_directory)
    create_concordance(run_directory, "raw")

    report = get_qc_summary_data(
        run_name="test-run",
        expected_sample="human_test",
        results_root=results_root,
    )

    assert report["valid"] is False
    assert any(
        "No filtered concordance" in error
        for error in report["errors"]
    )


def test_malformed_concordance_is_rejected(tmp_path):
    results_root = tmp_path / "results"
    run_directory = results_root / "test-run"
    run_directory.mkdir(parents=True)

    create_multiqc(run_directory)

    create_concordance(
        run_directory,
        "raw",
        content=(
            "type\tTP\tFP\n"
            "SNP\t10\t0\n"
        ),
    )

    create_concordance(run_directory, "filtered")

    report = get_qc_summary_data(
        run_name="test-run",
        expected_sample="human_test",
        results_root=results_root,
    )

    assert report["valid"] is False
    assert any(
        "missing required columns" in error
        for error in report["errors"]
    )


def test_invalid_numeric_value_is_reported(tmp_path):
    results_root = tmp_path / "results"
    run_directory = results_root / "test-run"
    run_directory.mkdir(parents=True)

    path = create_concordance(
        run_directory,
        "raw",
        content=(
            "type\tTP\tFP\tFN\tRECALL\tPRECISION\n"
            "SNP\tten\t0\t0\t1.0\t1.0\n"
        ),
    )

    result = read_concordance_file(
        path=path,
        allowed_root=run_directory,
    )

    assert result["valid"] is False
    assert any(
        "Invalid integer in TP" in error
        for error in result["errors"]
    )


def test_missing_run_directory_is_reported(tmp_path):
    report = get_qc_summary_data(
        run_name="missing-run",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert "does not exist" in report["errors"][0]


def test_unsafe_run_name_is_rejected(tmp_path):
    report = get_qc_summary_data(
        run_name="../../secret",
        results_root=tmp_path / "results",
    )

    assert report["valid"] is False
    assert "Run name must begin" in report["errors"][0]


def test_unsafe_sample_name_is_rejected(tmp_path):
    results_root = tmp_path / "results"
    create_complete_run(results_root)

    report = get_qc_summary_data(
        run_name="test-run",
        expected_sample="../../secret",
        results_root=results_root,
    )

    assert report["valid"] is False
    assert "unsupported characters" in report["errors"][0]