import os
import sys
import time
from pathlib import Path

from smolagents import InferenceClientModel, ToolCallingAgent
from smolagents.utils import AgentGenerationError

from agent_tools.inspect_reference import inspect_reference


def main():
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError("HF_TOKEN is not configured")

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m agent.reference_agent "
            "<reference.fa>"
        )

    reference_path = Path(sys.argv[1]).resolve()

    model = InferenceClientModel(
        model_id="openai/gpt-oss-20b",
        provider="deepinfra",
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1024,
    )

    agent = ToolCallingAgent(
        tools=[inspect_reference],
        model=model,
        max_steps=5,
        verbosity_level=2,
    )

    task = (
        "Use the inspect_reference tool to inspect this reference: "
        f"{reference_path}. Report whether it is valid, list its "
        "contigs, and explain whether it matches the approved GRCh38 "
        "chromosome 20 test reference. Do not guess."
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