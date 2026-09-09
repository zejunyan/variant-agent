from agent.execution_planning_agent import build_task


def test_task_contains_user_request():
    request = (
        "Prepare the GRCh38 test run using my samplesheet."
    )

    task = build_task(request)

    assert request in task


def test_task_requires_planning_tool():
    task = build_task("Prepare a test run")

    assert "Use the prepare_pipeline_run tool" in task


def test_task_forbids_execution():
    task = build_task("Run my pipeline")

    assert "Do not execute Nextflow" in task
    assert "Do not call a terminal" in task


def test_task_requires_approval_message():
    task = build_task("Prepare a test run")

    assert "human approval is required" in task


def test_task_encodes_allowed_values():
    task = build_task("Prepare a test run")

    assert "germline_test" in task
    assert "GRCh38" in task
    assert "profile is test" in task