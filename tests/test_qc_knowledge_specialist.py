from agent.qc_knowledge_specialist import (
    build_specialist_task,
    create_qc_knowledge_specialist,
    get_specialist_tool_names,
)
from agent.role_contracts import (
    EXECUTION_TOOL_NAMES,
    QC_KNOWLEDGE_SPECIALIST,
)


class DummyModel:
    """Model placeholder; tests never call the LLM."""

    pass


def test_actual_tools_match_role_contract():
    assert set(get_specialist_tool_names()) == set(
        QC_KNOWLEDGE_SPECIALIST.allowed_tools
    )


def test_specialist_has_no_execution_tools():
    assert set(
        get_specialist_tool_names()
    ).isdisjoint(EXECUTION_TOOL_NAMES)


def test_agent_has_managed_agent_identity():
    specialist = create_qc_knowledge_specialist(
        model=DummyModel()
    )

    assert specialist.name == "qc_knowledge_specialist"
    assert specialist.description == (
        QC_KNOWLEDGE_SPECIALIST.description
    )


def test_agent_receives_contract_instructions():
    specialist = create_qc_knowledge_specialist(
        model=DummyModel()
    )

    assert specialist.instructions == (
        QC_KNOWLEDGE_SPECIALIST.build_instructions()
    )

    assert "Prohibited actions:" in specialist.instructions
    assert (
        "Execute or resume a Nextflow pipeline"
        in specialist.instructions
    )


def test_registered_agent_tools_are_read_only():
    specialist = create_qc_knowledge_specialist(
        model=DummyModel()
    )

    registered_tool_names = set(specialist.tools)

    assert set(
        QC_KNOWLEDGE_SPECIALIST.allowed_tools
    ).issubset(registered_tool_names)

    assert "prepare_pipeline_run" not in registered_tool_names
    assert "recommend_recovery" not in registered_tool_names


def test_task_requires_tool_evidence():
    task = build_specialist_task(
        "Which reference build does the pipeline use?"
    )

    assert "Use at least one approved tool" in task
    assert "Base the answer on returned tool evidence" in task
    assert "Cite source filenames" in task


def test_task_rejects_unsupported_interpretation():
    task = build_specialist_task(
        "Give a clinical diagnosis from this VCF"
    )

    assert "Do not invent thresholds" in task
    assert "clinical interpretations" in task
    assert "returned to the manager" in task


def test_task_forbids_pipeline_changes():
    task = build_specialist_task(
        "Run the pipeline with a different reference"
    )

    assert "Do not execute, resume, or modify" in task