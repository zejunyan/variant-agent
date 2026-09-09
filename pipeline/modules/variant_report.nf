process VARIANT_REPORT {
    tag "${sample_id}"

    container 'multiqc/multiqc:v1.35'

    publishDir "${params.outdir}/report",
        mode: 'copy',
        overwrite: true

    input:
    tuple val(sample_id),
          path(raw_vcf),
          path(raw_index),
          path(filtered_vcf),
          path(filtered_index),
          path(pass_vcf),
          path(pass_index),
          path(raw_concordance),
          path(filtered_concordance)


    output:
        tuple val(sample_id),
        path("${sample_id}.variant_summary.tsv"),
        path("${sample_id}.raw.concordance_summary.tsv"),
        path("${sample_id}.filtered.concordance_summary.tsv"),
        emit: reports
    script:
    """
    python - <<'PY'
    import gzip
    import shutil

    sample_id = "${sample_id}"
    raw_vcf = "${raw_vcf}"
    filtered_vcf = "${filtered_vcf}"
    pass_vcf = "${pass_vcf}"
    raw_concordance = "${raw_concordance}"
    filtered_concordance = "${filtered_concordance}"

    def read_variants(path):
        records = []

        with gzip.open(path, "rt") as handle:
            for line in handle:
                if line.startswith("#"):
                    continue

                fields = line.rstrip().split("\\t")

                records.append({
                    "chrom": fields[0],
                    "position": fields[1],
                    "ref": fields[3],
                    "alt": fields[4],
                    "filter": fields[6],
                })

        return records

    def variant_type(record):
        alternate_alleles = record["alt"].split(",")

        if len(record["ref"]) == 1 and all(
            len(alt) == 1 for alt in alternate_alleles
        ):
            return "SNP"

        return "INDEL_OR_COMPLEX"

    raw_records = read_variants(raw_vcf)
    filtered_records = read_variants(filtered_vcf)
    pass_records = read_variants(pass_vcf)

    raw_snps = sum(
        variant_type(record) == "SNP"
        for record in raw_records
    )

    raw_indels = sum(
        variant_type(record) == "INDEL_OR_COMPLEX"
        for record in raw_records
    )

    failed_records = sum(
        record["filter"] not in {"PASS", "."}
        for record in filtered_records
    )

    summary_path = f"{sample_id}.variant_summary.tsv"

    with open(summary_path, "w") as handle:
        handle.write("sample_id\\tmetric\\tvalue\\n")
        handle.write(
            f"{sample_id}\\traw_variants\\t{len(raw_records)}\\n"
        )
        handle.write(
            f"{sample_id}\\traw_snps\\t{raw_snps}\\n"
        )
        handle.write(
            f"{sample_id}\\traw_indels_or_complex\\t{raw_indels}\\n"
        )
        handle.write(
            f"{sample_id}\\tfilter_failed\\t{failed_records}\\n"
        )
        handle.write(
            f"{sample_id}\\tpass_variants\\t{len(pass_records)}\\n"
        )

    shutil.copyfile(
    raw_concordance,
    f"{sample_id}.raw.concordance_summary.tsv",
    )

    shutil.copyfile(
    filtered_concordance,
    f"{sample_id}.filtered.concordance_summary.tsv",
    )
    PY
    """
}