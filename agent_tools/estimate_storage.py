import json
import math

from smolagents import tool


def _is_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def estimate_storage_data(
    sample_count: int,
    input_gb_per_sample: float,
    intermediate_multiplier: float = 3.0,
    output_gb_per_sample: float = 0.5,
    safety_margin_percent: float = 20.0,
) -> dict:
    """
    Estimate storage without using an LLM or accessing files.
    """
    report = {
        "valid": False,
        "inputs": {
            "sample_count": sample_count,
            "input_gb_per_sample": input_gb_per_sample,
            "intermediate_multiplier": intermediate_multiplier,
            "output_gb_per_sample": output_gb_per_sample,
            "safety_margin_percent": safety_margin_percent,
        },
        "estimates_gb": {},
        "errors": [],
        "warnings": [],
    }

    if (
        not isinstance(sample_count, int)
        or isinstance(sample_count, bool)
    ):
        report["errors"].append(
            "sample_count must be an integer."
        )
    elif sample_count <= 0:
        report["errors"].append(
            "sample_count must be greater than zero."
        )
    elif sample_count > 100_000:
        report["errors"].append(
            "sample_count exceeds the supported limit of 100000."
        )

    if not _is_number(input_gb_per_sample):
        report["errors"].append(
            "input_gb_per_sample must be a finite number."
        )
    elif input_gb_per_sample <= 0:
        report["errors"].append(
            "input_gb_per_sample must be greater than zero."
        )

    if not _is_number(intermediate_multiplier):
        report["errors"].append(
            "intermediate_multiplier must be a finite number."
        )
    elif not 0 <= intermediate_multiplier <= 20:
        report["errors"].append(
            "intermediate_multiplier must be between 0 and 20."
        )

    if not _is_number(output_gb_per_sample):
        report["errors"].append(
            "output_gb_per_sample must be a finite number."
        )
    elif output_gb_per_sample < 0:
        report["errors"].append(
            "output_gb_per_sample cannot be negative."
        )

    if not _is_number(safety_margin_percent):
        report["errors"].append(
            "safety_margin_percent must be a finite number."
        )
    elif not 0 <= safety_margin_percent <= 100:
        report["errors"].append(
            "safety_margin_percent must be between 0 and 100."
        )

    if report["errors"]:
        return report

    input_storage = sample_count * input_gb_per_sample

    intermediate_storage = (
        input_storage * intermediate_multiplier
    )

    final_output_storage = (
        sample_count * output_gb_per_sample
    )

    subtotal = (
        input_storage
        + intermediate_storage
        + final_output_storage
    )

    safety_margin = (
        subtotal * safety_margin_percent / 100
    )

    recommended_storage = subtotal + safety_margin

    report["estimates_gb"] = {
        "input_fastq": round(input_storage, 2),
        "intermediate_files": round(
            intermediate_storage,
            2,
        ),
        "final_outputs": round(
            final_output_storage,
            2,
        ),
        "subtotal": round(subtotal, 2),
        "safety_margin": round(safety_margin, 2),
        "recommended_free_space": round(
            recommended_storage,
            2,
        ),
    }

    if safety_margin_percent < 10:
        report["warnings"].append(
            "A safety margin below 10% may be insufficient."
        )

    report["valid"] = True
    return report


@tool
def estimate_storage(
    sample_count: int,
    input_gb_per_sample: float,
    intermediate_multiplier: float = 3.0,
    output_gb_per_sample: float = 0.5,
    safety_margin_percent: float = 20.0,
) -> str:
    """
    Estimate disk space required for a sequencing workflow.

    The estimate includes input FASTQs, intermediate files, final
    outputs, and a safety margin. It does not inspect actual files.

    Args:
        sample_count: Number of sequencing samples.
        input_gb_per_sample: Estimated FASTQ size per sample in GB.
        intermediate_multiplier: Intermediate storage as a multiple
            of total input storage.
        output_gb_per_sample: Expected final-output size per sample
            in GB.
        safety_margin_percent: Extra free space added as a percentage
            of the estimated subtotal.

    Returns:
        A JSON report containing assumptions, storage estimates,
        validation errors, and warnings.
    """
    report = estimate_storage_data(
        sample_count=sample_count,
        input_gb_per_sample=input_gb_per_sample,
        intermediate_multiplier=intermediate_multiplier,
        output_gb_per_sample=output_gb_per_sample,
        safety_margin_percent=safety_margin_percent,
    )

    return json.dumps(report, indent=2)