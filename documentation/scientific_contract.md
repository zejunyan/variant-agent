# Germline WES Pipeline Scientific Contract

## Purpose

This pipeline performs technical germline small-variant calling from
paired-end WES FASTQ files. It is a learning workflow and is not
validated for clinical use.

## Accepted inputs

- Paired-end compressed FASTQ files
- CSV samplesheet
- GRCh38 reference
- GRCh38-compatible target BED file

## Samplesheet schema

Required columns:

- sample_id
- read1
- read2

## Input validation rules

- Sample IDs must be present and unique.
- Both FASTQ mates must exist.
- FASTQ files must be readable.
- R1 and R2 must belong to the same sample.
- Reference build must be GRCh38.
- BED and reference contig names must agree.

## Required workflow stages

1. Read QC
2. Adapter and quality trimming
3. Alignment
4. BAM sorting and indexing
5. Duplicate marking
6. Germline variant calling
7. Variant filtering
8. QC and reporting

## Required outputs

- FastQC reports
- Trimmed FASTQ files
- Sorted and indexed BAM
- Raw gVCF
- Filtered VCF
- Variant statistics
- MultiQC report
- Provenance record

## Failure behavior

The pipeline must stop with a nonzero exit status when:

- a required file is absent;
- the samplesheet is invalid;
- the reference is incompatible;
- a required process fails;
- an expected output is missing or invalid.

## Fixed scientific settings

- Analysis type: germline WES
- Read layout: paired-end
- Reference build: GRCh38
- Clinical interpretation: not permitted

## Completion criteria

A run succeeds only when all required processes finish and all required
outputs pass their validation checks.