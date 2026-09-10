from agent.multi_agent_manager import (
    build_manager_task,
    create_multi_agent_system,
)
from agent.role_contracts import (
    MANAGER,
    QC_KNOWLEDGE_SPECIALIST,
)


class DummyModel:
    """Model placeholder; tests do not call the LLM."""

    pass


def test_manager_has_expected_identity():
    manager = create_multi_agent_system(
        model=DummyModel()
    )

    assert manager.name == "variant_agent_manager"
    assert manager.description == MANAGER.description


def test_manager_has_two_managed_agents():
    manager = create_multi_agent_system(
        model=DummyModel()
    )

    assert set(manager.managed_agents) == {
        "qc_knowledge_specialist",
        "knowledge_specialist",
    }


def test_registered_specialist_has_correct_identity():
    manager = create_multi_agent_system(
        model=DummyModel()
    )

    specialist = manager.managed_agents[
        "qc_knowledge_specialist"
    ]

    assert specialist.name == (
        QC_KNOWLEDGE_SPECIALIST.name
    )
    assert specialist.description == (
        QC_KNOWLEDGE_SPECIALIST.description
    )


def test_manager_has_no_direct_domain_tools():
    manager = create_multi_agent_system(
        model=DummyModel()
    )

    # smolagents automatically adds final_answer.
    assert set(manager.tools) == {
        "final_answer",
    }


def test_specialist_has_only_contracted_tools():
    manager = create_multi_agent_system(
        model=DummyModel()
    )

    specialist = manager.managed_agents[
        "qc_knowledge_specialist"
    ]

    actual_domain_tools = (
        set(specialist.tools) - {"final_answer"}
    )

    assert actual_domain_tools == set(
        QC_KNOWLEDGE_SPECIALIST.allowed_tools
    )


def test_manager_receives_role_contract():
    manager = create_multi_agent_system(
        model=DummyModel()
    )

    assert manager.instructions == (
        MANAGER.build_instructions()
    )

    assert (
        "Call specialist tools directly"
        in manager.instructions
    )


def test_supported_request_requires_delegation():
    task = build_manager_task(
        "Which reference files does the pipeline require?"
    )

    normalized_task = " ".join(task.split())

    assert (
        "delegate to qc_knowledge_specialist"
        in normalized_task
    )
    assert (
        "Do not perform the specialist's work yourself"
        in normalized_task
    )


def test_unsupported_execution_is_rejected():
    task = build_manager_task(
        "Run the pipeline now"
    )

    normalized_task = " ".join(task.split())

    assert "request concerns execution" in normalized_task
    assert (
        "no currently registered specialist is authorized"
        in normalized_task
    )
    assert "Do not execute commands" in normalized_task


def test_manager_must_preserve_evidence():
    task = build_manager_task(
        "Summarize the QC results"
    )

    assert "Use only the evidence returned" in task
    assert "Preserve source filenames" in task
    assert "insufficient evidence" in task


def test_documentation_routing_reaches_manager_contract():
    manager = create_multi_agent_system(model=DummyModel())
    assert "knowledge_specialist" in manager.instructions
    assert "consult both specialists" in manager.instructions
    assert "delegate to knowledge_specialist" in " ".join(
        build_manager_task("Which reference is required?").split()
    )
    knowledge = manager.managed_agents["knowledge_specialist"]
    assert set(knowledge.tools) == {"search_knowledge_base", "final_answer"}
