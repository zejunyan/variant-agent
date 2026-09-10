"""Read-only specialist for run status, failures, resources, and QC results."""

from typing import Any

from smolagents import ToolCallingAgent

from agent.role_contracts import RESULTS_SPECIALIST
from agent_tools.get_pipeline_status import get_pipeline_status
from agent_tools.get_qc_summary import get_qc_summary
from agent_tools.get_resource_usage import get_resource_usage
from agent_tools.list_failed_processes import list_failed_processes
from agent_tools.plot_concordance import plot_concordance
from agent_tools.read_process_error import read_process_error
from agent_tools.recommend_recovery import recommend_recovery
from agent_tools.summarize_multiqc import summarize_multiqc


RESULTS_SPECIALIST_TOOLS = (
    get_pipeline_status,
    list_failed_processes,
    read_process_error,
    get_resource_usage,
    get_qc_summary,
    summarize_multiqc,
    plot_concordance,
    recommend_recovery,
)


def get_results_specialist_tool_names() -> tuple[str, ...]:
    return tuple(tool.name for tool in RESULTS_SPECIALIST_TOOLS)


def create_results_specialist(model: Any) -> ToolCallingAgent:
    if set(get_results_specialist_tool_names()) != set(
        RESULTS_SPECIALIST.allowed_tools
    ):
        raise RuntimeError("Results specialist tools do not match its role contract")

    return ToolCallingAgent(
        tools=list(RESULTS_SPECIALIST_TOOLS),
        model=model,
        instructions=RESULTS_SPECIALIST.build_instructions(),
        name=RESULTS_SPECIALIST.name,
        description=RESULTS_SPECIALIST.description,
        max_steps=10,
        verbosity_level=2,
        provide_run_summary=True,
    )
