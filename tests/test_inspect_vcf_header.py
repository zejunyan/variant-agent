import gzip

from agent_tools.inspect_vcf_header import (
    inspect_vcf_header_data,
)


VALID_HEADER = """##fileformat=VCFv4.2
##reference=chr20.fa
##source=HaplotypeCaller
##contig=<ID=chr20,length=64444167>
##FILTER=<ID=PASS,Description="All filters passed">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\thuman_test
"""


def create_compressed_vcf(path, header=VALID_HEADER):
    with gzip.open(path, "wt") as handle:
        handle.write(header)
        handle.write(
            "chr20\t10001\t.\tA\tG\t100\tPASS\t.\tGT\t0/1\n"
        )


def test_valid_compressed_vcf(tmp_path):
    vcf = tmp_path / "test.vcf.gz"
    create_compressed_vcf(vcf)

    index = tmp_path / "test.vcf.gz.tbi"
    index.write_bytes(b"test-index")

    report = inspect_vcf_header_data(
        str(vcf),
        expected_sample="human_test",
        expected_contig="chr20",
        allowed_root=tmp_path,
    )

    assert report["valid"] is True
    assert report["fileformat"] == "VCFv4.2"
    assert report["samples"] == ["human_test"]
    assert report["expected_sample_present"] is True
    assert report["expected_contig_present"] is True
    assert report["index_exists"] is True


def test_missing_vcf(tmp_path):
    report = inspect_vcf_header_data(
        str(tmp_path / "missing.vcf.gz"),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "does not exist" in error
        for error in report["errors"]
    )


def test_missing_column_header(tmp_path):
    vcf = tmp_path / "invalid.vcf"

    vcf.write_text(
        "##fileformat=VCFv4.2\n"
        "##contig=<ID=chr20,length=64444167>\n",
        encoding="utf-8",
    )

    report = inspect_vcf_header_data(
        str(vcf),
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "#CHROM" in error
        for error in report["errors"]
    )


def test_missing_expected_sample(tmp_path):
    vcf = tmp_path / "test.vcf.gz"
    create_compressed_vcf(vcf)

    report = inspect_vcf_header_data(
        str(vcf),
        expected_sample="missing_sample",
        expected_contig="chr20",
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "Expected sample is absent" in error
        for error in report["errors"]
    )


def test_missing_expected_contig(tmp_path):
    vcf = tmp_path / "test.vcf.gz"
    create_compressed_vcf(vcf)

    report = inspect_vcf_header_data(
        str(vcf),
        expected_sample="human_test",
        expected_contig="chr21",
        allowed_root=tmp_path,
    )

    assert report["valid"] is False
    assert any(
        "Expected contig is absent" in error
        for error in report["errors"]
    )