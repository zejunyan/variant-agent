process SAMTOOLS_INDEX {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd'

    publishDir "${params.outdir}/alignment",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(bam)

    output:
    tuple val(sample_id),
          path(bam),
          path("${bam}.bai"),
          emit: bam_bai

    script:
    """
    samtools index \
        -@ ${task.cpus} \
        ${bam}
    """
}