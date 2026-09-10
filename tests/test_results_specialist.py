import pytest

import agent.results_specialist as module
from agent.role_contracts import RESULTS_SPECIALIST


class DummyModel:
    pass


def test_identity_tools_and_read_only_contract():
    agent = module.create_results_specialist(DummyModel())
    assert agent.name == "results_specialist"
    assert set(agent.tools) - {"final_answer"} == set(
        RESULTS_SPECIALIST.allowed_tools
    )
    assert "execute_pipeline_run" not in agent.tools
    assert "get_pipeline_status first" in agent.instructions
    assert "Apply recovery recommendations automatically" in agent.instructions


def test_tool_contract_mismatch_is_rejected(monkeypatch):
    monkeypatch.setattr(module, "RESULTS_SPECIALIST_TOOLS", ())
    with pytest.raises(RuntimeError, match="role contract"):
        module.create_results_specialist(DummyModel())
