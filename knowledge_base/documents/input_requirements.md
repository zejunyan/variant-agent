---
document_id: input-requirements
title: Pipeline input requirements
document_type: project_documentation
reference_build: GRCh38
status: reviewed
---

# Pipeline input requirements

## Samplesheet

The pipeline requires a CSV samplesheet containing one row per sample.

Each sample must have:

- A non-empty sample identifier
- A readable first FASTQ file
- A readable second FASTQ file
- Paired FASTQ files belonging to the same sample

An incomplete row must be rejected before running the pipeline.

## FASTQ files

The pipeline currently expects paired-end compressed FASTQ files.

Typical filenames are:

- `sample_R1.fastq.gz`
- `sample_R2.fastq.gz`

Both mates must exist and be readable.

## Reference files

The germline pipeline uses a GRCh38-compatible reference FASTA.

The reference normally requires:

- Reference FASTA: `.fa` or `.fasta`
- FASTA index: `.fai`
- Sequence dictionary: `.dict`
- BWA-MEM2 alignment index files

The reference contig names must agree with the BAM, VCF, truth VCF and callable
BED file.

## Truth resources

Pipeline evaluation uses:

- A compressed truth VCF
- A truth VCF index
- A callable-region BED file

Truth resources are used for evaluation. They are not used to train or modify
the variant caller.

## Validation behavior

If required files are missing, unreadable or inconsistent, validation should
fail and report the specific problem. The agent must not invent missing paths,
samples, reference builds or metadata.