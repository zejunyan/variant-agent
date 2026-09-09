import argparse
import os
import time
from pathlib import Path

from smolagents import InferenceClientModel, ToolCallingAgent
from smolagents.utils import AgentGenerationError

from agent_tools.inspect_vcf_header import inspect_vcf_header


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Inspect VCF header metadata."
    )

    parser.add_argument(
        "vcf",
        help="Path to a VCF or compressed VCF.",
    )

    parser.add_argument(
        "--expected-sample",
        default="human_test",
    )

    parser.add_argument(
        "--expected-contig",
        default="chr20",
    )

    return parser.parse_args()


def main():
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError("HF_TOKEN is not configured")

    args = parse_arguments()
    vcf_path = Path(args.vcf).resolve()

    model = InferenceClientModel(
        model_id="Qwen/Qwen3.5-9B",
        provider="deepinfra",
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1024,
    )

    agent = ToolCallingAgent(
        tools=[inspect_vcf_header],
        model=model,
        max_steps=3,
        verbosity_level=2,
    )

    task = (
        "You must call the inspect_vcf_header tool exactly once. "
        f"Inspect VCF path {vcf_path}, using expected_sample="
        f"{args.expected_sample} and expected_contig="
        f"{args.expected_contig}. Explain whether the VCF header "
        "is valid using only the returned evidence. If index_exists "
        "is true, say only that an index file exists; do not claim "
        "that its integrity was validated. Missing reference metadata "
        "means the reference build cannot be confirmed from that "
        "header field. Do not perform clinical interpretation."
    )

    for attempt in range(1, 4):
        try:
            result = agent.run(task, reset=True)
            print("\nFinal result:")
            print(result)
            return

        except AgentGenerationError:
            print(
                f"Model generation failed on attempt {attempt}/3."
            )

            if attempt == 3:
                raise

            time.sleep(2)


if __name__ == "__main__":
    main()