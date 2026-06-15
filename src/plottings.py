# src/plottings.py
import sys
from pathlib import Path
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import contextily as ctx

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config import TransitConfig

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
OUTPUT_DIR = BASE_DIR / "latex" / "figures" / "bologna"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Helper functions for DRY styling
def apply_plot_style(ax, title, xlabel, ylabel):
    """Applies a consistent light theme styling for plots."""
    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    ax.set_title(title, fontweight="bold", pad=15)
    ax.set_xlabel(xlabel, fontweight="bold")
    ax.set_ylabel(ylabel, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.7)


def finalize_map(fig, ax, title):
    """Applies light basemap and annotations to a geographic map."""
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.grid(False)  # Disable grid lines for geographic maps

    # Add light basemap (Positron)
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    try:
        ctx.add_basemap(
            ax, crs="EPSG:4326", source=ctx.providers.CartoDB.Positron, alpha=0.85
        )
    except Exception as e:
        print(f"⚠️ Background map error: {e}")
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

    # Format labels
    ax.set_title(title, fontsize=14, fontweight="bold", color="black", pad=15)
    ax.set_xlabel("Longitudine", fontweight="bold", color="black")
    ax.set_ylabel("Latitudine", fontweight="bold", color="black")
    ax.tick_params(colors="black")


def draw_transit_network(ax, G, pos, tram_color, bus_color="#bdc3c7"):
    """Helper to draw transit network layout (bus/tram edges and tram nodes) on a given axis."""
    # Bus edges
    bus_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("type") == "bus" and u in pos and v in pos
    ]
    nx.draw_networkx_edges(
        G, pos, edgelist=bus_edges, ax=ax, edge_color=bus_color, width=0.8, alpha=0.3
    )

    # Tram edges
    tram_edges = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get("type") == "tram" and u in pos and v in pos
    ]
    nx.draw_networkx_edges(
        G, pos, edgelist=tram_edges, ax=ax, edge_color=tram_color, width=2.5, alpha=0.9
    )

    # Tram nodes (azure/light blue)
    tram_nodes = [
        n
        for n, d in G.nodes(data=True)
        if d.get("type") in ["tram", "intersezione_bus_tram"] and n in pos
    ]
    if tram_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=tram_nodes,
            ax=ax,
            node_color="#3498db",
            node_size=30,
            edgecolors="white",
            linewidths=0.5,
            alpha=0.9,
        )


def plot_resilience_curves():
    csv_path = PROCESSED_DIR / "resilience_percolation_results.csv"
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    x = df["Removal_Fraction"] * 100

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    c_rand = "#2ecc71"  # Green
    c_targ = "#e74c3c"  # Red
    c_acc = "#f39c12"  # Orange

    # Subplot 1: LCC Size
    ax1.plot(
        x, df["Random_LCC_Size"], label="Random Failure", color=c_rand, lw=2.5, ls="--"
    )
    ax1.plot(
        x, df["Targeted_LCC_Size"], label="Targeted Attack (Hubs)", color=c_targ, lw=2.5
    )
    ax1.plot(
        x,
        df["Accidents_LCC_Size"],
        label="Accident Risk",
        color=c_acc,
        lw=2.5,
        marker="o",
        ms=4,
    )
    apply_plot_style(
        ax1,
        "Topological Resilience (LCC Fragmentation)",
        "Removed Nodes (%)",
        "Giant Component Size (LCC)",
    )
    ax1.set_ylim([0, 1.05])
    ax1.set_xlim([0, 50])
    ax1.legend()

    # Subplot 2: Efficiency
    ax2.plot(
        x,
        df["Random_Efficiency"],
        label="Random Failure",
        color=c_rand,
        lw=2.5,
        ls="--",
    )
    ax2.plot(
        x,
        df["Targeted_Efficiency"],
        label="Targeted Attack (Hubs)",
        color=c_targ,
        lw=2.5,
    )
    ax2.plot(
        x,
        df["Accidents_Efficiency"],
        label="Accident Risk",
        color=c_acc,
        lw=2.5,
        marker="o",
        ms=4,
    )
    apply_plot_style(
        ax2,
        "Dynamic Resilience (Travel Times)",
        "Removed Nodes (%)",
        "Residual Global Efficiency",
    )
    ax2.set_ylim([0, 1.05])
    ax2.set_xlim([0, 50])
    ax2.legend()

    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_resilience_curves.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Resilience curves saved to: {output_path}")


