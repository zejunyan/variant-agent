process GATK_VARIANT_FILTERING {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/gatk4-main_gcnvkernel_htslib_samtools:0644b06d5f7121cf'

    publishDir "${params.outdir}/variants",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(raw_vcf), path(raw_vcf_index)

    output:
    tuple val(sample_id),
          path("${sample_id}.filtered.vcf.gz"),
          path("${sample_id}.filtered.vcf.gz.tbi"),
          emit: filtered_vcf

    tuple val(sample_id),
          path("${sample_id}.pass.vcf.gz"),
          path("${sample_id}.pass.vcf.gz.tbi"),
          emit: pass_vcf

    script:
    def java_memory_mb = (task.memory.mega * 0.8).intValue()

    """
    gatk --java-options "-Xmx${java_memory_mb}M -XX:-UsePerfData" \
        VariantFiltration \
        --variant ${raw_vcf} \
        --output ${sample_id}.filtered.vcf.gz \
        --filter-expression "QD < 2.0" \
        --filter-name "QD2" \
        --filter-expression "QUAL < 30.0" \
        --filter-name "QUAL30" \
        --filter-expression "SOR > 3.0" \
        --filter-name "SOR3" \
        --filter-expression "FS > 60.0" \
        --filter-name "FS60" \
        --filter-expression "MQ < 40.0" \
        --filter-name "MQ40" \
        --filter-expression "MQRankSum < -12.5" \
        --filter-name "MQRankSum-12.5" \
        --filter-expression "ReadPosRankSum < -8.0" \
        --filter-name "ReadPosRankSum-8"

    gatk --java-options "-Xmx${java_memory_mb}M -XX:-UsePerfData" \
        SelectVariants \
        --variant ${sample_id}.filtered.vcf.gz \
        --exclude-filtered true \
        --output ${sample_id}.pass.vcf.gz
    """
}