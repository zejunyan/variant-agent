---
document_id: pipeline-overview
title: Germline variant-calling pipeline overview
document_type: project_documentation
reference_build: GRCh38
status: reviewed
---

# Germline variant-calling pipeline overview

## Purpose

This project implements a deterministic germline variant-calling pipeline using
Nextflow and containerized bioinformatics tools.

The pipeline processes paired-end FASTQ files and produces filtered germline
variant calls, quality-control metrics, truth-set comparisons and a final
MultiQC report.

## Pipeline stages

1. FastQC performs initial read-quality assessment.
2. fastp trims and filters paired-end reads.
3. BWA-MEM2 aligns the trimmed reads to the GRCh38 reference.
4. samtools converts and coordinate-sorts the alignment.
5. GATK MarkDuplicates marks duplicate reads.
6. samtools indexes the duplicate-marked BAM.
7. samtools produces alignment metrics.
8. GATK HaplotypeCaller produces a per-sample GVCF.
9. GATK GenotypeGVCFs performs joint genotyping for the sample.
10. The raw VCF is compared with the known truth variants.
11. GATK applies variant filtering.
12. The filtered VCF is compared with the known truth variants.
13. MultiQC creates the final quality-control report.

## Workflow responsibility

Nextflow controls process dependencies, input and output movement, execution,
container selection and reproducibility.

The AI agent does not replace these scientific processes. It can inspect
inputs, retrieve documentation, explain results and later request execution of
approved workflows.

## Current test dataset

The current development dataset is a small synthetic human dataset based on
GRCh38 chromosome 20.

It includes:

- Paired-end FASTQ files
- A GRCh38 chromosome 20 reference
- A truth VCF
- A callable-region BED file
- A samplesheet

## Important scientific constraint

Reference files, BAM files, VCF files and truth resources must use compatible
contig names and the same reference build.