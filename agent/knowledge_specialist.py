"""Documentation specialist, usable alone or through the manager."""

import argparse
from typing import Any

from smolagents import ToolCallingAgent

from agent.qc_knowledge_specialist import create_hosted_model
from agent.role_contracts import KNOWLEDGE_SPECIALIST
from agent_tools.search_knowledge_base import search_knowledge_base


KNOWLEDGE_SPECIALIST_TOOLS = (search_knowledge_base,)


def get_knowledge_specialist_tool_names() -> tuple[str, ...]:
    return tuple(tool.name for tool in KNOWLEDGE_SPECIALIST_TOOLS)


def build_specialist_task(question: str) -> str:
    if not question.strip():
        raise ValueError("Question cannot be empty")
    return f"Handle this project-documentation request:\n\n{question.strip()}"


def create_knowledge_specialist(model: Any) -> ToolCallingAgent:
    if set(get_knowledge_specialist_tool_names()) != set(
        KNOWLEDGE_SPECIALIST.allowed_tools
    ):
        raise RuntimeError("Knowledge specialist tools do not match its role contract")
    return ToolCallingAgent(
        tools=list(KNOWLEDGE_SPECIALIST_TOOLS),
        model=model,
        instructions=KNOWLEDGE_SPECIALIST.build_instructions(),
        name=KNOWLEDGE_SPECIALIST.name,
        description=KNOWLEDGE_SPECIALIST.description,
        max_steps=6,
        verbosity_level=2,
        provide_run_summary=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the project knowledge specialist.")
    parser.add_argument("question")
    args = parser.parse_args()
    task = build_specialist_task(args.question)
    specialist = create_knowledge_specialist(create_hosted_model())
    print(specialist.run(task))


if __name__ == "__main__":
    main()
