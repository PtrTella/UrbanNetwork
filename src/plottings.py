# src/plottings.py
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx

def apply_latex_plot_style(ax, title, xlabel, ylabel):
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    ax.set_title(title, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel, fontweight="bold")
    ax.set_ylabel(ylabel, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.7)

def apply_latex_map_style(fig, ax, title, dark_mode=True):
    import contextily as ctx
    fig.patch.set_facecolor('#1a1a1a' if dark_mode else 'white')
    text_color = 'white' if dark_mode else 'black'
    
    # Save the limits of the plotted data
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    try:
        source = ctx.providers.CartoDB.DarkMatter if dark_mode else ctx.providers.CartoDB.Positron
        ctx.add_basemap(ax, crs="EPSG:4326", source=source)
    except Exception as e:
        print(f"⚠️ Errore caricamento mappa di sfondo: {e}")
        
    # Restore the limits so contextily doesn't alter the zoom/bounds
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
        
    ax.set_title(title, fontsize=15, fontweight="bold", color=text_color, pad=20)
    ax.set_xlabel("Longitudine", fontweight="bold", color=text_color)
    ax.set_ylabel("Latitudine", fontweight="bold", color=text_color)
    ax.tick_params(colors=text_color)

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

    sns.set_theme(style="white", context="paper", font_scale=1.2)
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
    sns.set_theme(style="white", context="paper", font_scale=1.2)

    # 1. SCATTER PLOT: Betweenness vs Degree (with regression and jitter)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.regplot(
        data=df_centrality,
        x="Degree",
        y="Betweenness Centrality",
        x_jitter=0.15,
        scatter_kws={"alpha": 0.4, "color": "#3498db", "edgecolor": None},
        line_kws={"color": "#e74c3c", "linewidth": 2.0, "label": "Linea di Tendenza"},
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
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.CartoDB.DarkMatter)
    except Exception as e:
        print(f"⚠️ Errore caricamento mappa di sfondo: {e}")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    fig.patch.set_facecolor("#1a1a1a")
    ax.set_title(
        "Mappa Topologica L-Space e Layout Stradale della Rete di Bologna",
        fontsize=14,
        fontweight="bold",
        color="white",
    )
    ax.set_xlabel("Longitudine", fontweight="bold", color="white")
    ax.set_ylabel("Latitudine", fontweight="bold", color="white")
    ax.tick_params(colors="white")

    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_static_network.png"
    plt.savefig(
        output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor()
    )
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


def plot_demographic_pressure_maps():
    """Genera due mappe per la pressione demografica (popolazione servita)."""
    import contextily as ctx

    csv_bus = BASE_DIR / "data_output" / "bologna" / "demographic_bus_results.csv"
    csv_tram = BASE_DIR / "data_output" / "bologna" / "demographic_tram_results.csv"
    if not csv_bus.exists() or not csv_tram.exists():
        print("⚠️ File non trovati. Eseguire demographic.py prima.")
        return

    df_bus = pd.read_csv(csv_bus)
    df_tram = pd.read_csv(csv_tram)
    df_bus = df_bus[df_bus["Population_Served"] > 0]
    df_tram = df_tram[df_tram["Population_Served"] > 0]

    sns.set_theme(style="white", context="paper")

    # --- Mappa 1: Pressione Demografica Globale (Zone) ---
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.kdeplot(
        data=df_tram,
        x="Longitude",
        y="Latitude",
        weights="Population_Served",
        fill=True,
        cmap="inferno",
        alpha=0.6,
        levels=100,
        thresh=0.05,
        ax=ax,
    )

    try:
        ctx.add_basemap(ax, crs="EPSG:4326", source=ctx.providers.CartoDB.DarkMatter)
    except Exception as e:
        print(f"⚠️ Errore caricamento mappa di sfondo: {e}")

    ax.set_title(
        "Pressione Demografica Globale (Densità per Macro-Aree)",
        fontsize=15,
        fontweight="bold",
        color="white",
        pad=20,
    )
    fig.patch.set_facecolor("#1a1a1a")  # Sfondo scuro per far risaltare DarkMatter
    ax.set_xlabel("Longitudine", fontweight="bold", color="white")
    ax.set_ylabel("Latitudine", fontweight="bold", color="white")
    ax.tick_params(colors="white")

    plt.tight_layout()
    output_path1 = OUTPUT_DIR / "bologna_demographic_pressure_map.png"
    plt.savefig(
        output_path1, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor()
    )
    plt.close()

    # --- Mappa 2: Top Vulnerabilità / Saturazione (Confronto Bus vs Tram) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    top_n = 15

    for ax, df, title in zip(
        [ax1, ax2],
        [df_bus, df_tram],
        ["Vulnerabilità Rete Bus", "Assorbimento Rete Tram"],
    ):
        # Usiamo Dwell_Penalty invece di Population_Served per la classifica
        df_top = df.nlargest(top_n, "Dwell_Penalty")

        # Sfondo KDE basato sulla vulnerabilità
        sns.kdeplot(
            data=df,
            x="Longitude",
            y="Latitude",
            weights="Dwell_Penalty",
            fill=True,
            cmap="magma",
            alpha=0.4,
            levels=50,
            thresh=0.05,
            ax=ax,
        )

        # Etichette pulite per le Top Macro-Zone vulnerabili
        for _, row in df_top.iterrows():
            ax.plot(
                row["Longitude"],
                row["Latitude"],
                marker="o",
                markersize=8,
                color="#e74c3c",
                markeredgecolor="white",
            )
            ax.text(
                row["Longitude"] + 0.0015,
                row["Latitude"] + 0.0015,
                f"{row['Zone_Name']}\n(+{int(row['Dwell_Penalty'])}s delay)",
                fontsize=9,
                fontweight="bold",
                color="white",
                bbox=dict(
                    facecolor="#c0392b",
                    alpha=0.8,
                    edgecolor="none",
                    boxstyle="round,pad=0.3",
                ),
            )

        try:
            ctx.add_basemap(
                ax, crs="EPSG:4326", source=ctx.providers.CartoDB.DarkMatter
            )
        except Exception:
            pass

        ax.set_title(
            f"Top {top_n} Macro-Zone: {title}",
            fontsize=15,
            fontweight="bold",
            color="white",
            pad=20,
        )
        ax.set_xlabel("Longitudine", fontweight="bold", color="white")
        ax.set_ylabel("Latitudine", fontweight="bold", color="white")
        ax.tick_params(colors="white")

    fig.patch.set_facecolor("#1a1a1a")
    plt.tight_layout()
    output_path2 = OUTPUT_DIR / "bologna_top_vulnerability.png"
    plt.savefig(
        output_path2, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor()
    )
    plt.close()
    print(f"✅ Mappe di vulnerabilità e densità salvate in: {OUTPUT_DIR}")

