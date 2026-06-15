import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import contextily as ctx

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "latex" / "figures" / "bologna"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_bottlenecks_map():
    print(" -> Generazione Mappa Bottleneck Fisici (Act 2)...")
    cent_csv = BASE_DIR / "data_output" / "bologna" / "centrality_results.csv"
    if not cent_csv.exists():
        print("⚠️ centrality_results.csv non trovato!")
        return

    df = pd.read_csv(cent_csv)
    
    # Rimuoviamo i nodi con betweenness zero per pulizia visiva
    df = df[df["Betweenness Centrality"] > 0]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Scatter plot dove la dimensione e il colore dipendono dalla Betweenness
    sns.scatterplot(
        data=df,
        x="Longitude",
        y="Latitude",
        size="Betweenness Centrality",
        hue="Betweenness Centrality",
        palette="Reds",
        sizes=(20, 500),
        alpha=0.8,
        legend=False,
        ax=ax
    )
    
    # Etichettiamo i top 5 bottleneck
    top_5 = df.nlargest(5, "Betweenness Centrality")
    for _, row in top_5.iterrows():
        ax.text(
            row["Longitude"] + 0.001,
            row["Latitude"] + 0.001,
            f"{row['Station_Name']}",
            fontsize=10,
            fontweight="bold",
            color="white",
            bbox=dict(facecolor='#c0392b', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3')
        )

    try:
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.CartoDB.DarkMatter)
    except Exception as e:
        pass
        
    ax.set_title("Colli di Bottiglia (Betweenness Centrality L-Space)", fontsize=15, fontweight="bold", color="white", pad=20)
    fig.patch.set_facecolor('#1a1a1a')
    ax.set_xlabel("Longitudine", fontweight="bold", color="white")
    ax.set_ylabel("Latitudine", fontweight="bold", color="white")
    ax.tick_params(colors="white")
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_bottlenecks_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"✅ Mappa Bottleneck salvata: {output_path}")

def generate_comparative_resilience():
    print(" -> Generazione Confronto Resilienza Bus vs Tram (Act 3)...")
    from src.graph import load_cached_graph
    from src.simulator import simulate_removal, compute_weighted_global_efficiency
    import networkx as nx
    import numpy as np
    
    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")
    
    if not G_bus or not G_fused:
        print("⚠️ Impossibile caricare i grafi per la resilienza.")
        return
        
    fractions = np.linspace(0, 0.4, 20)
    
    # Efficienza Originale
    eff_bus_base = compute_weighted_global_efficiency(G_bus) or 1.0
    eff_fused_base = compute_weighted_global_efficiency(G_fused) or 1.0
    
    # Pre-computa l'ordine di rimozione per attacco mirato
    bus_bet = nx.betweenness_centrality(G_bus, weight="weight")
    sorted_bus = [k for k, v in sorted(bus_bet.items(), key=lambda item: item[1], reverse=True)]
    
    fused_bet = nx.betweenness_centrality(G_fused, weight="weight")
    sorted_fused = [k for k, v in sorted(fused_bet.items(), key=lambda item: item[1], reverse=True)]
    
    bus_eff_drops = []
    fused_eff_drops = []
    
    for f in fractions:
        # Bus
        _, _, e_b = simulate_removal(G_bus, f, scenario="targeted", sorted_nodes=sorted_bus)
        bus_eff_drops.append(e_b / eff_bus_base)
        
        # Fused
        _, _, e_f = simulate_removal(G_fused, f, scenario="targeted", sorted_nodes=sorted_fused)
        fused_eff_drops.append(e_f / eff_fused_base)
        
    sns.set_theme(style="white", context="paper", font_scale=1.2)
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(fractions * 100, bus_eff_drops, label="Attacco Mirato (Solo Bus)", color="#e74c3c", lw=2.5, marker="o")
    ax.plot(fractions * 100, fused_eff_drops, label="Attacco Mirato (Tram Fused)", color="#2ecc71", lw=2.5, marker="s")
    
    ax.set_title("Vantaggio di Resilienza del Tram (L-Space)", fontweight="bold")
    ax.set_xlabel("Nodi Rimossi (%)", fontweight="bold")
    ax.set_ylabel("Efficienza Globale Residua (%)", fontweight="bold")
    ax.set_ylim([0, 1.05])
    ax.set_xlim([0, 40])
    ax.legend()
    
    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_resilience_comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Confronto Resilienza salvato: {out_path}")

if __name__ == "__main__":
    generate_bottlenecks_map()
    generate_comparative_resilience()