def plot_centrality_analysis(df_cent_bus=None, df_cent_tram=None):
    from src.graph import load_cached_graph
    from src.analyzer import compute_centralities

    if df_cent_bus is None:
        G_bus = load_cached_graph("G_bus")
        df_cent_bus = compute_centralities(G_bus)
    if df_cent_tram is None:
        G_fused = load_cached_graph("G_fused")
        df_cent_tram = compute_centralities(G_fused)

    sns.set_theme(style="whitegrid", context="paper", font_scale=1.2)

    # 1. SCATTER PLOT
    fig, ax = plt.subplots(figsize=(9, 6))

    # Bus Only (Blue)
    sns.regplot(
        data=df_cent_bus,
        x="Degree",
        y="Betweenness Centrality",
        x_jitter=0.15,
        scatter_kws={"alpha": 0.4, "color": "#3498db", "edgecolor": None},
        line_kws={"color": "#2980b9", "linewidth": 2.0, "label": "Trend: Bus Only"},
        ax=ax,
    )
    # Planned Tram (Green)
    sns.regplot(
        data=df_cent_tram,
        x="Degree",
        y="Betweenness Centrality",
        x_jitter=0.15,
        scatter_kws={"alpha": 0.4, "color": "#2ecc71", "edgecolor": None},
        line_kws={"color": "#27ae60", "linewidth": 2.0, "label": "Trend: Planned Tram"},
        ax=ax,
    )

    # Highlight top 5 bottlenecks
    top_5_bus = df_cent_bus.nlargest(5, "Betweenness Centrality")
    sns.scatterplot(
        data=top_5_bus,
        x="Degree",
        y="Betweenness Centrality",
        color="#2980b9",
        s=120,
        marker="o",
        edgecolor="black",
        linewidth=1.5,
        ax=ax,
        label="Bus Only Bottlenecks",
    )

    top_5_tram = df_cent_tram.nlargest(5, "Betweenness Centrality")
    sns.scatterplot(
        data=top_5_tram,
        x="Degree",
        y="Betweenness Centrality",
        color="#27ae60",
        s=120,
        marker="s",
        edgecolor="black",
        linewidth=1.5,
        ax=ax,
        label="Planned Tram Bottlenecks",
    )

    # Labels for top bottlenecks (using B1-B5 on the right, and T1-T5 on the left)
    for idx, (_, row) in enumerate(top_5_bus.iterrows()):
        ax.text(
            row["Degree"] + 0.18,
            row["Betweenness Centrality"],
            f"B{idx + 1}",
            color="#2980b9",
            fontsize=9,
            fontweight="bold",
            ha="left",
            va="center",
            bbox=dict(
                facecolor="white",
                edgecolor="#2980b9",
                boxstyle="circle,pad=0.15",
                alpha=0.95,
            ),
        )

    for idx, (_, row) in enumerate(top_5_tram.iterrows()):
        ax.text(
            row["Degree"] - 0.18,
            row["Betweenness Centrality"],
            f"T{idx + 1}",
            color="#27ae60",
            fontsize=9,
            fontweight="bold",
            ha="right",
            va="center",
            bbox=dict(
                facecolor="white",
                edgecolor="#27ae60",
                boxstyle="circle,pad=0.15",
                alpha=0.95,
            ),
        )

    # Add descriptive legend box
    legend_text = (
        "Bottlenecks Legend\n\n"
        "Bus Only:\n"
        "  B1: FARINI\n"
        "  B2: PIAZZA CAVOUR\n"
        "  B3: GARGANELLI\n"
        "  B4: PORTA SANTO STEFANO\n"
        "  B5: MARCONI\n\n"
        "Planned Tram:\n"
        "  T1: FARINI\n"
        "  T2: PIAZZA DELL'UNITA'\n"
        "  T3: MATTEOTTI A.V.\n"
        "  T4: UGO BASSI\n"
        "  T5: SAN FELICE"
    )
    ax.text(
        0.65,
        0.20,
        legend_text,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        color="black",
        verticalalignment="bottom",
        bbox=dict(
            facecolor="white", alpha=0.95, edgecolor="#bdc3c7", boxstyle="round,pad=0.4"
        ),
    )

    apply_plot_style(
        ax,
        "Node Degree vs Betweenness Centrality Comparison",
        "Node Degree",
        "Betweenness Centrality (Weighted)",
    )
    ax.legend(loc="upper left")
    plt.tight_layout()
    output_path_scatter = OUTPUT_DIR / "bologna_centrality_scatter.png"
    plt.savefig(output_path_scatter, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Centrality scatter plot saved to: {output_path_scatter}")

    # 2. HISTOGRAM
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(
        data=df_cent_bus[df_cent_bus["Betweenness Centrality"] > 0],
        x="Betweenness Centrality",
        kde=True,
        color="#3498db",
        bins=30,
        ax=ax,
        stat="density",
        alpha=0.4,
        label="Bus Only",
    )
    sns.histplot(
        data=df_cent_tram[df_cent_tram["Betweenness Centrality"] > 0],
        x="Betweenness Centrality",
        kde=True,
        color="#2ecc71",
        bins=30,
        ax=ax,
        stat="density",
        alpha=0.4,
        label="Planned Tram",
    )
    apply_plot_style(
        ax,
        "Betweenness Centrality Distribution (Values > 0)",
        "Betweenness Centrality",
        "Density",
    )
    ax.legend()
    plt.tight_layout()
    output_path_hist = OUTPUT_DIR / "bologna_betweenness_hist.png"
    plt.savefig(output_path_hist, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Betweenness histogram saved to: {output_path_hist}")


def plot_static_network(G):
    """Plots a light-theme static layout of the integrated network."""
    fig, ax = plt.subplots(figsize=(12, 10))
    pos = {
        n: (d["lon"], d["lat"])
        for n, d in G.nodes(data=True)
        if "lon" in d and "lat" in d
    }

    # 1. Bus edges (grouped and colored softly)
    bus_edges_by_route = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get("type") == "bus" and u in pos and v in pos:
            route_id = str(data.get("route_id", "default"))
            bus_edges_by_route[route_id].append((u, v))

    def get_bus_color(route_id):
        colors = [
            "#a8a5e6",
            "#8be0cf",
            "#ebdca0",
            "#a5b4c4",
            "#ecc2a0",
            "#86ccba",
            "#c7a0eb",
            "#eba6a0",
        ]
        return colors[hash(str(route_id)) % len(colors)]

    for route_id, edgelist in bus_edges_by_route.items():
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=edgelist,
            ax=ax,
            edge_color=get_bus_color(route_id),
            width=0.8,
            alpha=0.35,
        )

    # 2. Tram edges (Red and Green lines)
    tram_edges_by_route = defaultdict(list)
    for u, v, data in G.edges(data=True):
        if data.get("type") == "tram" and u in pos and v in pos:
            route_id = str(data.get("route_id", "default")).upper()
            tram_edges_by_route[route_id].append((u, v))

    for route_id, edgelist in tram_edges_by_route.items():
        color = "#e74c3c" if any(k in route_id for k in ["RED", "ROSSA"]) else "#2ecc71"
        nx.draw_networkx_edges(
            G, pos, edgelist=edgelist, ax=ax, edge_color=color, width=3.0, alpha=0.85
        )

    # 3. Nodes
    bus_nodes = [
        n for n, d in G.nodes(data=True) if d.get("type") == "bus" and n in pos
    ]
    nx.draw_networkx_nodes(
        G, pos, nodelist=bus_nodes, ax=ax, node_color="#bdc3c7", node_size=8, alpha=0.4
    )

    # All tram nodes (both 'tram' and 'intersezione_bus_tram') painted Azure
    tram_nodes = [
        n
        for n, d in G.nodes(data=True)
        if d.get("type") in ["tram", "intersezione_bus_tram"] and n in pos
    ]
    if tram_nodes:
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=tram_nodes,
            ax=ax,
            node_color="#3498db",
            node_size=35,
            edgecolors="white",
            linewidths=0.5,
            alpha=0.95,
        )

    finalize_map(fig, ax, "Topological Map of Bologna Integrated Network (Bus & Tram)")
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_static_network.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Static network map saved to: {output_path}")


