process GATK_HAPLOTYPECALLER {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/gatk4-main_gcnvkernel_htslib_samtools:0644b06d5f7121cf'

    publishDir "${params.outdir}/variants",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(bam), path(bai)
    path reference

    output:
    tuple val(sample_id),
          path("${sample_id}.g.vcf.gz"),
          path("${sample_id}.g.vcf.gz.tbi"),
          emit: gvcf

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
        HaplotypeCaller \
        --reference ${reference} \
        --input ${bam} \
        --output ${sample_id}.g.vcf.gz \
        --emit-ref-confidence GVCF \
        --native-pair-hmm-threads ${task.cpus}
    """
}