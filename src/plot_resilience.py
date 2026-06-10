import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configurazioni di base
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
OUTPUT_DIR = BASE_DIR / "data_output" / "bologna"  # Salviamo nella cartella output
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def plot_resilience_curves():
    csv_path = PROCESSED_DIR / "resilience_percolation_results.csv"
    if not csv_path.exists():
        print(f"File non trovato: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    x = df["Removal_Fraction"] * 100

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    c_rand = "#2ecc71"  # Verde
    c_targ = "#e74c3c"  # Rosso
    c_acc = "#f39c12"  # Arancio

    # --- GRAFICO 1: LCC ---
    ax1.plot(
        x, df["Random_LCC_Size"], label="Guasto Casuale", color=c_rand, lw=2.5, ls="--"
    )
    ax1.plot(
        x, df["Targeted_LCC_Size"], label="Attacco Mirato (Hubs)", color=c_targ, lw=2.5
    )
    ax1.plot(
        x,
        df["Accidents_LCC_Size"],
        label="Rischio Incidenti",
        color=c_acc,
        lw=2.5,
        marker="o",
        ms=4,
    )

    ax1.set_title("Resilienza Topologica (Frammentazione)", fontweight="bold")
    ax1.set_xlabel("Nodi Rimossi (%)", fontweight="bold")
    ax1.set_ylabel("Dimensione Componente Gigante (LCC)", fontweight="bold")
    ax1.set_ylim([0, 1.05])
    ax1.set_xlim([0, 50])
    ax1.legend()

    # --- GRAFICO 2: EFFICIENZA ---
    ax2.plot(
        x,
        df["Random_Efficiency"],
        label="Guasto Casuale",
        color=c_rand,
        lw=2.5,
        ls="--",
    )
    ax2.plot(
        x,
        df["Targeted_Efficiency"],
        label="Attacco Mirato (Hubs)",
        color=c_targ,
        lw=2.5,
    )
    ax2.plot(
        x,
        df["Accidents_Efficiency"],
        label="Rischio Incidenti",
        color=c_acc,
        lw=2.5,
        marker="o",
        ms=4,
    )

    ax2.set_title("Resilienza Dinamica (Tempi di Viaggio)", fontweight="bold")
    ax2.set_xlabel("Nodi Rimossi (%)", fontweight="bold")
    ax2.set_ylabel("Efficienza Globale Residua (Normalizzata)", fontweight="bold")
    ax2.set_ylim([0, 1.05])
    ax2.set_xlim([0, 50])
    ax2.legend()

    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_resilience_curves.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"✅ Grafico di percolazione salvato in: {output_path}")


if __name__ == "__main__":
    plot_resilience_curves()
