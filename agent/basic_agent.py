import os
import time

from smolagents import InferenceClientModel, ToolCallingAgent
from smolagents.utils import AgentGenerationError


def main():
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError("HF_TOKEN is not configured")

    model = InferenceClientModel(
        model_id="openai/gpt-oss-20b",
        provider="together",
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=512,
    )

    agent = ToolCallingAgent(
        tools=[],
        model=model,
        max_steps=5,
    )

    task = (
        "Estimate the input storage required for 20 sequencing "
        "samples if each sample requires 35 GB. "
        "Explain the calculation in one plain-text sentence "
        "without line breaks."
    )

    maximum_attempts = 3

    for attempt in range(1, maximum_attempts + 1):
        try:
            result = agent.run(task, reset=True)

            print("\nFinal result:")
            print(result)
            return

        except AgentGenerationError as error:
            print(
                f"Model generation failed on attempt "
                f"{attempt}/{maximum_attempts}."
            )

            if attempt == maximum_attempts:
                raise

            time.sleep(2)


if __name__ == "__main__":
    main()