import json
import re
from pathlib import Path
from uuid import uuid4

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from smolagents import tool

from agent_tools.get_qc_summary import read_concordance_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "results" / "agent_runs"

RUN_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,39}$")
SAMPLE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def within(path: Path, root: Path) -> bool:
    return path.is_relative_to(root)


def load_metrics(path: Path, run_directory: Path) -> dict:
    """Validate counts and calculate metrics from their denominators."""

    report = read_concordance_file(path, run_directory)

    if not report["valid"]:
        raise ValueError("; ".join(report["errors"]))

    metrics = {}

    for row in report["rows"]:
        variant_type = row["type"].upper()

        if variant_type not in {"SNP", "INDEL"}:
            raise ValueError(
                f"Unsupported variant type: {variant_type}"
            )

        if variant_type in metrics:
            raise ValueError(
                f"Duplicate variant type: {variant_type}"
            )

        tp = row["true_positives"]
        fp = row["false_positives"]
        fn = row["false_negatives"]

        if min(tp, fp, fn) < 0:
            raise ValueError("Variant counts cannot be negative")

        metrics[variant_type] = {
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
        }

    return metrics


def plot_concordance_data(
    run_name: str,
    expected_sample: str,
    results_root: Path | None = None,
) -> dict:
    """Create a derived PNG without changing source results."""

    report = {
        "valid": False,
        "run_name": run_name,
        "sample": expected_sample,
        "plot_path": None,
        "sources": [],
        "metrics": {},
        "errors": [],
        "warnings": [],
    }

    if not RUN_PATTERN.fullmatch(run_name):
        report["errors"].append("Invalid run name.")
        return report

    if not SAMPLE_PATTERN.fullmatch(expected_sample):
        report["errors"].append("Invalid sample identifier.")
        return report

    root = (results_root or RESULTS_ROOT).resolve()
    run_directory = (root / run_name).resolve()

    if not within(run_directory, root):
        report["errors"].append(
            "Run directory is outside the approved results root."
        )
        return report

    if not run_directory.is_dir():
        report["errors"].append("Run directory does not exist.")
        return report

    try:
        for stage in ("raw", "filtered"):
            source = (
                run_directory
                / "evaluation"
                / f"{expected_sample}.{stage}.concordance.tsv"
            ).resolve()

            if not within(source, run_directory):
                raise ValueError(
                    "Concordance file is outside the run directory."
                )

            report["metrics"][stage] = load_metrics(
                source, run_directory
            )
            report["sources"].append(str(source))

        plot_directory = (run_directory / "plots").resolve()

        if not within(plot_directory, run_directory):
            raise ValueError(
                "Plot directory is outside the run directory."
            )

        for stage, metrics in report["metrics"].items():
            for variant_type in ("SNP", "INDEL"):
                values = metrics.get(variant_type)

                if values is None:
                    report["warnings"].append(
                        f"{stage} {variant_type}: no result row."
                    )
                elif (
                    values["precision"] is None
                    or values["recall"] is None
                ):
                    report["warnings"].append(
                        f"{stage} {variant_type}: a zero denominator "
                        "makes one or more metrics undefined."
                    )

        figure = Figure(figsize=(10, 5), layout="constrained")
        FigureCanvasAgg(figure)
        axes = figure.subplots(1, 2)

        for axis, variant_type in zip(axes, ("SNP", "INDEL")):
            for stage, offset, color in (
                ("raw", -0.19, "#2563eb"),
                ("filtered", 0.19, "#0d9488"),
            ):
                values = report["metrics"][stage].get(
                    variant_type, {}
                )

                for position, metric in enumerate(
                    ("precision", "recall")
                ):
                    value = values.get(metric)
                    x = position + offset

                    axis.bar(
                        x,
                        value if value is not None else 0,
                        width=0.34,
                        color=color,
                        label=stage.capitalize()
                        if position == 0 else None,
                    )

                    axis.text(
                        x,
                        value + 0.025 if value is not None else 0.04,
                        f"{value:.3f}" if value is not None else "N/A",
                        ha="center",
                        fontsize=10,
                    )

            axis.set_title(variant_type)
            axis.set_xticks([0, 1], ["Precision", "Recall"])
            axis.set_ylim(0, 1.15)
            axis.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
            axis.set_ylabel("Proportion")
            axis.legend(loc="upper left", fontsize=9)
            axis.spines[["top", "right"]].set_visible(False)

        figure.suptitle(
            f"{expected_sample} — raw and filtered concordance"
        )
        figure.supxlabel(
            "N/A = missing evidence or zero denominator. "
            "Metrics calculated from TP, FP and FN."
        )

        plot_directory.mkdir(parents=True, exist_ok=True)

        # Unique filename preserves previously generated figures.
        output = plot_directory / (
            f"{expected_sample}.concordance."
            f"{uuid4().hex[:12]}.png"
        )

        with output.open("xb") as handle:
            figure.savefig(handle, format="png", dpi=160)

        figure.clear()

        report["plot_path"] = str(output)
        report["valid"] = True

    except (OSError, ValueError, TypeError) as error:
        report["errors"].append(str(error))

    return report


@tool
def plot_concordance(
    run_name: str,
    expected_sample: str,
) -> str:
    """
    Create a plot comparing raw and filtered variant concordance.

    Use when the user requests a concordance plot. Reads existing
    TP, FP and FN counts and saves a new PNG in the run's plots
    directory. Undefined precision or recall is displayed as N/A.
    Source files are preserved. Return the plot path to the user.

    Args:
        run_name: Controlled run name, such as phase8-monitoring-test.
        expected_sample: Exact sample identifier, such as human_test.

    Returns:
        JSON containing the saved image path, source files, plotted
        metrics, warnings and errors.
    """
    return json.dumps(
        plot_concordance_data(run_name, expected_sample),
        indent=2,
        allow_nan=False,
    )