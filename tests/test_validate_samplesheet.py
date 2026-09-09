import csv
import gzip

from agent_tools.validate_samplesheet import (
    validate_samplesheet_data,
)


def create_fastq(path):
    with gzip.open(path, "wt") as handle:
        handle.write("@read1\n")
        handle.write("ACGT\n")
        handle.write("+\n")
        handle.write("IIII\n")


def create_samplesheet(path, fieldnames, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(rows)


def test_valid_samplesheet(tmp_path):
    read1 = tmp_path / "sample01_R1.fastq.gz"
    read2 = tmp_path / "sample01_R2.fastq.gz"

    create_fastq(read1)
    create_fastq(read2)

    samplesheet = tmp_path / "samplesheet.csv"

    create_samplesheet(
        samplesheet,
        ["sample_id", "read1", "read2"],
        [{
            "sample_id": "sample01",
            "read1": str(read1),
            "read2": str(read2),
        }],
    )

    report = validate_samplesheet_data(
        str(samplesheet),
        allowed_root=tmp_path,
    )

    assert report["valid"] is True
    assert report["sample_count"] == 1
    assert report["errors"] == []


def test_missing_column(tmp_path):
    samplesheet = tmp_path / "samplesheet.csv"

    create_samplesheet(
        samplesheet,
        ["sample_id", "read1"],
        [{
            "sample_id": "sample01",
            "read1": "sample01_R1.fastq.gz",
        }],
    )

    report = validate_samplesheet_data(
        str(samplesheet),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "read2" in error
        for error in report["errors"]
    )


def test_missing_fastq(tmp_path):
    samplesheet = tmp_path / "samplesheet.csv"

    create_samplesheet(
        samplesheet,
        ["sample_id", "read1", "read2"],
        [{
            "sample_id": "sample01",
            "read1": "missing_R1.fastq.gz",
            "read2": "missing_R2.fastq.gz",
        }],
    )

    report = validate_samplesheet_data(
        str(samplesheet),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "does not exist" in error
        for error in report["errors"]
    )


def test_duplicate_sample_id(tmp_path):
    read1 = tmp_path / "sample01_R1.fastq.gz"
    read2 = tmp_path / "sample01_R2.fastq.gz"
    read3 = tmp_path / "sample02_R1.fastq.gz"
    read4 = tmp_path / "sample02_R2.fastq.gz"

    for path in (read1, read2, read3, read4):
        create_fastq(path)

    samplesheet = tmp_path / "samplesheet.csv"

    create_samplesheet(
        samplesheet,
        ["sample_id", "read1", "read2"],
        [
            {
                "sample_id": "sample01",
                "read1": str(read1),
                "read2": str(read2),
            },
            {
                "sample_id": "sample01",
                "read1": str(read3),
                "read2": str(read4),
            },
        ],
    )

    report = validate_samplesheet_data(
        str(samplesheet),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "duplicate sample_id" in error
        for error in report["errors"]
    )