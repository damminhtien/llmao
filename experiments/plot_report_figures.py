"""Plot selected published results without rerunning experimental evaluation."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "figures"
COLORS = ("#38685b", "#b56c42", "#637994", "#96958d")


def table_rows(report: str, section: str) -> list[list[str]]:
    """Read the first Markdown table under an exact section heading."""
    text = (ROOT / "reports" / report).read_text()
    lines = text.split(section, 1)[1].splitlines()
    rows = []
    started = False
    for line in lines:
        if line.startswith("|"):
            started = True
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(rows) >= 1 and all(set(cell) <= set(" -:") for cell in cells):
                continue
            rows.append(cells)
        elif started:
            break
    return rows[1:]


def save(figure: plt.Figure, name: str) -> None:
    figure.savefig(OUTPUT / name, dpi=180, facecolor=figure.get_facecolor())
    plt.close(figure)


def plot_v1() -> None:
    rows = table_rows("FINAL_REPORT.md", "## Final test accuracy")
    selected = {
        "Qwen: raw pixels + stroke direction": ("Pixels + stroke direction", COLORS[0]),
        "Raw pixels": ("Raw pixels", COLORS[3]),
        "HOG control": ("HOG", COLORS[2]),
    }
    figure, axis = plt.subplots(figsize=(10, 4.7), layout="constrained")
    sizes = [250, 500, 1000, 5000, 60000]
    for row in rows:
        if row[0] not in selected:
            continue
        values = [cell.replace("%", "").split("±") for cell in row[2:]]
        label, color = selected[row[0]]
        axis.errorbar(
            sizes, [float(value[0]) for value in values],
            yerr=[float(value[1]) for value in values],
            color=color, label=label, marker="o", capsize=3, linewidth=2,
        )
    axis.set_xscale("log")
    axis.set_xticks(sizes, [f"{size:,}" for size in sizes])
    axis.set_ylim(75, 100)
    axis.set_xlabel("Training examples (log scale)")
    axis.set_ylabel("Official MNIST test accuracy (%)")
    axis.set_title("V1: a useful addition to pixels, with HOG still ahead", loc="left")
    axis.legend(loc="lower right", frameon=False)
    save(figure, "V1_LEARNING_CURVES.png")


def plot_v2() -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.7), layout="constrained")
    rows = table_rows("V2_PROGRAM_SYNTHESIS.md", "## Raw-pixel augmentation controls")
    labels = ["Pixels", "Pixels + angles", "Pixels + spatial"]
    positions = np.arange(len(rows))
    for column, shift, color, label in [(3, -.18, COLORS[3], "500 examples"),
                                         (5, .18, COLORS[0], "5,000 examples")]:
        axes[0].bar(positions + shift, [float(row[column]) * 100 for row in rows],
                    width=.36, color=color, label=label)
    axes[0].set_xticks(positions, labels)
    axes[0].set_ylim(0, 100)
    axes[0].set_ylabel("MNIST validation accuracy (%)")
    axes[0].set_title("A. Post-search pixel augmentation", loc="left")
    axes[0].legend(frameon=False, loc="lower right")

    rows = table_rows("V2_PROGRAM_SYNTHESIS.md", "## Frozen transfer evaluation")
    chosen = [row for row in rows if row[1] == "spatial_cycle_hist" and row[4] == "5000"]
    domains = ["emnist_digits", "emnist_letters", "kmnist", "fashion_mnist"]
    chosen = sorted(chosen, key=lambda row: domains.index(row[0]))
    values = [row[5].split("±") for row in chosen]
    axes[1].bar(range(4), [float(value[0]) * 100 for value in values],
                yerr=[float(value[1]) * 100 for value in values],
                capsize=3, color=[COLORS[0]] * 3 + [COLORS[1]])
    axes[1].set_xticks(range(4), ["EMNIST\nDigits", "EMNIST\nLetters", "KMNIST", "Fashion\nMNIST"])
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Sampled official-test accuracy (%)")
    axes[1].set_title("B. Spatial cycle summary, 25 dimensions", loc="left")
    save(figure, "V2_AUGMENTATION_TRANSFER.png")


def plot_v3() -> None:
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.9), layout="constrained")
    rows = table_rows("V3_EVIDENCE.md", "## Mechanism evidence")
    positions = np.arange(len(rows))
    for column, shift, label, color in [(1, -.18, "Original", COLORS[0]),
                                         (2, .18, "Locations reassigned", COLORS[1])]:
        axes[0].bar(positions + shift, [float(row[column]) * 100 for row in rows],
                    width=.36, color=color, label=label)
    axes[0].set_xticks(positions, ["Angle /\ncentroid", "Regional\nturns", "Horizontal\nturns", "Regional\nprofile", "Vertical\ngradient"])
    axes[0].set_ylim(0, 100)
    axes[0].set_ylabel("Sampled MNIST test accuracy (%)")
    axes[0].set_title("A. Preserve marginals; change event locations", loc="left")
    axes[0].legend(frameon=False, loc="lower right")

    rows = table_rows("V3_EVIDENCE.md", "## Transfer evaluation")
    intervals = [[float(value) * 100 for value in row[2].split("–")] for row in rows]
    centers = [sum(values) / 2 for values in intervals]
    widths = [(values[1] - values[0]) / 2 for values in intervals]
    positions = np.arange(len(rows))
    axes[1].errorbar(positions - .16, centers, yerr=widths, fmt="none", capsize=6,
                    color=COLORS[0], linewidth=3, label="V3 finalist range")
    axes[1].scatter(positions, [float(row[3].split("/")[1]) * 100 for row in rows],
                   marker="s", color=COLORS[3], label="Zoning (30D)")
    axes[1].scatter(positions + .16, [float(row[5]) * 100 for row in rows],
                   marker="^", color=COLORS[2], label="HOG")
    axes[1].set_xticks(positions, ["EMNIST\nDigits", "EMNIST\nLetters", "KMNIST", "Fashion\nMNIST"])
    axes[1].set_ylim(0, 100)
    axes[1].set_ylabel("Sampled official-test accuracy (%)")
    axes[1].set_title("B. Transfer with 5,000 training examples", loc="left")
    axes[1].legend(frameon=False, loc="lower left")
    save(figure, "V3_MECHANISM_TRANSFER.png")


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    plt.rcParams.update({
        "font.size": 10, "axes.titlesize": 12, "axes.titlepad": 16,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.axisbelow": True, "axes.grid": True, "grid.alpha": .15,
        "axes.facecolor": "#faf9f5", "figure.facecolor": "#faf9f5",
    })
    plot_v1()
    plot_v2()
    plot_v3()


if __name__ == "__main__":
    main()
