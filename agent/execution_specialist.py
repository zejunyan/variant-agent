"""Specialist for controlled planning and explicitly approved execution."""

from typing import Any

from smolagents import ToolCallingAgent

from agent.role_contracts import EXECUTION_SPECIALIST
from agent_tools.pipeline_launcher import (
    execute_pipeline_run,
    prepare_pipeline_run,
)


EXECUTION_SPECIALIST_TOOLS = (
    prepare_pipeline_run,
    execute_pipeline_run,
)


def get_execution_specialist_tool_names() -> tuple[str, ...]:
    return tuple(tool.name for tool in EXECUTION_SPECIALIST_TOOLS)


def create_execution_specialist(model: Any) -> ToolCallingAgent:
    if set(get_execution_specialist_tool_names()) != set(
        EXECUTION_SPECIALIST.allowed_tools
    ):
        raise RuntimeError("Execution specialist tools do not match its role contract")

    return ToolCallingAgent(
        tools=list(EXECUTION_SPECIALIST_TOOLS),
        model=model,
        instructions=EXECUTION_SPECIALIST.build_instructions(),
        name=EXECUTION_SPECIALIST.name,
        description=EXECUTION_SPECIALIST.description,
        max_steps=6,
        verbosity_level=2,
        provide_run_summary=True,
    )
