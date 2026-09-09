
The pipeline creates the FASTA index and GATK sequence dictionary inside the
relevant containerized processes.

## Generate the synthetic dataset

From the repository root, run:

```bash
python scripts/create_grch38_synthetic_test.py
```

The script creates:

```text
test_data/human_grch38/
|-- reads/
|   |-- human_test_R1.fastq.gz
|   `-- human_test_R2.fastq.gz
`-- truth/
    |-- human_test.truth.vcf
    `-- human_test.callable.bed
```

The generated paired-end reads contain ten deliberately inserted
heterozygous SNPs. The truth VCF records their expected GRCh38 coordinates.

Compress and index the truth VCF using the samtools/htslib container used by
the workflow:

```bash
docker run --rm \
  -v "$PWD:/work" \
  -w /work \
  community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd \
  bgzip -f test_data/human_grch38/truth/human_test.truth.vcf
```

```bash
docker run --rm \
  -v "$PWD:/work" \
  -w /work \
  community.wave.seqera.io/library/htslib_samtools:1.24--d697cfb9dce007cd \
  tabix -f -p vcf \
  test_data/human_grch38/truth/human_test.truth.vcf.gz
```

The resulting truth inputs are:

```text
human_test.truth.vcf.gz
human_test.truth.vcf.gz.tbi
human_test.callable.bed
```

## Create the samplesheet

Create:

```text
test_data/human_grch38/samplesheet.csv
```

The required columns are `sample_id`, `read1`, and `read2`. Use absolute paths
for the FASTQ files so that input resolution does not depend on the directory
from which Nextflow is launched:

```csv
sample_id,read1,read2
human_test,/absolute/path/to/variant-agent/test_data/human_grch38/reads/human_test_R1.fastq.gz,/absolute/path/to/variant-agent/test_data/human_grch38/reads/human_test_R2.fastq.gz
```

Replace `/absolute/path/to/variant-agent` with the repository's actual path on
your computer.

## Run the workflow

Change to the pipeline directory:

```bash
cd pipeline
```

Run the complete workflow:

```bash
nextflow run main.nf \
  --input ../test_data/human_grch38/samplesheet.csv \
  --reference ../test_data/human_grch38/reference/chr20.fa \
  --truth ../test_data/human_grch38/truth/human_test.truth.vcf.gz \
  --callable ../test_data/human_grch38/truth/human_test.callable.bed \
  --outdir ../results/human_grch38 \
  -resume
```

The `-resume` option allows Nextflow to reuse successfully completed cached
tasks when the workflow is rerun without relevant input or code changes.

## Main outputs

```text
results/human_grch38/
|-- alignment/
|-- evaluation/
|   |-- human_test.raw.concordance.tsv
|   `-- human_test.filtered.concordance.tsv
|-- fastp/
|-- fastqc/
|-- metrics/
|-- variants/
|   |-- human_test.g.vcf.gz
|   |-- human_test.raw.vcf.gz
|   |-- human_test.filtered.vcf.gz
|   `-- human_test.pass.vcf.gz
`-- report/
    |-- human_test.variant_summary.tsv
    |-- human_test.raw.concordance_summary.tsv
    |-- human_test.filtered.concordance_summary.tsv
    `-- multiqc_report.html
```

## Current validation result

The raw and filtered call sets were compared with the known truth variants
within the callable BED region.

| Call set | Variant type | TP | FP | FN | Recall | Precision |
|---|---|---:|---:|---:|---:|---:|
| Raw | SNP | 10 | 0 | 0 | 1.0 | 1.0 |
| Filtered | SNP | 10 | 0 | 0 | 1.0 | 1.0 |

The workflow detected all ten inserted SNPs without false-positive or
false-negative SNP calls. Hard filtering did not change the result because the
synthetic reads are clean.

The concordance output reports zero values for indels because the truth set
contains no indels. Therefore, indel performance was **not evaluated**.

## Inspect the reports

From the `pipeline` directory:

```bash
cat ../results/human_grch38/evaluation/human_test.raw.concordance.tsv
```

```bash
cat ../results/human_grch38/evaluation/human_test.filtered.concordance.tsv
```

Open the following file in a web browser to inspect the combined quality-control
report:

```text
results/human_grch38/report/multiqc_report.html
```

## Reproducibility and Git

Pipeline source code, configuration, documentation, and the synthetic-data