import os
import sys
import time
from pathlib import Path

from smolagents import InferenceClientModel, ToolCallingAgent
from smolagents.utils import AgentGenerationError

from agent_tools.validate_samplesheet import validate_samplesheet


def main():
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError("HF_TOKEN is not configured")

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python agent/samplesheet_agent.py "
            "<samplesheet.csv>"
        )

    samplesheet_path = Path(sys.argv[1]).resolve()

    model = InferenceClientModel(
        model_id="openai/gpt-oss-20b",
        provider="together",
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1024,
    )

    agent = ToolCallingAgent(
        tools=[validate_samplesheet],
        model=model,
        max_steps=5,
    )

    task = (
        "Use the validate_samplesheet tool to validate this "
        f"samplesheet: {samplesheet_path}. "
        "Report whether it is valid. Do not guess file contents."
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