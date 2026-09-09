process GATK_CONCORDANCE {
    tag "${sample_id}:${comparison}"

    container 'community.wave.seqera.io/library/gatk4-main_gcnvkernel_htslib_samtools:0644b06d5f7121cf'

    publishDir "${params.outdir}/evaluation",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id),
          val(comparison),
          path(evaluation_vcf),
          path(evaluation_index)

    path truth_vcf
    path truth_index
    path callable_bed
    path reference

    output:
    tuple val(sample_id),
          path("${sample_id}.${comparison}.concordance.tsv"),
          emit: summary

    path "${sample_id}.${comparison}.truth-status.vcf.gz",
        emit: truth_status

    path "${sample_id}.${comparison}.evaluation-status.vcf.gz",
        emit: evaluation_status

    script:
    def java_memory_mb = (task.memory.mega * 0.8).intValue()
    def reference_dict = "${reference.baseName}.dict"

    """
    samtools faidx ${reference}

    gatk --java-options "-Xmx${java_memory_mb}M -XX:-UsePerfData" \
        CreateSequenceDictionary \
        --REFERENCE ${reference} \
        --OUTPUT ${reference_dict}

    gatk --java-options "-Xmx${java_memory_mb}M -XX:-UsePerfData" \
        Concordance \
        --reference ${reference} \
        --evaluation ${evaluation_vcf} \
        --truth ${truth_vcf} \
        --intervals ${callable_bed} \
        --summary ${sample_id}.${comparison}.concordance.tsv \
        --true-positives-and-false-negatives \
            ${sample_id}.${comparison}.truth-status.vcf.gz \
        --true-positives-and-false-positives \
            ${sample_id}.${comparison}.evaluation-status.vcf.gz
    """
}