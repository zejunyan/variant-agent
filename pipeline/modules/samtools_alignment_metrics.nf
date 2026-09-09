process SAMTOOLS_ALIGNMENT_METRICS {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd'

    publishDir "${params.outdir}/metrics",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(bam), path(bai)

    output:
    tuple val(sample_id),
          path("${sample_id}.marked.flagstat.txt"),
          path("${sample_id}.marked.stats.txt"),
          path("${sample_id}.marked.idxstats.txt"),
          emit: reports

    script:
    """
    samtools flagstat \
        -@ ${task.cpus} \
        ${bam} \
        > ${sample_id}.marked.flagstat.txt

    samtools stats \
        -@ ${task.cpus} \
        ${bam} \
        > ${sample_id}.marked.stats.txt

    samtools idxstats \
        ${bam} \
        > ${sample_id}.marked.idxstats.txt
    """
}