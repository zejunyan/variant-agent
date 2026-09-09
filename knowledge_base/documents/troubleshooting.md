---
document_id: troubleshooting
title: Variant pipeline troubleshooting guide
document_type: project_documentation
reference_build: GRCh38
status: draft
---

# Variant pipeline troubleshooting guide

## Missing FASTQ mate

### Symptom

The samplesheet contains an incomplete row, or one paired FASTQ file cannot be
found.

### Checks

- Confirm that both R1 and R2 paths are present.
- Confirm that both files exist.
- Confirm that the paths are absolute or correctly resolved.
- Confirm that the files belong to the same sample.

### Required action

Correct the samplesheet or restore the missing file before running the
pipeline.

## Missing reference

### Symptom

Nextflow reports that the reference FASTA does not exist.

### Checks

- Confirm the reference path.
- Confirm whether the command was started from the repository root or the
  pipeline directory.
- Confirm that the FASTA index and sequence dictionary also exist.

### Required action

Do not continue variant calling until the required reference files are
available.

## BAM cannot be opened

### Symptom

`samtools quickcheck` reports that the BAM file cannot be opened.

### Checks

- Confirm the correct results directory.
- Use an absolute host path when mounting the directory into Docker.
- Confirm that the expected BAM was published by Nextflow.
- Confirm that the filename matches the process output.

### Required action

Distinguish between a missing pipeline output and an incorrect Docker volume
mount before rerunning the pipeline.

## VCF header validation failure

### Checks

- Confirm that the VCF contains a `#CHROM` header.
- Confirm that the expected sample is present.
- Confirm that the expected contig is declared.
- For a compressed VCF, confirm that the corresponding index exists.
- Confirm reference-build compatibility.

## No relevant knowledge-base result

If the retrieval system cannot find evidence supporting an answer, the agent
must say that the knowledge base does not contain enough information. It must
not invent a scientific rule, threshold, tool version or reference build.