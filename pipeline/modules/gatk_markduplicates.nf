process GATK_MARKDUPLICATES {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/gatk4-main_gcnvkernel_htslib_samtools:0644b06d5f7121cf'

    publishDir "${params.outdir}/metrics",
        mode: 'copy',
        pattern: '*.markduplicates.metrics.txt',
        overwrite: false

    input:
    tuple val(sample_id), path(bam)

    output:
    tuple val(sample_id),
          path("${sample_id}.marked.bam"),
          emit: bam

    tuple val(sample_id),
          path("${sample_id}.markduplicates.metrics.txt"),
          emit: metrics

    script:
    def java_memory_mb = (task.memory.mega * 0.8).intValue()

    """
    gatk --java-options "-Xmx${java_memory_mb}M -XX:-UsePerfData" \
        MarkDuplicates \
        --INPUT ${bam} \
        --OUTPUT ${sample_id}.marked.bam \
        --METRICS_FILE ${sample_id}.markduplicates.metrics.txt \
        --ASSUME_SORT_ORDER coordinate \
        --REMOVE_DUPLICATES false \
        --VALIDATION_STRINGENCY STRICT \
        --TMP_DIR .
    """
}