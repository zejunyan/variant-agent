process FASTP {
    tag "${sample_id}"

    container 'community.wave.seqera.io/library/fastp:1.1.0--08aa7c5662a30d57'

    publishDir "${params.outdir}/fastp",
        mode: 'copy',
        overwrite: false

    input:
    tuple val(sample_id), path(reads)

    output:
    tuple val(sample_id),
          path("${sample_id}_R1.trimmed.fastq.gz"),
          path("${sample_id}_R2.trimmed.fastq.gz"),
          emit: reads

    tuple val(sample_id),
          path("${sample_id}.fastp.html"),
          path("${sample_id}.fastp.json"),
          emit: reports

    script:
    def read1 = reads[0]
    def read2 = reads[1]

    """
    fastp \
        --in1 ${read1} \
        --in2 ${read2} \
        --out1 ${sample_id}_R1.trimmed.fastq.gz \
        --out2 ${sample_id}_R2.trimmed.fastq.gz \
        --html ${sample_id}.fastp.html \
        --json ${sample_id}.fastp.json \
        --thread ${task.cpus} \
        --detect_adapter_for_pe
    """
}