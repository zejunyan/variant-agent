from dataclasses import dataclass


@dataclass(frozen=True)
class AgentRoleContract:
    """Immutable responsibility and permission contract."""

    name: str
    description: str
    responsibilities: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    allowed_delegates: tuple[str, ...]
    prohibited_actions: tuple[str, ...]

    def build_instructions(self) -> str:
        """Convert the contract into agent instructions."""

        responsibilities = "\n".join(
            f"- {item}"
            for item in self.responsibilities
        )

        allowed_tools = (
            "\n".join(
                f"- {tool_name}"
                for tool_name in self.allowed_tools
            )
            if self.allowed_tools
            else "- No direct tools"
        )

        prohibited_actions = "\n".join(
            f"- {item}"
            for item in self.prohibited_actions
        )

        delegates = (
            "\n".join(
                f"- {name}"
                for name in self.allowed_delegates
            )
            if self.allowed_delegates
            else "- No delegation"
        )

        return f"""
Role: {self.name}

Description:
{self.description}

Responsibilities:
{responsibilities}

Allowed tools:
{allowed_tools}

Allowed delegates:
{delegates}

Prohibited actions:
{prohibited_actions}

Only act within this contract. If a request is outside your
responsibility, return it to the manager with a clear explanation.
Never claim that a tool was called unless its result is present in
the agent trace.
""".strip()


QC_KNOWLEDGE_SPECIALIST = AgentRoleContract(
    name="qc_knowledge_specialist",
    description=(
        "A read-only bioinformatics specialist that retrieves "
        "project documentation and inspects existing QC and "
        "variant evidence."
    ),
    responsibilities=(
        "Answer questions using project knowledge-base evidence.",
        "Inspect existing MultiQC output.",
        "Inspect existing VCF headers.",
        "Summarize raw and filtered concordance evidence.",
        "Distinguish technical completion from scientific QC.",
        "State when available evidence is insufficient.",
        "Cite source files and sections used in the answer.",
    ),
    allowed_tools=(
        "search_knowledge_base",
        "summarize_multiqc",
        "inspect_vcf_header",
        "get_qc_summary",
    ),
    allowed_delegates=(),
    prohibited_actions=(
        "Execute or resume a Nextflow pipeline.",
        "Prepare or approve a pipeline execution.",
        "Modify FASTQ, BAM, VCF, reference, or result files.",
        "Change scientific thresholds or reference builds.",
        "Invent QC thresholds that are not documented.",
        "Make clinical interpretations.",
        "Use arbitrary terminal commands.",
    ),
)


MANAGER = AgentRoleContract(
    name="variant_agent_manager",
    description=(
        "The user-facing coordinator that identifies the request "
        "type, delegates work to an approved specialist, and "
        "presents the specialist's evidence."
    ),
    responsibilities=(
        "Understand the user's bioinformatics request.",
        "Delegate QC and documentation questions to the approved "
        "QC and knowledge specialist.",
        "Preserve source citations returned by the specialist.",
        "Report when no available specialist can handle a request.",
        "Request clarification when essential information is missing.",
        "Return a concise evidence-based answer to the user.",
    ),
    allowed_tools=(),
    allowed_delegates=(
        "qc_knowledge_specialist",
    ),
    prohibited_actions=(
        "Execute or resume a Nextflow pipeline.",
        "Call specialist tools directly.",
        "Modify pipeline inputs or outputs.",
        "Bypass a specialist's tool restrictions.",
        "Invent evidence that was not returned by a specialist.",
        "Make clinical interpretations.",
        "Approve its own execution request.",
    ),
)


ROLE_CONTRACTS = {
    MANAGER.name: MANAGER,
    QC_KNOWLEDGE_SPECIALIST.name: QC_KNOWLEDGE_SPECIALIST,
}


EXECUTION_TOOL_NAMES = {
    "prepare_pipeline_run",
    "execute_pipeline_run",
    "nextflow",
    "terminal",
    "shell",
}