from agent_tools.inspect_reference import inspect_reference_data


def create_reference(tmp_path, contig="chr20", length=4):
    reference = tmp_path / "reference.fa"
    reference.write_text(
        f">{contig}\nACGT\n",
        encoding="utf-8",
    )

    fai = tmp_path / "reference.fa.fai"
    fai.write_text(
        f"{contig}\t{length}\t7\t4\t5\n",
        encoding="utf-8",
    )

    return reference


def test_valid_reference(tmp_path):
    reference = create_reference(tmp_path)

    report = inspect_reference_data(
        str(reference),
        allowed_root=tmp_path,
    )

    assert report["valid"] is True
    assert report["contig_count"] == 1
    assert report["has_chr20"] is True
    assert report["total_length"] == 4
    assert report["errors"] == []


def test_missing_reference(tmp_path):
    reference = tmp_path / "missing.fa"

    report = inspect_reference_data(
        str(reference),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "does not exist" in error
        for error in report["errors"]
    )


def test_missing_fasta_index(tmp_path):
    reference = tmp_path / "reference.fa"
    reference.write_text(
        ">chr20\nACGT\n",
        encoding="utf-8",
    )

    report = inspect_reference_data(
        str(reference),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "FASTA index does not exist" in error
        for error in report["errors"]
    )


def test_mismatched_first_contig(tmp_path):
    reference = tmp_path / "reference.fa"
    reference.write_text(
        ">chr20\nACGT\n",
        encoding="utf-8",
    )

    fai = tmp_path / "reference.fa.fai"
    fai.write_text(
        "chr21\t4\t7\t4\t5\n",
        encoding="utf-8",
    )

    report = inspect_reference_data(
        str(reference),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "does not match" in error
        for error in report["errors"]
    )