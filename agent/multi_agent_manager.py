import argparse
import os
import time
from typing import Any

from smolagents import (
    InferenceClientModel,
    ToolCallingAgent,
)
from smolagents.utils import AgentGenerationError

from agent.qc_knowledge_specialist import (
    create_qc_knowledge_specialist,
)
from agent.knowledge_specialist import create_knowledge_specialist
from agent.execution_specialist import create_execution_specialist
from agent.results_specialist import create_results_specialist
from agent.role_contracts import (
    EXECUTION_SPECIALIST,
    MANAGER,
    QC_KNOWLEDGE_SPECIALIST,
    RESULTS_SPECIALIST,
)


MODEL_ID = "Qwen/Qwen3.5-9B"
MODEL_PROVIDER = "deepinfra"


def build_manager_task(question: str) -> str:
    """Create a controlled task for the manager."""

    return f"""
Handle this user request:

{question}

Delegation procedure:

1. Determine whether the request concerns:
   - Project documentation
   - Pipeline input requirements
   - QC or MultiQC results
   - Raw or filtered concordance
   - VCF header inspection
   - Creating plots from existing concordance results
   - Preparing or launching an approved pipeline run
   - Run status, failed processes, resource usage, and recovery evidence

2. For documentation, input requirements, reference resources, or documented
   troubleshooting, delegate to knowledge_specialist.
   For VCF header inspection or a focused QC question,
   delegate to qc_knowledge_specialist.
   For pipeline planning or an execution request, delegate to
   execution_specialist. The specialist may execute only when the user supplied
   an exact APPROVE-<plan-id> value; preserve that value verbatim.
   For run status, failures, resources, MultiQC, concordance results, recovery
   recommendations, or plots, delegate to results_specialist.
   For mixed requests, consult both specialists and distinguish documented
   guidance from observed run evidence.

3. Give the specialist the complete user request, including any
   run name, sample name, VCF path, or MultiQC path supplied by
   the user.

4. Do not perform the specialist's work yourself.

5. Use only the evidence returned by the specialist.

6. Preserve source filenames, section names, inspected paths,
   warnings, and limitations from the specialist response.

7. If the specialist reports insufficient evidence, preserve that
   conclusion. Do not fill the gap using unsupported model
   knowledge.

8. If the request concerns pipeline resume, unauthorized file modification,
   clinical interpretation, or another
   unsupported responsibility, explain that no currently
   registered specialist is authorized to perform it.

9. Do not execute commands or modify files directly. Execution is available
   only by delegating to execution_specialist under its approval contract.

10. In the final answer, identify which specialist handled the
    request and summarize its evidence clearly.
""".strip()


def create_multi_agent_system(
    model: Any,
) -> ToolCallingAgent:
    """Create the manager and its four bounded specialists."""

    specialist = create_qc_knowledge_specialist(
        model=model
    )
    knowledge_specialist = create_knowledge_specialist(model=model)
    execution_specialist = create_execution_specialist(model=model)
    results_specialist = create_results_specialist(model=model)

    actual_delegates = {
        specialist.name,
        knowledge_specialist.name,
        execution_specialist.name,
        results_specialist.name,
    }

    contracted_delegates = set(
        MANAGER.allowed_delegates
    )

    if actual_delegates != contracted_delegates:
        raise RuntimeError(
            "The manager's actual delegates do not match its "
            "role contract. "
            f"Actual: {sorted(actual_delegates)}; "
            f"contracted: {sorted(contracted_delegates)}"
        )

    if specialist.name != QC_KNOWLEDGE_SPECIALIST.name:
        raise RuntimeError(
            "Specialist name does not match its role contract."
        )

    if execution_specialist.name != EXECUTION_SPECIALIST.name:
        raise RuntimeError("Execution specialist name does not match its role contract.")
    if results_specialist.name != RESULTS_SPECIALIST.name:
        raise RuntimeError("Results specialist name does not match its role contract.")

    manager = ToolCallingAgent(
        tools=[],
        model=model,
        managed_agents=[
            specialist,
            knowledge_specialist,
            execution_specialist,
            results_specialist,
        ],
        instructions=MANAGER.build_instructions(),
        name=MANAGER.name,
        description=MANAGER.description,
        max_steps=5,
        verbosity_level=2,
    )

    return manager


def create_hosted_model() -> InferenceClientModel:
    """Create the hosted model shared by both agents."""

    if "HF_TOKEN" not in os.environ:
        raise RuntimeError(
            "HF_TOKEN is not configured"
        )

    return InferenceClientModel(
        model_id=MODEL_ID,
        provider=MODEL_PROVIDER,
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=2048,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the manager with knowledge, QC, execution, and results specialists."
        )
    )

    parser.add_argument(
        "question",
        help="Question for the multi-agent system.",
    )

    args = parser.parse_args()

    question = args.question.strip()

    if not question:
        raise SystemExit("Question cannot be empty")

    model = create_hosted_model()
    manager = create_multi_agent_system(model=model)
    task = build_manager_task(question)

    maximum_attempts = 3

    for attempt in range(1, maximum_attempts + 1):
        try:
            result = manager.run(
                task,
                reset=True,
            )

            print("\nManager result:")
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
