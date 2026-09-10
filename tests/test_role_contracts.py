from agent.role_contracts import (
    EXECUTION_TOOL_NAMES,
    MANAGER,
    QC_KNOWLEDGE_SPECIALIST,
    ROLE_CONTRACTS,
)


def test_role_names_are_unique():
    assert len(ROLE_CONTRACTS) == 3
    assert set(ROLE_CONTRACTS) == {
        "variant_agent_manager",
        "qc_knowledge_specialist",
        "knowledge_specialist",
    }


def test_manager_has_no_direct_tools():
    assert MANAGER.allowed_tools == ()


def test_manager_can_delegate_only_to_registered_specialists():
    assert MANAGER.allowed_delegates == (
        "qc_knowledge_specialist",
        "knowledge_specialist",
    )


def test_qc_specialist_cannot_delegate():
    assert QC_KNOWLEDGE_SPECIALIST.allowed_delegates == ()


def test_qc_specialist_has_expected_read_only_tools():
    assert set(QC_KNOWLEDGE_SPECIALIST.allowed_tools) == {
        "search_knowledge_base",
        "summarize_multiqc",
        "inspect_vcf_header",
        "get_qc_summary",
        "plot_concordance",
    }


def test_qc_specialist_has_no_execution_tools():
    assert (
        set(QC_KNOWLEDGE_SPECIALIST.allowed_tools)
        .isdisjoint(EXECUTION_TOOL_NAMES)
    )


def test_manager_has_no_execution_tools():
    assert (
        set(MANAGER.allowed_tools)
        .isdisjoint(EXECUTION_TOOL_NAMES)
    )


def test_contract_instructions_include_boundaries():
    instructions = (
        QC_KNOWLEDGE_SPECIALIST.build_instructions()
    )

    assert "Allowed tools:" in instructions
    assert "Prohibited actions:" in instructions
    assert "search_knowledge_base" in instructions
    assert "Execute or resume a Nextflow pipeline" in instructions
    assert "Never claim that a tool was called" in instructions
