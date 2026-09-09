process SAMTOOLS_SORT {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd'

    input:
    tuple val(sample_id), path(sam)

    output:
    tuple val(sample_id),
          path("${sample_id}.sorted.bam"),
          emit: bam

    script:
    """
    samtools sort \
        --threads ${task.cpus} \
        -o ${sample_id}.sorted.bam \
        ${sam}
    """
}