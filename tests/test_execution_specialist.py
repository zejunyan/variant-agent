import pytest

import agent.execution_specialist as module
from agent.role_contracts import EXECUTION_SPECIALIST


class DummyModel:
    pass


def test_identity_tools_and_approval_contract():
    agent = module.create_execution_specialist(DummyModel())
    assert agent.name == "execution_specialist"
    assert set(agent.tools) == {
        "prepare_pipeline_run", "execute_pipeline_run", "final_answer"
    }
    assert agent.instructions == EXECUTION_SPECIALIST.build_instructions()
    assert "exact matching approval" in agent.instructions
    assert "Invent, infer, or approve" in agent.instructions


def test_tool_contract_mismatch_is_rejected(monkeypatch):
    monkeypatch.setattr(module, "EXECUTION_SPECIALIST_TOOLS", ())
    with pytest.raises(RuntimeError, match="role contract"):
        module.create_execution_specialist(DummyModel())
