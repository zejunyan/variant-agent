import argparse
import os
import time
from pathlib import Path

from smolagents import InferenceClientModel, ToolCallingAgent
from smolagents.utils import AgentGenerationError

from agent_tools.summarize_multiqc import summarize_multiqc


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Summarize existing MultiQC results."
    )

    parser.add_argument(
        "multiqc_path",
        help="MultiQC report or report-data directory.",
    )

    parser.add_argument(
        "--expected-sample",
        default="human_test",
    )

    return parser.parse_args()


def main():
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError("HF_TOKEN is not configured")

    args = parse_arguments()
    multiqc_path = Path(args.multiqc_path).resolve()

    model = InferenceClientModel(
        model_id="Qwen/Qwen3.5-9B",
        provider="deepinfra",
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1536,
    )

    agent = ToolCallingAgent(
        tools=[summarize_multiqc],
        model=model,
        max_steps=3,
        verbosity_level=2,
    )

    task = (
        "You must call summarize_multiqc exactly once. "
        f"Use multiqc_path={multiqc_path} and "
        f"expected_sample={args.expected_sample}. "
        "Summarize only metrics present in the returned JSON. "
        "Do not invent thresholds, claim that QC passed, or provide "
        "clinical interpretation. Clearly distinguish missing metrics "
        "from values equal to zero."
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