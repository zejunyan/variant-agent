import argparse
import os
import time

from smolagents import InferenceClientModel, ToolCallingAgent
from smolagents.utils import AgentGenerationError

from agent_tools.estimate_storage import estimate_storage


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Estimate sequencing workflow storage."
    )

    parser.add_argument(
        "--samples",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--input-gb",
        type=float,
        required=True,
    )

    return parser.parse_args()


def main():
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError("HF_TOKEN is not configured")

    args = parse_arguments()

    model = InferenceClientModel(
        model_id="Qwen/Qwen3.5-9B",
        provider="deepinfra",
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1024,
    )

    agent = ToolCallingAgent(
        tools=[estimate_storage],
        model=model,
        max_steps=3,
        verbosity_level=2,
    )

    task = (
        "You must call the estimate_storage tool exactly once. "
        f"Use sample_count={args.samples} and "
        f"input_gb_per_sample={args.input_gb}. "
        "Use the default values for all other arguments. "
        "After receiving the tool result, call final_answer and "
        "explain the input storage and recommended free space. "
        "Do not perform the calculation yourself."
    )

    maximum_attempts = 3

    for attempt in range(1, maximum_attempts + 1):
        try:
            result = agent.run(task, reset=True)

            print("\nFinal result:")
            print(result)
            return

        except AgentGenerationError:
            print(
                f"Model generation failed on attempt "
                f"{attempt}/{maximum_attempts}."
            )

            if attempt == maximum_attempts:
                raise

            time.sleep(2)


if __name__ == "__main__":
    main()