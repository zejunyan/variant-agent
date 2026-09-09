nextflow.enable.dsl = 2

include { FASTQC } from './modules/fastqc'
include { FASTP }  from './modules/fastp'

params.input = null
params.outdir = 'results'

workflow {
    if (!params.input) {
        error("Please provide a samplesheet using --input")
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
}