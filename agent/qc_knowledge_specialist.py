import argparse
import os
import time
from typing import Any

from smolagents import (
    InferenceClientModel,
    ToolCallingAgent,
)
from smolagents.utils import AgentGenerationError

from agent.role_contracts import (
    QC_KNOWLEDGE_SPECIALIST,
)
from agent_tools.get_qc_summary import get_qc_summary
from agent_tools.inspect_vcf_header import inspect_vcf_header
from agent_tools.search_knowledge_base import (
    search_knowledge_base,
)
from agent_tools.summarize_multiqc import summarize_multiqc
from agent_tools.plot_concordance import plot_concordance


MODEL_ID = "Qwen/Qwen3.5-9B"
MODEL_PROVIDER = "deepinfra"


QC_SPECIALIST_TOOLS = (
    search_knowledge_base,
    summarize_multiqc,
    inspect_vcf_header,
    get_qc_summary,
    plot_concordance,
)


def get_specialist_tool_names() -> tuple[str, ...]:
    """Return the actual tool names assigned to the specialist."""

    return tuple(
        tool.name
        for tool in QC_SPECIALIST_TOOLS
    )


def build_specialist_task(question: str) -> str:
    """Create a controlled task for the QC specialist."""

    return f"""
Handle this QC or project-knowledge request:

{question}

Requirements:

1. Use at least one approved tool before answering.
2. Use search_knowledge_base for questions about documented
   pipeline behavior, requirements, or troubleshooting.
3. Use get_qc_summary for combined QC and concordance evidence
   from a controlled run.
4. Use summarize_multiqc when the request identifies a specific
   MultiQC report directory.
5. Use inspect_vcf_header when the request identifies a specific
   VCF that needs header inspection.
6. Base the answer on returned tool evidence.
7. Cite source filenames, sections, or inspected paths.
8. State clearly when evidence is insufficient.
9. Separate technical completion from scientific QC.
10. Do not invent thresholds, versions, reference builds, files,
    or clinical interpretations.
11. Do not execute, resume, or modify the pipeline.
12. If the request is outside this role, say that it must be
    returned to the manager.
""".strip()


def create_qc_knowledge_specialist(
    model: Any,
) -> ToolCallingAgent:
    """Create the specialist using an injected model."""

    actual_tools = set(get_specialist_tool_names())
    contracted_tools = set(
        QC_KNOWLEDGE_SPECIALIST.allowed_tools
    )

    if actual_tools != contracted_tools:
        raise RuntimeError(
            "The specialist's actual tools do not match its "
            "role contract. "
            f"Actual: {sorted(actual_tools)}; "
            f"contracted: {sorted(contracted_tools)}"
        )

    return ToolCallingAgent(
        tools=list(QC_SPECIALIST_TOOLS),
        model=model,
        instructions=(
            QC_KNOWLEDGE_SPECIALIST.build_instructions()
        ),
        name=QC_KNOWLEDGE_SPECIALIST.name,
        description=QC_KNOWLEDGE_SPECIALIST.description,
        max_steps=6,
        verbosity_level=2,
        provide_run_summary=True,
    )


def create_hosted_model() -> InferenceClientModel:
    """Create the hosted model used by the specialist."""

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
            "Run the standalone QC and knowledge specialist."
        )
    )

    parser.add_argument(
        "question",
        help="QC or project-knowledge question.",
    )

    args = parser.parse_args()

    question = args.question.strip()

    if not question:
        raise SystemExit("Question cannot be empty")

    model = create_hosted_model()

    specialist = create_qc_knowledge_specialist(
        model=model
    )

    task = build_specialist_task(question)

    maximum_attempts = 3

    for attempt in range(1, maximum_attempts + 1):
        try:
            result = specialist.run(
                task,
                reset=True,
            )

            print("\nSpecialist result:")
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