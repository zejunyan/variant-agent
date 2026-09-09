import os
import sys
import time

from smolagents import (
    InferenceClientModel,
    ToolCallingAgent,
)
from smolagents.utils import AgentGenerationError

from agent_tools.pipeline_launcher import (
    prepare_pipeline_run,
)


MODEL_ID = "Qwen/Qwen3.5-9B"
MODEL_PROVIDER = "deepinfra"


def build_task(user_request: str) -> str:
    return f"""
Prepare a safe execution plan for this request:

{user_request}

Rules:

1. Use the prepare_pipeline_run tool.
2. The only workflow is germline_test.
3. The only profile is test.
4. The only reference build is GRCh38.
5. The samplesheet must be inside
   test_data/human_grch38.
6. Use a unique lowercase run name containing only letters,
   numbers and hyphens.
7. Do not execute Nextflow.
8. Do not call a terminal.
9. Report all validation errors.
10. If the plan is valid, report the plan ID, exact command,
    sample count and output directory.
11. State clearly that human approval is required before
    execution.
""".strip()


def create_agent() -> ToolCallingAgent:
    if "HF_TOKEN" not in os.environ:
        raise RuntimeError(
            "HF_TOKEN is not configured"
        )

    model = InferenceClientModel(
        model_id=MODEL_ID,
        provider=MODEL_PROVIDER,
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1536,
    )

    return ToolCallingAgent(
        tools=[prepare_pipeline_run],
        model=model,
        max_steps=4,
        verbosity_level=2,
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python -m agent.execution_planning_agent '
            '"<pipeline request>"'
        )

    user_request = " ".join(sys.argv[1:]).strip()

    if not user_request:
        raise SystemExit("The request cannot be empty")

    agent = create_agent()
    task = build_task(user_request)

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