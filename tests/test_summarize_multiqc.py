from agent_tools.summarize_multiqc import (
    summarize_multiqc_data,
)


def create_multiqc_data(tmp_path):
    data_directory = tmp_path / "multiqc_report_data"
    data_directory.mkdir()

    general_stats = (
        data_directory / "multiqc_general_stats.txt"
    )

    general_stats.write_text(
        "Sample\tmapped_percent\tduplicate_percent\n"
        "human_test.marked\t100.0\t4.92\n"
        "human_test_R1\t\t4.45\n",
        encoding="utf-8",
    )

    versions = (
        data_directory / "multiqc_software_versions.txt"
    )

    versions.write_text(
        "Sample\tSamtools\tFastQC\n"
        "Samtools\t1.24\t\n"
        "FastQC\t\t0.12.1\n",
        encoding="utf-8",
    )

    return data_directory


def test_valid_multiqc_summary(tmp_path):
    data_directory = create_multiqc_data(tmp_path)

    report = summarize_multiqc_data(
        str(data_directory),
        expected_sample="human_test",
        allowed_root=tmp_path,
    )

    assert report["valid"] is True
    assert "human_test.marked" in report["matched_rows"]

    assert (
        report["metrics"]["human_test.marked"][
            "mapped_percent"
        ]
        == 100
    )

    assert (
        report["metrics"]["human_test.marked"][
            "duplicate_percent"
        ]
        == 4.92
    )

    assert report["software_versions"]["Samtools"][
        "Samtools"
    ] == "1.24"


def test_parent_report_directory_is_accepted(tmp_path):
    create_multiqc_data(tmp_path)

    report = summarize_multiqc_data(
        str(tmp_path),
        expected_sample="human_test",
        allowed_root=tmp_path,
    )

    assert report["valid"] is True
    assert report["data_directory"].endswith(
        "multiqc_report_data"
    )


def test_missing_multiqc_directory(tmp_path):
    report = summarize_multiqc_data(
        str(tmp_path / "missing"),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "does not exist" in error
        for error in report["errors"]
    )


def test_missing_general_statistics(tmp_path):
    empty_directory = tmp_path / "empty"
    empty_directory.mkdir()

    report = summarize_multiqc_data(
        str(empty_directory),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "Could not find" in error
        for error in report["errors"]
    )


def test_missing_expected_sample(tmp_path):
    data_directory = create_multiqc_data(tmp_path)

    report = summarize_multiqc_data(
        str(data_directory),
        expected_sample="missing_sample",
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "No MultiQC rows matched" in error
        for error in report["errors"]
    )