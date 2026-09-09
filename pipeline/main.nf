nextflow.enable.dsl = 2

include { FASTQC } from './modules/fastqc'
include { FASTP }  from './modules/fastp'
include { BWAMEM2_ALIGN } from './modules/bwamem2_align'
include { SAMTOOLS_SORT } from './modules/samtools_sort'
include { SAMTOOLS_INDEX } from './modules/samtools_index'
include { GATK_MARKDUPLICATES }       from './modules/gatk_markduplicates'
include { SAMTOOLS_ALIGNMENT_METRICS } from './modules/samtools_alignment_metrics'

params.input = null
params.reference = null
params.outdir = 'results'

workflow {
    if (!params.input) {
        error("Please provide a samplesheet using --input")
    }

    if (!params.reference) {
    error("Please provide a reference FASTA using --reference")
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
}