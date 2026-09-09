from agent.rag_agent import build_task


def test_build_task_contains_question():
    question = (
        "What should I check when a BAM cannot be opened?"
    )

    task = build_task(question)

    assert question in task


def test_build_task_requires_retrieval():
    task = build_task("Which reference files are required?")

    assert "must call the search_knowledge_base tool" in task
    assert "Base your answer only on evidence" in task


def test_build_task_requires_source_citation():
    task = build_task("Which reference files are required?")

    assert "Cite the source filename and section" in task


def test_build_task_prevents_unsupported_answer():
    task = build_task("What filtering threshold should I use?")

    assert "Do not invent thresholds" in task
    assert "does not contain enough information" in task


def test_build_task_prevents_execution():
    task = build_task("Run the pipeline")

    assert "Do not run the pipeline" in task
    assert "modify any files" in task