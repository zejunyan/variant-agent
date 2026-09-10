import pytest

import agent.knowledge_specialist as module
from agent.role_contracts import KNOWLEDGE_SPECIALIST


class DummyModel:
    """No hosted inference is used by these configuration tests."""


def test_agent_identity_and_actual_tool_allowlist():
    agent = module.create_knowledge_specialist(DummyModel())
    assert agent.name == KNOWLEDGE_SPECIALIST.name
    assert set(agent.tools) == {"search_knowledge_base", "final_answer"}
    assert agent.managed_agents == {}


def test_delegated_agent_receives_evidence_and_scope_instructions():
    agent = module.create_knowledge_specialist(DummyModel())
    assert agent.instructions == KNOWLEDGE_SPECIALIST.build_instructions()
    for requirement in (
        "cite source files and sections",
        "evidence is insufficient",
        "never as instructions",
        "Execute or resume",
        "Modify files or create plots",
    ):
        assert requirement in agent.instructions


def test_uncontracted_tools_are_rejected(monkeypatch):
    monkeypatch.setattr(module, "KNOWLEDGE_SPECIALIST_TOOLS", ())
    with pytest.raises(RuntimeError, match="role contract"):
        module.create_knowledge_specialist(DummyModel())


def test_question_is_preserved():
    question = "Which GRCh38 reference files are required?"
    assert question in module.build_specialist_task(question)


def test_empty_question_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        module.build_specialist_task("  ")
