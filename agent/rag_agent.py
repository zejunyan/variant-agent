import os
import sys
import time

from smolagents import (
    InferenceClientModel,
    ToolCallingAgent,
)
from smolagents.utils import AgentGenerationError

from agent_tools.search_knowledge_base import (
    search_knowledge_base,
)


MODEL_ID = "Qwen/Qwen3.5-9B"
MODEL_PROVIDER = "deepinfra"


def build_task(question: str) -> str:
    """Create a controlled RAG task for the agent."""

    return f"""
Answer the following question about the variant-calling project:

{question}

Requirements:

1. You must call the search_knowledge_base tool before answering.
2. Base your answer only on evidence returned by the tool.
3. Cite the source filename and section used.
4. Clearly separate documented facts from your interpretation.
5. Do not invent thresholds, versions, files, clinical conclusions,
   or pipeline behavior.
6. If the retrieved evidence is insufficient, explicitly say:
   "The project knowledge base does not contain enough information
   to answer this question."
7. Do not run the pipeline or modify any files.
""".strip()


def create_agent() -> ToolCallingAgent:
    """Create the project RAG agent."""

    if "HF_TOKEN" not in os.environ:
        raise RuntimeError(
            "HF_TOKEN is not configured in the environment"
        )

    model = InferenceClientModel(
        model_id=MODEL_ID,
        provider=MODEL_PROVIDER,
        token=os.environ["HF_TOKEN"],
        temperature=0.0,
        max_tokens=1536,
    )

    return ToolCallingAgent(
        tools=[search_knowledge_base],
        model=model,
        max_steps=4,
        verbosity_level=2,
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            'Usage: python agent/rag_agent.py '
            '"<question about the pipeline>"'
        )

    question = " ".join(sys.argv[1:]).strip()

    if not question:
        raise SystemExit("The question cannot be empty")

    agent = create_agent()
    task = build_task(question)

    maximum_attempts = 3

    for attempt in range(1, maximum_attempts + 1):
        try:
            result = agent.run(
                task,
                reset=True,
            )

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