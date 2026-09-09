nextflow.enable.dsl = 2

include { FASTQC } from './modules/fastqc'

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
            def read1 = file(row.read1, checkIfExists: true)
            def read2 = file(row.read2, checkIfExists: true)

            tuple(row.sample_id, [read1, read2])
        }

    FASTQC(samples_ch)
}