def plot_communities_map():
    csv_comm = BASE_DIR / "data_output" / "bologna" / "communities_bus.csv"
    if not csv_comm.exists():
        print("⚠️ File communities_bus.csv non trovato.")
        return
        
    df_comm = pd.read_csv(csv_comm)
    df_comm = df_comm[df_comm["Community_ID"] >= 0]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.scatterplot(data=df_comm, x="Longitude", y="Latitude", hue="Community_ID", palette="tab20", s=60, alpha=0.9, edgecolor="white", legend=False, ax=ax)
    
    apply_latex_map_style(fig, ax, "Act 1: P-Space Sociological Communities (Louvain)")
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_communities_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"✅ Mappa delle comunità salvata in: {output_path}")

def plot_bottlenecks_map():
    cent_csv = BASE_DIR / "data_output" / "bologna" / "centrality_results.csv"
    if not cent_csv.exists(): return
    df = pd.read_csv(cent_csv)
    df = df[df["Betweenness Centrality"] > 0]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    sns.scatterplot(data=df, x="Longitude", y="Latitude", size="Betweenness Centrality", hue="Betweenness Centrality", palette="Reds", sizes=(20, 500), alpha=0.8, legend=False, ax=ax)
    
    top_5 = df.nlargest(5, "Betweenness Centrality")
    for _, row in top_5.iterrows():
        ax.text(row["Longitude"] + 0.001, row["Latitude"] + 0.001, f"{row['Station_Name']}", fontsize=10, fontweight="bold", color="white", bbox=dict(facecolor='#c0392b', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3'))

    apply_latex_map_style(fig, ax, "Act 2: Physical Bottlenecks (L-Space Betweenness Centrality)")
    
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_bottlenecks_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"✅ Mappa Bottleneck salvata: {output_path}")

def plot_comparative_resilience():
    from src.graph import load_cached_graph
    from src.simulator import simulate_removal, compute_weighted_global_efficiency
    import numpy as np
    
    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")
    if not G_bus or not G_fused: return
        
    fractions = np.linspace(0, 0.4, 20)
    eff_bus_base = compute_weighted_global_efficiency(G_bus) or 1.0
    eff_fused_base = compute_weighted_global_efficiency(G_fused) or 1.0
    
    bus_bet = nx.betweenness_centrality(G_bus, weight="weight")
    sorted_bus = [k for k, v in sorted(bus_bet.items(), key=lambda item: item[1], reverse=True)]
    fused_bet = nx.betweenness_centrality(G_fused, weight="weight")
    sorted_fused = [k for k, v in sorted(fused_bet.items(), key=lambda item: item[1], reverse=True)]
    
    bus_eff_drops, fused_eff_drops = [], []
    for f in fractions:
        _, _, e_b = simulate_removal(G_bus, f, scenario="targeted", sorted_nodes=sorted_bus)
        bus_eff_drops.append(e_b / eff_bus_base)
        _, _, e_f = simulate_removal(G_fused, f, scenario="targeted", sorted_nodes=sorted_fused)
        fused_eff_drops.append(e_f / eff_fused_base)
        
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(fractions * 100, bus_eff_drops, label="Attacco Mirato (Solo Bus)", color="#e74c3c", lw=2.5, marker="o")
    ax.plot(fractions * 100, fused_eff_drops, label="Attacco Mirato (Tram Fused)", color="#2ecc71", lw=2.5, marker="s")
    
    apply_latex_plot_style(ax, "Act 3: Resilience Mitigation (L-Space Target Attack)", "Nodi Rimossi (%)", "Efficienza Globale Residua (%)")
    ax.set_ylim([0, 1.05])
    ax.set_xlim([0, 40])
    ax.legend()
    
    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_resilience_comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    plt.close()
    print(f"✅ Confronto Resilienza salvato: {out_path}")

def plot_tram_impact_map():
    from src.graph import load_cached_graph
    import numpy as np
    
    G_fused = load_cached_graph("G_fused")
    if not G_fused: return
    
    # Estraiamo solo i nodi e gli archi del tram
    tram_nodes = [n for n, d in G_fused.nodes(data=True) if d.get("type") == "tram"]
    tram_edges = [(u, v) for u, v, d in G_fused.edges(data=True) if d.get("type") == "tram"]
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # 1. Plot all network elements first to establish correct axis limits
    pos = {n: (d["lon"], d["lat"]) for n, d in G_fused.nodes(data=True)}
    bus_edges = [(u, v) for u, v, d in G_fused.edges(data=True) if d.get("type") == "bus" and u in pos and v in pos]
    nx.draw_networkx_edges(G_fused, pos, edgelist=bus_edges, ax=ax, edge_color="white", alpha=0.1, width=0.5)
    
    # Disegniamo gli archi tram in modo molto evidente
    nx.draw_networkx_edges(G_fused, pos, edgelist=tram_edges, ax=ax, edge_color="#2ecc71", alpha=0.9, width=3.5)
    nx.draw_networkx_nodes(G_fused, pos, nodelist=tram_nodes, ax=ax, node_color="#2ecc71", node_size=30, edgecolors="white", linewidths=0.5)
    
    # Evidenziamo Stazione Centrale e Autostazione
    target_hubs = ["STAZIONE CENTRALE", "AUTOSTAZIONE"]
    hub_nodes = [n for n, d in G_fused.nodes(data=True) if any(h in d.get("name", "").upper() for h in target_hubs)]
    if hub_nodes:
        nx.draw_networkx_nodes(G_fused, pos, nodelist=hub_nodes, ax=ax, node_color="#e74c3c", node_size=200, edgecolors="white", linewidths=2.0)
        for h in hub_nodes:
            ax.text(pos[h][0], pos[h][1] + 0.0015, "HUB", color="white", fontsize=12, fontweight="bold", ha="center", bbox=dict(facecolor='#e74c3c', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3'))
    
    # 2. Call apply_latex_map_style AFTER elements are plotted so basemap fits bounds perfectly
    apply_latex_map_style(fig, ax, "Act 4: Tram Network Overlay (Linea Rossa & Verde)", dark_mode=True)
    
    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_tram_impact_map.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"✅ Mappa Tram Impact salvata in: {out_path}")

def plot_forced_injection_shock(injection_steps, bus_times, tram_times, futuro_times, opt_times=None):
    bus_mins = [t / 60.0 for t in bus_times]
    tram_mins = [t / 60.0 for t in tram_times]
    futuro_mins = [t / 60.0 for t in futuro_times]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(injection_steps, bus_mins, label="Solo Bus (Congestione)", color="#e74c3c", lw=2.5, marker="o")
    ax.plot(injection_steps, tram_mins, label="Tram Pianificato TPER", color="#2ecc71", lw=2.5, marker="s")
    ax.plot(injection_steps, futuro_mins, label="Tram Pianificato + Circolare 32/33", color="#3498db", lw=2.5, marker="^")
    
    if opt_times is not None:
        opt_mins = [t / 60.0 for t in opt_times]
        ax.plot(injection_steps, opt_mins, label="Tram Ottimizzato (Greedy TNDP)", color="#e67e22", lw=2.5, marker="D")
        max_time = max(max(bus_mins), max(tram_mins), max(futuro_mins), max(opt_mins))
    else:
        max_time = max(max(bus_mins), max(tram_mins), max(futuro_mins))
        
    apply_latex_plot_style(ax, "Act 4: Forced Passenger Injection (Stazione/Autostazione)", "Passeggeri Pendolari Iniettati", "Tempo di Viaggio Medio (Minuti)")
    
    ax.set_ylim([0, max_time + 5])
    ax.legend()
    
    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_forced_injection_shock.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Forced Injection Shock salvato in: {out_path}")

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

    # 5. Demographic pressure maps
    print(" -> Generating demographic pressure maps...")
    plot_demographic_pressure_maps()

    # 6. Communities map
    print(" -> Generating communities map...")
    plot_communities_map()

    print("✅ All plots generated successfully!")
