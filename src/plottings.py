# src/plottings.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx

# Configurazioni di base
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
OUTPUT_DIR = BASE_DIR / "latex" / "figures" / "bologna"
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


def plot_centrality_analysis(df_centrality):
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
        ax=ax,
    )

    # Evidenzia i top 5 bottlenecks
    top_5 = df_centrality.sort_values(
        by="Betweenness Centrality", ascending=False
    ).head(5)
    sns.scatterplot(
        data=top_5,
        x="Degree",
        y="Betweenness Centrality",
        color="#e74c3c",
        s=100,
        edgecolor="black",
        linewidth=1.5,
        ax=ax,
        label="Top 5 Bottlenecks",
    )

    # Etichette sui nodi top 5
    for _, row in top_5.iterrows():
        ax.text(
            row["Degree"] + 0.1,
            row["Betweenness Centrality"],
            row["Station_Name"],
            fontsize=9,
            fontweight="bold",
            color="#2c3e50",
        )

    ax.set_title(
        "Correlazione tra Grado e Centralità di Betweenness",
        fontweight="bold",
        fontsize=13,
    )
    ax.set_xlabel("Grado del Nodo (Degree)", fontweight="bold")
    ax.set_ylabel("Centralità di Betweenness (Weighted)", fontweight="bold")
    ax.legend()
    plt.tight_layout()
    output_path_scatter = OUTPUT_DIR / "bologna_centrality_scatter.png"
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
        stat="density",
    )
    ax.set_title(
        "Distribuzione della Centralità di Betweenness (Valori > 0)",
        fontweight="bold",
        fontsize=13,
    )
    ax.set_xlabel("Centralità di Betweenness", fontweight="bold")
    ax.set_ylabel("Densità di Frequenza", fontweight="bold")
    plt.tight_layout()
    output_path_hist = OUTPUT_DIR / "bologna_betweenness_hist.png"
    plt.savefig(output_path_hist, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Istogramma distribuzione betweenness salvato in: {output_path_hist}")


def plot_static_network(G):
    """Genera una visualizzazione statica del grafo con coordinate geografiche per LaTeX."""
    import contextily as ctx
    from collections import defaultdict

    fig, ax = plt.subplots(figsize=(12, 10))
    pos = {
        n: (data["lon"], data["lat"])
        for n, data in G.nodes(data=True)
        if "lon" in data and "lat" in data
    }

    # 1. Disegna archi bus colorati per linea (evitiamo il rosso puro riservato al tram)
    bus_edges_by_route = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get("type") == "bus" and u in pos and v in pos:
            route_id = str(data.get("route_id", "default"))
            bus_edges_by_route[route_id].append((u, v))

    def get_bus_color(route_id):
        colors = [
            "#3498db",  # Azzurro
            "#9b59b6",  # Viola
            "#1abc9c",  # Turchese
            "#f1c40f",  # Giallo
            "#34495e",  # Grigio scuro
            "#2ecc71",  # Verde
            "#e67e22",  # Arancione
            "#16a085",  # Ottanio
            "#8e44ad",  # Viola scuro
            "#27ae60",  # Verde scuro
            "#2980b9",  # Blu
            "#d35400",  # Zucca
        ]
        return colors[hash(str(route_id)) % len(colors)]

    for route_id, edgelist in bus_edges_by_route.items():
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=edgelist,
            ax=ax,
            edge_color=get_bus_color(route_id),
            width=1.0,
            alpha=0.45,
        )

    # 2. Disegna archi tram (spessi e colorati per linea)
    tram_edges_by_route = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get("type") == "tram" and u in pos and v in pos:
            route_id = str(data.get("route_id", "default")).upper()
            tram_edges_by_route[route_id].append((u, v))

    for route_id, edgelist in tram_edges_by_route.items():
        # Linea Rossa (RED, ROSSA) in rosso, Linea Verde in verde
        if any(keyword in route_id for keyword in ["RED", "ROSSA"]):
            color = "#e74c3c"  # Rosso tram
        else:
            color = "#27ae60"  # Verde tram
        nx.draw_networkx_edges(
            G, pos, edgelist=edgelist, ax=ax, edge_color=color, width=3.2, alpha=0.9
        )

    # 3. Disegna archi di trasbordo multiplex (arancione a trattini)
    trans_edges = [
        (u, v)
        for u, v, data in G.edges(data=True)
        if data.get("type") == "trasbordo_pedonale" and u in pos and v in pos
    ]
    if trans_edges:
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=trans_edges,
            ax=ax,
            edge_color="#e67e22",
            width=1.5,
            alpha=0.7,
            style="dashed",
        )

    # 4. Disegna nodi bus (piccoli, grigio scuro)
    bus_nodes = [
        n for n, data in G.nodes(data=True) if data.get("type") == "bus" and n in pos
    ]
    nx.draw_networkx_nodes(
        G, pos, nodelist=bus_nodes, ax=ax, node_color="#2c3e50", node_size=10, alpha=0.6
    )

    # 5. Disegna nodi tram (blu, medi)
    tram_nodes = [
        n for n, data in G.nodes(data=True) if data.get("type") == "tram" and n in pos
    ]
    if tram_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=tram_nodes,
            ax=ax,
            node_color="#2980b9",
            node_size=30,
            alpha=0.9,
        )

    # 6. Disegna nodi di intersezione fusione (arancione, grandi)
    inter_nodes = [
        n
        for n, data in G.nodes(data=True)
        if data.get("type") == "intersezione_bus_tram" and n in pos
    ]
    if inter_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=inter_nodes,
            ax=ax,
            node_color="#d35400",
            node_size=50,
            alpha=0.9,
        )

    # 7. Aggiungi il basemap geografico minimale da OpenStreetMap/CartoDB
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    try:
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.CartoDB.Positron)
    except Exception as e:
        print(f"⚠️ Errore caricamento mappa di sfondo: {e}")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    ax.set_title(
        "Mappa Topologica L-Space e Layout Stradale della Rete di Bologna",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Longitudine", fontweight="bold")
    ax.set_ylabel("Latitudine", fontweight="bold")

    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_static_network.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Mappa statica della rete salvata in: {output_path}")


def plot_optimized_layout(G_planned, G_opt):
    """Genera un grafico comparativo side-by-side geografico tra il tracciato pianificato e quello ottimizzato."""
    import contextily as ctx

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

    # Prepara coordinate nodi
    pos_planned = {
        n: (data["lon"], data["lat"])
        for n, data in G_planned.nodes(data=True)
        if "lon" in data and "lat" in data
    }
    pos_opt = {
        n: (data["lon"], data["lat"])
        for n, data in G_opt.nodes(data=True)
        if "lon" in data and "lat" in data
    }

    # ------------------ SUBPLOT 1: PIANIFICATO (TPER) ------------------
    # Bus edges (grigio molto chiaro)
    bus_edges_p = [
        (u, v)
        for u, v, data in G_planned.edges(data=True)
        if data.get("type") == "bus" and u in pos_planned and v in pos_planned
    ]
    nx.draw_networkx_edges(
        G_planned,
        pos_planned,
        edgelist=bus_edges_p,
        ax=ax1,
        edge_color="#bdc3c7",
        width=0.8,
        alpha=0.3,
    )

    # Tram edges planned (rosso/verde)
    tram_edges_p = [
        (u, v)
        for u, v, data in G_planned.edges(data=True)
        if data.get("type") == "tram" and u in pos_planned and v in pos_planned
    ]
    nx.draw_networkx_edges(
        G_planned,
        pos_planned,
        edgelist=tram_edges_p,
        ax=ax1,
        edge_color="#e74c3c",
        width=2.5,
        alpha=0.9,
    )

    # Nodi tram
    tram_nodes_p = [
        n
        for n, data in G_planned.nodes(data=True)
        if data.get("type") in ["tram", "intersezione_bus_tram"] and n in pos_planned
    ]
    nx.draw_networkx_nodes(
        G_planned,
        pos_planned,
        nodelist=tram_nodes_p,
        ax=ax1,
        node_color="#2980b9",
        node_size=30,
        alpha=0.9,
    )

    ax1.set_title(
        "Layout Pianificato (Rete Rossa & Verde TPER)", fontsize=14, fontweight="bold"
    )
    ax1.set_xlabel("Longitudine", fontweight="bold")
    ax1.set_ylabel("Latitudine", fontweight="bold")

    # ------------------ SUBPLOT 2: OTTIMIZZATO (Greedy TNDP) ------------------
    # Bus edges (grigio molto chiaro)
    bus_edges_o = [
        (u, v)
        for u, v, data in G_opt.edges(data=True)
        if data.get("type") == "bus" and u in pos_opt and v in pos_opt
    ]
    nx.draw_networkx_edges(
        G_opt,
        pos_opt,
        edgelist=bus_edges_o,
        ax=ax2,
        edge_color="#bdc3c7",
        width=0.8,
        alpha=0.3,
    )

    # Tram edges optimized (viola elettrico)
    tram_edges_o = [
        (u, v)
        for u, v, data in G_opt.edges(data=True)
        if data.get("type") == "tram" and u in pos_opt and v in pos_opt
    ]
    nx.draw_networkx_edges(
        G_opt,
        pos_opt,
        edgelist=tram_edges_o,
        ax=ax2,
        edge_color="#9b59b6",
        width=2.5,
        alpha=0.9,
    )

    # Nodi tram
    tram_nodes_o = [
        n
        for n, data in G_opt.nodes(data=True)
        if data.get("type") in ["tram", "intersezione_bus_tram"] and n in pos_opt
    ]
    nx.draw_networkx_nodes(
        G_opt,
        pos_opt,
        nodelist=tram_nodes_o,
        ax=ax2,
        node_color="#8e44ad",
        node_size=30,
        alpha=0.9,
    )

    ax2.set_title(
        "Layout Ottimizzato (Algoritmo Greedy Steiner-TNDP)",
        fontsize=14,
        fontweight="bold",
    )
    ax2.set_xlabel("Longitudine", fontweight="bold")
    ax2.set_ylabel("Latitudine", fontweight="bold")

    # Aggiungi basemap e mantieni i limiti
    for ax, pos in [(ax1, pos_planned), (ax2, pos_opt)]:
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        try:
            ctx.add_basemap(
                ax, crs="EPSG:4326", source=ctx.providers.CartoDB.Positron, alpha=0.45
            )
        except Exception as e:
            print(f"⚠️ Errore caricamento mappa di sfondo: {e}")
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

    plt.suptitle(
        "Bologna: Confronto tra Rete Tram Pianificata e Ottimizzata (Budget 20 km)",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_optimized_layout.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Grafico di confronto layout salvato in: {output_path}")


if __name__ == "__main__":
    from src.graph import load_cached_graph
    from src.analyzer import compute_centralities

    # 1. Resilience curves
    print(" -> Generating resilience curves...")
    plot_resilience_curves()

    # 2. Centrality plots
    print(" -> Loading graph and computing centralities for plots...")
    G_bus = load_cached_graph("G_bus")
    df_cent = compute_centralities(G_bus)

    print(" -> Generating centrality plots...")
    plot_centrality_analysis(df_cent)

    # 3. Static network layout map
    print(" -> Loading fused graph for static network map...")
    G_fused = load_cached_graph("G_fused")

    print(" -> Generating static transit map...")
    plot_static_network(G_fused)

    # 4. Optimized vs planned layout
    print(" -> Generating optimized vs planned layout...")
    G_planned = load_cached_graph("G_fused")
    G_opt = load_cached_graph("G_opt_tram")
    plot_optimized_layout(G_planned, G_opt)

    print("✅ All plots generated successfully!")
