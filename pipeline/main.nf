nextflow.enable.dsl = 2

include { FASTQC } from './modules/fastqc'
include { FASTP }  from './modules/fastp'
include { BWAMEM2_ALIGN } from './modules/bwamem2_align'
include { SAMTOOLS_SORT } from './modules/samtools_sort'
include { SAMTOOLS_INDEX } from './modules/samtools_index'
include { GATK_MARKDUPLICATES }       from './modules/gatk_markduplicates'
include { SAMTOOLS_ALIGNMENT_METRICS } from './modules/samtools_alignment_metrics'
include { GATK_HAPLOTYPECALLER } from './modules/gatk_haplotypecaller'
include { GATK_GENOTYPEGVCFS } from './modules/gatk_genotypegvcfs'
include {GATK_CONCORDANCE as GATK_RAW_CONCORDANCE} from './modules/gatk_concordance'
include {GATK_CONCORDANCE as GATK_FILTERED_CONCORDANCE} from './modules/gatk_concordance'
include { GATK_VARIANT_FILTERING } from './modules/gatk_variant_filtering'
include { VARIANT_REPORT } from './modules/variant_report'
include { MULTIQC } from './modules/multiqc'

params.input = null
params.reference = null
params.truth = null
params.callable = null
params.outdir = 'results'

workflow {
    if (!params.input) {
        error("Please provide a samplesheet using --input")
    }

    if (!params.reference) {
        error("Please provide a reference FASTA using --reference")
    }

    if (!params.truth) {
        error("Please provide a truth VCF using --truth")
    }

    if (!params.callable) {
        error("Please provide a callable BED using --callable")
    }

    samples_ch = Channel
        .fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true)
        .map { row ->
            if (!row.sample_id || !row.read1 || !row.read2) {
                error("Samplesheet contains an incomplete row: ${row}")
            }

            def read1 = file(row.read1, checkIfExists: true)
            def read2 = file(row.read2, checkIfExists: true)

            tuple(row.sample_id, [read1, read2])
        }


    /*
     * Raw-read quality reports
     */
    FASTQC(samples_ch)

    /*
     * Adapter and quality trimming
     */
    FASTP(samples_ch)
    
    /*
     * Later:
     * ALIGN(FASTP.out.reads)
     */

    reference_ch = Channel.fromPath(
        params.reference,
        checkIfExists: true)
    
    truth_vcf_ch = Channel.fromPath(
    params.truth,
    checkIfExists: true
    )

    truth_index_ch = Channel.fromPath(
        "${params.truth}.tbi",
        checkIfExists: true
    )

    callable_bed_ch = Channel.fromPath(
        params.callable,
        checkIfExists: true
    )

    BWAMEM2_ALIGN(
        FASTP.out.reads,
        reference_ch)
    
    SAMTOOLS_SORT(
        BWAMEM2_ALIGN.out.sam)

    GATK_MARKDUPLICATES(
        SAMTOOLS_SORT.out.bam)

    SAMTOOLS_INDEX(
        GATK_MARKDUPLICATES.out.bam)

    SAMTOOLS_ALIGNMENT_METRICS(
        SAMTOOLS_INDEX.out.bam_bai)

    GATK_HAPLOTYPECALLER(
        SAMTOOLS_INDEX.out.bam_bai,
        reference_ch)

    GATK_GENOTYPEGVCFS(
        GATK_HAPLOTYPECALLER.out.gvcf,
        reference_ch)


        /*
    * Hard-filter the raw variants
    */
    GATK_VARIANT_FILTERING(
        GATK_GENOTYPEGVCFS.out.vcf
    )

    /*
    * Label the raw VCF for raw concordance
    */
    raw_evaluation_ch = GATK_GENOTYPEGVCFS.out.vcf.map {
        sample_id, vcf, index ->

        tuple(sample_id, "raw", vcf, index)
    }

    /*
    * Label the PASS VCF for filtered concordance
    */
    filtered_evaluation_ch = GATK_VARIANT_FILTERING.out.pass_vcf.map {
        sample_id, vcf, index ->

        tuple(sample_id, "filtered", vcf, index)
    }

    /*
    * Compare the raw VCF with truth
    */
    GATK_RAW_CONCORDANCE(
        raw_evaluation_ch,
        truth_vcf_ch,
        truth_index_ch,
        callable_bed_ch,
        reference_ch
    )

    /*
    * Compare the filtered PASS VCF with truth
    */
    GATK_FILTERED_CONCORDANCE(
        filtered_evaluation_ch,
        truth_vcf_ch,
        truth_index_ch,
        callable_bed_ch,
        reference_ch
    )

    variant_report_ch = GATK_GENOTYPEGVCFS.out.vcf
        .join(GATK_VARIANT_FILTERING.out.filtered_vcf)
        .join(GATK_VARIANT_FILTERING.out.pass_vcf)
        .join(GATK_RAW_CONCORDANCE.out.summary)
        .join(GATK_FILTERED_CONCORDANCE.out.summary)

    VARIANT_REPORT(variant_report_ch)


    multiqc_inputs_ch = FASTQC.out.reports
        .mix(
            FASTP.out.reports,
            GATK_MARKDUPLICATES.out.metrics,
            SAMTOOLS_ALIGNMENT_METRICS.out.reports
        )
        .map { record -> record.drop(1) }
        .flatten()
        .collect()

    MULTIQC(multiqc_inputs_ch)
}