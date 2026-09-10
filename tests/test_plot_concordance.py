from pathlib import Path

from agent_tools.plot_concordance import plot_concordance_data


def create_run(root, counts="10\t0\t0"):
    evaluation = root / "test-run" / "evaluation"
    evaluation.mkdir(parents=True)

    content = (
        "type\tTP\tFP\tFN\tRECALL\tPRECISION\n"
        f"SNP\t{counts}\t1.0\t1.0\n"
        "INDEL\t0\t0\t0\t0.0\t0.0\n"
    )

    for stage in ("raw", "filtered"):
        (evaluation / f"sample01.{stage}.concordance.tsv").write_text(
            content, encoding="utf-8"
        )

    return evaluation


def test_creates_png_and_preserves_sources(tmp_path):
    evaluation = create_run(tmp_path)
    before = {
        path.name: path.read_bytes()
        for path in evaluation.iterdir()
    }

    report = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )

    assert report["valid"] is True
    output = Path(report["plot_path"])
    assert output.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert output.parent == tmp_path / "test-run" / "plots"
    assert report["metrics"]["raw"]["SNP"]["precision"] == 1.0

    after = {
        path.name: path.read_bytes()
        for path in evaluation.iterdir()
    }
    assert before == after


def test_zero_denominator_is_undefined(tmp_path):
    create_run(tmp_path)

    report = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )

    assert report["valid"] is True
    assert report["metrics"]["raw"]["INDEL"]["precision"] is None
    assert report["metrics"]["raw"]["INDEL"]["recall"] is None
    assert report["warnings"]


def test_missing_filtered_file_is_rejected(tmp_path):
    evaluation = create_run(tmp_path)
    (evaluation / "sample01.filtered.concordance.tsv").unlink()

    report = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )

    assert report["valid"] is False
    assert report["plot_path"] is None


def test_negative_counts_are_rejected(tmp_path):
    create_run(tmp_path, counts="-1\t0\t0")

    report = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )

    assert report["valid"] is False
    assert "negative" in report["errors"][0]


def test_unsafe_run_is_rejected(tmp_path):
    report = plot_concordance_data(
        "../../outside", "sample01", results_root=tmp_path
    )

    assert report["valid"] is False


def test_plot_directory_cannot_escape_run(tmp_path):
    create_run(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()

    (tmp_path / "test-run" / "plots").symlink_to(
        outside, target_is_directory=True
    )

    report = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )

    assert report["valid"] is False
    assert list(outside.iterdir()) == []


def test_repeated_calls_preserve_previous_plot(tmp_path):
    create_run(tmp_path)

    first = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )
    second = plot_concordance_data(
        "test-run", "sample01", results_root=tmp_path
    )

    assert first["valid"] and second["valid"]
    assert first["plot_path"] != second["plot_path"]
    assert Path(first["plot_path"]).exists()