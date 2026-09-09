process MULTIQC {
    tag "final-report"

    container 'multiqc/multiqc:v1.35'

    publishDir "${params.outdir}/report",
        mode: 'copy',
        overwrite: true

    input:
    path report_files

    output:
    path "multiqc_report.html",
        emit: html

    path "multiqc_report_data",
        emit: data

    script:
    """
    multiqc . \
        --force \
        --filename multiqc_report.html \
        --outdir .
    """
}