def plot_optimized_layout(G_planned, G_opt):
    """Side-by-side planned vs optimal tramway layout comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    pos_planned = {
        n: (d["lon"], d["lat"])
        for n, d in G_planned.nodes(data=True)
        if "lon" in d and "lat" in d
    }
    pos_opt = {
        n: (d["lon"], d["lat"])
        for n, d in G_opt.nodes(data=True)
        if "lon" in d and "lat" in d
    }

    # 1. Planned Layout Subplot
    draw_transit_network(ax1, G_planned, pos_planned, tram_color="#e74c3c")
    finalize_map(fig, ax1, "Planned Tram")

    # 2. Optimal Layout Subplot
    draw_transit_network(ax2, G_opt, pos_opt, tram_color="#9b59b6")
    finalize_map(fig, ax2, "Optimal Tram")

    budget_km = int(TransitConfig.OPTIMAL_TRAM_BUDGET_METERS / 1000)
    plt.suptitle(
        f"Bologna: Planned vs Optimal Layout Comparison ({budget_km} km Budget)",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_optimized_layout.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Layout comparison map saved to: {output_path}")


def plot_demographic_pressure_maps():
    """Generates the demographic pressure KDE density map (light theme)."""
    csv_tram = BASE_DIR / "data_output" / "bologna" / "demographic_tram_results.csv"
    if not csv_tram.exists():
        print("⚠️ Demographic results not found.")
        return

    df_tram = pd.read_csv(csv_tram)
    df_tram = df_tram[df_tram["Population_Served"] > 0]

    fig, ax = plt.subplots(figsize=(12, 10))
    # Draw tiny station dots to give spatial context
    ax.scatter(
        df_tram["Longitude"],
        df_tram["Latitude"],
        color="#7f8c8d",
        s=10,
        alpha=0.4,
        label="Stations",
    )
    # Draw soft, transparent demographic pressure contour density
    sns.kdeplot(
        data=df_tram,
        x="Longitude",
        y="Latitude",
        weights="Population_Served",
        fill=True,
        cmap="YlOrRd",
        alpha=0.35,
        levels=15,
        thresh=0.08,
        ax=ax,
    )

    finalize_map(fig, ax, "Exogenous Stress: Demographic Pressure Density (ISTAT)")
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_demographic_pressure_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Demographic pressure map saved to: {output_path}")


def plot_communities_map():
    csv_comm = BASE_DIR / "data_output" / "bologna" / "communities_bus.csv"
    if not csv_comm.exists():
        print("⚠️ communities_bus.csv not found.")
        return

    df_comm = pd.read_csv(csv_comm)
    df_comm = df_comm[df_comm["Community_ID"] >= 0]

    fig, ax = plt.subplots(figsize=(12, 10))
    sns.scatterplot(
        data=df_comm,
        x="Longitude",
        y="Latitude",
        hue="Community_ID",
        palette="tab20",
        s=60,
        alpha=0.8,
        edgecolor="white",
        legend=False,
        ax=ax,
    )

    finalize_map(fig, ax, "Act 1: P-Space Sociological Communities (Louvain)")
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_communities_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Communities map saved to: {output_path}")


def plot_bottlenecks_map():
    from src.graph import load_cached_graph
    from src.analyzer import compute_centralities

    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")

    df_bus = compute_centralities(G_bus)
    df_tram = compute_centralities(G_fused)

    df_bus = df_bus[df_bus["Betweenness Centrality"] > 0]
    df_tram = df_tram[df_tram["Betweenness Centrality"] > 0]

    fig, ax = plt.subplots(figsize=(12, 10))

    # Plot Bus Only in grayscale
    sns.scatterplot(
        data=df_bus,
        x="Longitude",
        y="Latitude",
        size="Betweenness Centrality",
        color="#7f8c8d",
        sizes=(20, 500),
        alpha=0.5,
        legend=False,
        ax=ax,
    )
    # Plot Planned Tram in grayscale
    sns.scatterplot(
        data=df_tram,
        x="Longitude",
        y="Latitude",
        size="Betweenness Centrality",
        color="#95a5a6",
        sizes=(20, 500),
        alpha=0.5,
        legend=False,
        ax=ax,
    )

    # Highlight top 5 Bus Only bottlenecks as large colored circles
    top_5_bus = df_bus.nlargest(5, "Betweenness Centrality")
    sns.scatterplot(
        data=top_5_bus,
        x="Longitude",
        y="Latitude",
        color="#2980b9",
        s=180,
        edgecolor="black",
        linewidth=1.5,
        legend=False,
        ax=ax,
    )
    # Highlight top 5 Planned Tram bottlenecks as large colored circles
    top_5_tram = df_tram.nlargest(5, "Betweenness Centrality")
    sns.scatterplot(
        data=top_5_tram,
        x="Longitude",
        y="Latitude",
        color="#27ae60",
        s=180,
        edgecolor="black",
        linewidth=1.5,
        legend=False,
        ax=ax,
    )

    # Draw numbers centered on the highlighted nodes (B1-B5 and T1-T5)
    for idx, (_, row) in enumerate(top_5_bus.iterrows()):
        is_shared = row['Station_Name'] in top_5_tram['Station_Name'].values
        offset_x = -0.0008 if is_shared else 0.0
        ax.text(
            row["Longitude"] + offset_x,
            row["Latitude"],
            f"B{idx + 1}",
            color="white",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(
                facecolor="#2980b9",
                edgecolor="white",
                boxstyle="circle,pad=0.25",
                alpha=0.95,
                lw=1.0
            ),
        )
    for idx, (_, row) in enumerate(top_5_tram.iterrows()):
        is_shared = row['Station_Name'] in top_5_bus['Station_Name'].values
        offset_x = 0.0008 if is_shared else 0.0
        ax.text(
            row["Longitude"] + offset_x,
            row["Latitude"],
            f"T{idx + 1}",
            color="white",
            fontsize=8,
            fontweight="bold",
            ha="center",
            va="center",
            bbox=dict(
                facecolor="#27ae60",
                edgecolor="white",
                boxstyle="circle,pad=0.25",
                alpha=0.95,
                lw=1.0
            ),
        )

    # Add a nice, clean legend panel at the bottom-left corner of the map
    legend_text = (
        "Top Bottlenecks Legend\n\n"
        "Bus Only:\n"
        "  B1: FARINI\n"
        "  B2: PIAZZA CAVOUR\n"
        "  B3: GARGANELLI\n"
        "  B4: PORTA SANTO STEFANO\n"
        "  B5: MARCONI\n\n"
        "Planned Tram:\n"
        "  T1: FARINI\n"
        "  T2: PIAZZA DELL'UNITA'\n"
        "  T3: MATTEOTTI A.V.\n"
        "  T4: UGO BASSI\n"
        "  T5: SAN FELICE"
    )
    ax.text(
        0.02,
        0.02,
        legend_text,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        color="black",
        verticalalignment="bottom",
        bbox=dict(
            facecolor="white", alpha=0.95, edgecolor="#bdc3c7", boxstyle="round,pad=0.5"
        ),
    )

    finalize_map(
        fig,
        ax,
        "Act 2: Physical Bottlenecks Comparison (L-Space Betweenness Centrality)",
    )
    plt.tight_layout()
    output_path = OUTPUT_DIR / "bologna_bottlenecks_map.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Bottlenecks comparison map saved to: {output_path}")


def plot_comparative_resilience():
    from src.graph import load_cached_graph
    from src.simulator import simulate_removal, compute_weighted_global_efficiency
    import numpy as np

    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")
    if not G_bus or not G_fused:
        return

    fractions = np.linspace(0, 0.4, 20)
    eff_bus_base = compute_weighted_global_efficiency(G_bus) or 1.0
    eff_fused_base = compute_weighted_global_efficiency(G_fused) or 1.0

    bus_bet = nx.betweenness_centrality(G_bus, weight="weight")
    sorted_bus = [
        k for k, v in sorted(bus_bet.items(), key=lambda item: item[1], reverse=True)
    ]
    fused_bet = nx.betweenness_centrality(G_fused, weight="weight")
    sorted_fused = [
        k for k, v in sorted(fused_bet.items(), key=lambda item: item[1], reverse=True)
    ]

    bus_eff_drops, fused_eff_drops = [], []
    for f in fractions:
        _, _, e_b = simulate_removal(
            G_bus, f, scenario="targeted", sorted_nodes=sorted_bus
        )
        bus_eff_drops.append(e_b / eff_bus_base)
        _, _, e_f = simulate_removal(
            G_fused, f, scenario="targeted", sorted_nodes=sorted_fused
        )
        fused_eff_drops.append(e_f / eff_fused_base)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        fractions * 100,
        bus_eff_drops,
        label="Bus Only",
        color="#e74c3c",
        lw=2.5,
        marker="o",
    )
    ax.plot(
        fractions * 100,
        fused_eff_drops,
        label="Planned Tram",
        color="#2ecc71",
        lw=2.5,
        marker="s",
    )

    apply_plot_style(
        ax,
        "Act 3: Resilience Mitigation (L-Space Target Attack)",
        "Removed Nodes (%)",
        "Residual Global Efficiency (%)",
    )
    ax.set_ylim([0, 1.05])
    ax.set_xlim([0, 40])
    ax.legend()

    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_resilience_comparison.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Comparative resilience plot saved to: {out_path}")


def plot_tram_impact_map():
    from src.graph import load_cached_graph

    G_fused = load_cached_graph("G_fused")
    if not G_fused:
        return

    fig, ax = plt.subplots(figsize=(12, 10))
    pos = {n: (d["lon"], d["lat"]) for n, d in G_fused.nodes(data=True)}

    # Draw transit network
    draw_transit_network(ax, G_fused, pos, tram_color="#2ecc71")

    # Highlight main inter-modal hubs
    target_hubs = ["STAZIONE CENTRALE", "AUTOSTAZIONE"]
    hub_nodes = [
        n
        for n, d in G_fused.nodes(data=True)
        if any(h in d.get("name", "").upper() for h in target_hubs)
    ]
    if hub_nodes:
        nx.draw_networkx_nodes(
            G_fused,
            pos,
            nodelist=hub_nodes,
            ax=ax,
            node_color="#e74c3c",
            node_size=150,
            edgecolors="white",
            linewidths=1.5,
        )
        for h in hub_nodes:
            ax.text(
                pos[h][0],
                pos[h][1] + 0.0012,
                "HUB",
                color="white",
                fontsize=10,
                fontweight="bold",
                ha="center",
                bbox=dict(
                    facecolor="#e74c3c",
                    alpha=0.85,
                    edgecolor="none",
                    boxstyle="round,pad=0.25",
                ),
            )

    finalize_map(fig, ax, "Planned Tram Overlay")
    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_tram_impact_map.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Tram overlay map saved to: {out_path}")


def plot_forced_injection_shock(
    injection_steps, bus_times, tram_times, futuro_times, opt_times=None
):
    bus_mins = [t / 60.0 for t in bus_times]
    tram_mins = [t / 60.0 for t in tram_times]
    futuro_mins = [t / 60.0 for t in futuro_times]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        injection_steps, bus_mins, label="Bus Only", color="#e74c3c", lw=2.5, marker="o"
    )
    ax.plot(
        injection_steps,
        tram_mins,
        label="Planned Tram",
        color="#2ecc71",
        lw=2.5,
        marker="s",
    )
    ax.plot(
        injection_steps,
        futuro_mins,
        label="Circular Tram",
        color="#3498db",
        lw=2.5,
        marker="^",
    )

    if opt_times is not None:
        opt_mins = [t / 60.0 for t in opt_times]
        ax.plot(
            injection_steps,
            opt_mins,
            label="Optimal Tram",
            color="#9b59b6",
            lw=2.5,
            marker="D",
        )
        max_time = max(max(bus_mins), max(tram_mins), max(futuro_mins), max(opt_mins))
    else:
        max_time = max(max(bus_mins), max(tram_mins), max(futuro_mins))

    apply_plot_style(
        ax,
        "Act 4: Forced Passenger Injection (Stazione/Autostazione Shock)",
        "Injected Commuters",
        "Average Travel Time (Minutes)",
    )
    ax.set_ylim([0, max_time + 5])
    ax.legend()

    plt.tight_layout()
    out_path = OUTPUT_DIR / "bologna_forced_injection_shock.png"
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"✅ Forced Injection Shock curve saved to: {out_path}")


if __name__ == "__main__":
    from src.graph import load_cached_graph
    from src.analyzer import compute_centralities

    print("📊 Generating all light-theme plots...")
    plot_resilience_curves()

    G_bus = load_cached_graph("G_bus")
    df_cent = compute_centralities(G_bus)
    plot_centrality_analysis(df_cent)

    G_fused = load_cached_graph("G_fused")
    plot_static_network(G_fused)

    G_opt = load_cached_graph("G_opt_tram")
    plot_optimized_layout(G_fused, G_opt)
    plot_demographic_pressure_maps()
    plot_communities_map()
    plot_bottlenecks_map()
    plot_comparative_resilience()
    plot_tram_impact_map()

    print("✅ All light-theme plots generated successfully!")
