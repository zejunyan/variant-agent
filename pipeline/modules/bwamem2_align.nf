process BWAMEM2_ALIGN {
    tag "${sample_id}"

    container 'quay.io/biocontainers/bwa-mem2:2.2.1--he70b90d_6'

    publishDir "${params.outdir}/alignment",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(read1), path(read2)
    path reference

    output:
    tuple val(sample_id),
          path("${sample_id}.sam"),
          emit: sam

    script:
    def read_group = "@RG\\tID:${sample_id}\\tSM:${sample_id}\\tPL:ILLUMINA"

    """
    bwa-mem2 index ${reference}

    bwa-mem2 mem \
        -t ${task.cpus} \
        -R '${read_group}' \
        ${reference} \
        ${read1} \
        ${read2} \
        > ${sample_id}.sam
    """
}