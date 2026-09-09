process FASTQC {
    tag "${sample_id}"

    container 'quay.io/biocontainers/fastqc:0.12.1--hdfd78af_0'

    publishDir "${params.outdir}/fastqc",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(reads)

    output:
    tuple val(sample_id),
          path("*_fastqc.html"),
          path("*_fastqc.zip"),
          emit: reports

    script:
    """
    fastqc --threads ${task.cpus} ${reads}
    """
}