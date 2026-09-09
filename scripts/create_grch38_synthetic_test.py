#!/usr/bin/env python3

import gzip
import random
from pathlib import Path

SEED = 42
CHROMOSOME = "chr20"

# A 100 kb region of GRCh38 chromosome 20
REGION_START_1BASED = 10_000_001
REGION_LENGTH = 100_000

READ_LENGTH = 150
INSERT_SIZE = 350
COVERAGE = 30
NUMBER_OF_VARIANTS = 10
ERROR_RATE = 0.001

REFERENCE_PATH = Path("test_data/human_grch38/reference/chr20.fa")
READS_DIR = Path("test_data/human_grch38/reads")
TRUTH_DIR = Path("test_data/human_grch38/truth")

R1_PATH = READS_DIR / "human_test_R1.fastq.gz"
R2_PATH = READS_DIR / "human_test_R2.fastq.gz"
VCF_PATH = TRUTH_DIR / "human_test.truth.vcf"
BED_PATH = TRUTH_DIR / "human_test.callable.bed"


def read_fasta(path):
    """Read a single-sequence FASTA file."""
    sequence_parts = []
    header = None

    with path.open() as handle:
        for line in handle:
            line = line.strip()

            if line.startswith(">"):
                if header is not None:
                    raise ValueError("Expected a single-sequence FASTA")
                header = line[1:].split()[0]
            elif line:
                sequence_parts.append(line.upper())

    if header is None:
        raise ValueError(f"No FASTA header found in {path}")

    return header, "".join(sequence_parts)


def reverse_complement(sequence):
    table = str.maketrans("ACGTN", "TGCAN")
    return sequence.translate(table)[::-1]


def add_sequencing_errors(sequence, rng):
    """Introduce simple substitution errors."""
    bases = "ACGT"
    result = []

    for base in sequence:
        if base in bases and rng.random() < ERROR_RATE:
            alternatives = bases.replace(base, "")
            result.append(rng.choice(alternatives))
        else:
            result.append(base)

    return "".join(result)


def choose_variant_offsets(region_sequence, count):
    """
    Select reproducible positions distributed across the region.

    Positions near the ends and positions containing N are excluded.
    """
    valid_offsets = [
        offset
        for offset in range(1_000, len(region_sequence) - 1_000)
        if region_sequence[offset] in "ACGT"
    ]

    selected = []

    for index in range(count):
        target_index = int((index + 1) * len(valid_offsets) / (count + 1))
        selected.append(valid_offsets[target_index])

    return selected


def choose_alternate_base(reference_base):
    alternatives = {
        "A": "G",
        "C": "T",
        "G": "A",
        "T": "C",
    }
    return alternatives[reference_base]


def write_fastq_record(handle, read_name, sequence):
    quality = "I" * len(sequence)

    handle.write(f"@{read_name}\n")
    handle.write(f"{sequence}\n")
    handle.write("+\n")
    handle.write(f"{quality}\n")


def main():
    rng = random.Random(SEED)

    READS_DIR.mkdir(parents=True, exist_ok=True)
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    chromosome, full_reference = read_fasta(REFERENCE_PATH)

    if chromosome != CHROMOSOME:
        raise ValueError(
            f"Expected chromosome {CHROMOSOME}, but FASTA contains {chromosome}"
        )

    region_start_0based = REGION_START_1BASED - 1
    region_end_0based = region_start_0based + REGION_LENGTH

    reference_region = full_reference[
        region_start_0based:region_end_0based
    ]

    if len(reference_region) != REGION_LENGTH:
        raise ValueError("The requested region is outside the reference sequence")

    variant_offsets = choose_variant_offsets(
        reference_region,
        NUMBER_OF_VARIANTS,
    )

    # Haplotype 1 remains reference.
    haplotype_1 = reference_region

    # Haplotype 2 contains the known variants.
    haplotype_2_bases = list(reference_region)
    variants = []

    for offset in variant_offsets:
        ref = reference_region[offset]
        alt = choose_alternate_base(ref)
        haplotype_2_bases[offset] = alt

        genomic_position = REGION_START_1BASED + offset
        variants.append((genomic_position, ref, alt))

    haplotype_2 = "".join(haplotype_2_bases)

    # Total sequenced bases:
    # pairs × 2 reads × read length ≈ coverage × region length
    total_pairs = round(
        COVERAGE * REGION_LENGTH / (2 * READ_LENGTH)
    )

    with gzip.open(R1_PATH, "wt") as r1_handle, gzip.open(
        R2_PATH, "wt"
    ) as r2_handle:

        for pair_number in range(1, total_pairs + 1):
            haplotype_number = rng.choice([1, 2])

            if haplotype_number == 1:
                haplotype = haplotype_1
            else:
                haplotype = haplotype_2

            fragment_start = rng.randint(
                0,
                len(haplotype) - INSERT_SIZE,
            )

            fragment = haplotype[
                fragment_start:fragment_start + INSERT_SIZE
            ]

            read_1 = fragment[:READ_LENGTH]
            read_2 = reverse_complement(fragment[-READ_LENGTH:])

            read_1 = add_sequencing_errors(read_1, rng)
            read_2 = add_sequencing_errors(read_2, rng)

            read_name = (
                f"human_test_{pair_number:06d}"
                f"_hap{haplotype_number}"
            )

            write_fastq_record(
                r1_handle,
                f"{read_name}/1",
                read_1,
            )
            write_fastq_record(
                r2_handle,
                f"{read_name}/2",
                read_2,
            )

    with VCF_PATH.open("w") as vcf_handle:
        vcf_handle.write("##fileformat=VCFv4.2\n")
        vcf_handle.write("##source=GRCh38SyntheticTestGenerator\n")
        vcf_handle.write(
            f"##reference={REFERENCE_PATH}\n"
        )
        vcf_handle.write(
            f"##contig=<ID={CHROMOSOME},length={len(full_reference)}>\n"
        )
        vcf_handle.write(
            '##FORMAT=<ID=GT,Number=1,Type=String,'
            'Description="Genotype">\n'
        )
        vcf_handle.write(
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO"
            "\tFORMAT\thuman_test\n"
        )

        for index, (position, ref, alt) in enumerate(variants, start=1):
            vcf_handle.write(
                f"{CHROMOSOME}\t{position}\tsynthetic_{index}"
                f"\t{ref}\t{alt}\t100\tPASS\t.\tGT\t0/1\n"
            )

    # BED coordinates are zero-based and end-exclusive.
    # Exclude the edges because paired-read coverage decreases there.
    callable_margin = INSERT_SIZE
    callable_start = region_start_0based + callable_margin
    callable_end = region_end_0based - callable_margin

    with BED_PATH.open("w") as bed_handle:
        bed_handle.write(
            f"{CHROMOSOME}\t{callable_start}\t{callable_end}\n"
        )

    print("Synthetic GRCh38 test dataset created")
    print(f"Reference region: {CHROMOSOME}:{REGION_START_1BASED}-"
          f"{REGION_START_1BASED + REGION_LENGTH - 1}")
    print(f"Read pairs:       {total_pairs}")
    print(f"Known variants:   {len(variants)}")
    print(f"R1:               {R1_PATH}")
    print(f"R2:               {R2_PATH}")
    print(f"Truth VCF:        {VCF_PATH}")
    print(f"Callable BED:     {BED_PATH}")


if __name__ == "__main__":
    main()