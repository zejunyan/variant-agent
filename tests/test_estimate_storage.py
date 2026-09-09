from agent_tools.estimate_storage import estimate_storage_data


def test_normal_storage_estimate():
    report = estimate_storage_data(
        sample_count=20,
        input_gb_per_sample=35,
        intermediate_multiplier=3,
        output_gb_per_sample=0.5,
        safety_margin_percent=20,
    )

    assert report["valid"] is True
    assert report["estimates_gb"]["input_fastq"] == 700
    assert (
        report["estimates_gb"]["intermediate_files"]
        == 2100
    )
    assert report["estimates_gb"]["final_outputs"] == 10
    assert report["estimates_gb"]["subtotal"] == 2810
    assert report["estimates_gb"]["safety_margin"] == 562
    assert (
        report["estimates_gb"]["recommended_free_space"]
        == 3372
    )


def test_zero_samples_is_rejected():
    report = estimate_storage_data(
        sample_count=0,
        input_gb_per_sample=35,
    )

    assert report["valid"] is False
    assert any(
        "greater than zero" in error
        for error in report["errors"]
    )


def test_negative_input_size_is_rejected():
    report = estimate_storage_data(
        sample_count=20,
        input_gb_per_sample=-35,
    )

    assert report["valid"] is False
    assert any(
        "input_gb_per_sample" in error
        for error in report["errors"]
    )


def test_invalid_safety_margin_is_rejected():
    report = estimate_storage_data(
        sample_count=20,
        input_gb_per_sample=35,
        safety_margin_percent=150,
    )

    assert report["valid"] is False
    assert any(
        "safety_margin_percent" in error
        for error in report["errors"]
    )


def test_low_safety_margin_produces_warning():
    report = estimate_storage_data(
        sample_count=20,
        input_gb_per_sample=35,
        safety_margin_percent=5,
    )

    assert report["valid"] is True
    assert report["warnings"]