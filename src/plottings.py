# src/plottings.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from pathlib import Path

# Configurazioni di base
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
OUTPUT_DIR = BASE_DIR / "data_output" / "bologna"
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
    plt.close()
    print(f"✅ Grafico di percolazione salvato in: {output_path}")


def plot_centrality_analysis(df_centrality, output_path_scatter, output_path_hist):
    """Genera grafici correlazione grado-betweenness e istogramma della betweenness."""
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    
    # 1. SCATTER PLOT: Betweenness vs Degree
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(
        data=df_centrality, 
        x="Degree", 
        y="Betweenness Centrality", 
        alpha=0.6, 
        edgecolor=None, 
        color="#3498db", 
        ax=ax
    )
    
    # Evidenzia i top 5 bottlenecks
    top_5 = df_centrality.sort_values(by="Betweenness Centrality", ascending=False).head(5)
    sns.scatterplot(
        data=top_5,
        x="Degree",
        y="Betweenness Centrality",
        color="#e74c3c",
        s=100,
        edgecolor="black",
        linewidth=1.5,
        ax=ax,
        label="Top 5 Bottlenecks"
    )
    
    # Etichette sui nodi top 5
    for _, row in top_5.iterrows():
        ax.text(
            row["Degree"] + 0.1, 
            row["Betweenness Centrality"], 
            row["Station_Name"], 
            fontsize=9, 
            fontweight="bold",
            color="#2c3e50"
        )
        
    ax.set_title("Correlazione tra Grado e Centralità di Betweenness", fontweight="bold", fontsize=13)
    ax.set_xlabel("Grado del Nodo (Degree)", fontweight="bold")
    ax.set_ylabel("Centralità di Betweenness (Weighted)", fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.savefig(output_path_scatter, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Grafico correlazione centralità salvato in: {output_path_scatter}")
    
    # 2. HISTOGRAM: Betweenness Centrality Distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    df_filtered = df_centrality[df_centrality["Betweenness Centrality"] > 0]
    sns.histplot(
        data=df_filtered,
        x="Betweenness Centrality",
        kde=True,
        color="#9b59b6",
        bins=30,
        ax=ax,
        stat="density"
    )
    ax.set_title("Distribuzione della Centralità di Betweenness (Valori > 0)", fontweight="bold", fontsize=13)
    ax.set_xlabel("Centralità di Betweenness", fontweight="bold")
    ax.set_ylabel("Densità di Frequenza", fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path_hist, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Istogramma distribuzione betweenness salvato in: {output_path_hist}")


def plot_static_network(G, output_path):
    """Genera una visualizzazione statica del grafo con coordinate geografiche per LaTeX."""
    fig, ax = plt.subplots(figsize=(12, 10))
    pos = {n: (data["lon"], data["lat"]) for n, data in G.nodes(data=True) if "lon" in data and "lat" in data}
    
    # 1. Disegna archi bus (grigi chiari e sottili)
    bus_edges = [(u, v) for u, v, data in G.edges(data=True) if data.get("type") == "bus" and u in pos and v in pos]
    nx.draw_networkx_edges(G, pos, edgelist=bus_edges, ax=ax, edge_color="#bdc3c7", width=0.8, alpha=0.5)
    
    # 2. Disegna archi tram (rossi e spessi)
    tram_edges = [(u, v) for u, v, data in G.edges(data=True) if data.get("type") == "tram" and u in pos and v in pos]
    nx.draw_networkx_edges(G, pos, edgelist=tram_edges, ax=ax, edge_color="#e74c3c", width=3.0, alpha=0.9)
    
    # 3. Disegna archi di trasbordo multiplex (arancione a trattini)
    trans_edges = [(u, v) for u, v, data in G.edges(data=True) if data.get("type") == "trasbordo_pedonale" and u in pos and v in pos]
    if trans_edges:
        nx.draw_networkx_edges(G, pos, edgelist=trans_edges, ax=ax, edge_color="#f39c12", width=1.5, alpha=0.7, style="dashed")

    # 4. Disegna nodi bus (piccoli, grigio scuro)
    bus_nodes = [n for n, data in G.nodes(data=True) if data.get("type") == "bus" and n in pos]
    nx.draw_networkx_nodes(G, pos, nodelist=bus_nodes, ax=ax, node_color="#2c3e50", node_size=10, alpha=0.6)
    
    # 5. Disegna nodi tram (blu, medi)
    tram_nodes = [n for n, data in G.nodes(data=True) if data.get("type") == "tram" and n in pos]
    if tram_nodes:
        nx.draw_networkx_nodes(G, pos, nodelist=tram_nodes, ax=ax, node_color="#2980b9", node_size=30, alpha=0.9)
        
    # 6. Disegna nodi di intersezione fusione (arancione, grandi)
    inter_nodes = [n for n, data in G.nodes(data=True) if data.get("type") == "intersezione_bus_tram" and n in pos]
    if inter_nodes:
        nx.draw_networkx_nodes(G, pos, nodelist=inter_nodes, ax=ax, node_color="#e67e22", node_size=50, alpha=0.9)

    ax.set_title("Mappa Topologica L-Space della Rete di Bologna", fontsize=14, fontweight="bold")
    ax.set_xlabel("Longitudine", fontweight="bold")
    ax.set_ylabel("Latitudine", fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Mappa statica della rete salvata in: {output_path}")
