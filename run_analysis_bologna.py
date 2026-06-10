import os
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt

# --- NUOVI IMPORT ALLINEATI ALLA TUA REPO ---
from src.graph import load_bologna_graph
from src.analyzer import (
    compute_centralities,
    compute_small_worldness,
    compute_demand_weighted_efficiency,
)
from src.simulator import run_resilience_simulation


def main():
    print("=== Phase 1: Data Ingestion & Preprocessing ===")
    os.makedirs("data_output/bologna", exist_ok=True)
    os.makedirs("latex/figures/bologna", exist_ok=True)

    # 1. Caricamento tramite il nuovo graph.py
    G_bus = load_bologna_graph(scenario="bus_only")
    G_tram = load_bologna_graph(scenario="real_tram")

    print("\nBologna Bus-Only Network:")
    print(f"  Stations (Nodes, N): {len(G_bus.nodes)}")
    print(f"  Connections (Edges, M): {len(G_bus.edges)}")
    print(f"  Density (p): {nx.density(G_bus):.6f}")

    print("\nBologna Bus+Tram Network:")
    print(f"  Stations (Nodes, N): {len(G_tram.nodes)}")
    print(f"  Connections (Edges, M): {len(G_tram.edges)}")
    print(f"  Density (p): {nx.density(G_tram):.6f}")

    # Plot network layouts
    pos = {node: (data["lon"], data["lat"]) for node, data in G_tram.nodes(data=True)}

    plt.figure(figsize=(10, 8))
    plt.gca().set_facecolor("#fdfefe")

    # Disegna Archi Bus (Adattato al nuovo attributo 'type')
    bus_edges = [
        (u, v) for u, v, data in G_tram.edges(data=True) if data.get("type") == "bus"
    ]
    nx.draw_networkx_edges(
        G_tram,
        pos,
        edgelist=bus_edges,
        edge_color="#bdc3c7",
        width=1.0,
        alpha=0.5,
        label="Bus Lines",
    )

    # Disegna Archi Tram (Adattato al nuovo attributo 'type')
    tram_edges = [
        (u, v) for u, v, data in G_tram.edges(data=True) if data.get("type") == "tram"
    ]
    nx.draw_networkx_edges(
        G_tram,
        pos,
        edgelist=tram_edges,
        edge_color="#C62828",
        width=3.5,
        alpha=0.9,
        label="Tram Lines",
    )

    # Disegna Nodi
    station_nodes = [
        node for node, data in G_tram.nodes(data=True) if data.get("type") == "bus"
    ]
    tram_nodes = [
        node for node, data in G_tram.nodes(data=True) if data.get("type") == "tram"
    ]

    nx.draw_networkx_nodes(
        G_tram, pos, nodelist=station_nodes, node_size=15, node_color="black", alpha=0.6
    )
    nx.draw_networkx_nodes(
        G_tram,
        pos,
        nodelist=tram_nodes,
        node_size=60,
        node_color="#1976D2",
        node_shape="s",
        label="Tram Stops",
    )

    plt.title(
        "Bologna Integrated Public Transport Network (L-Space)",
        fontsize=13,
        fontweight="bold",
    )
    plt.legend(loc="lower left", frameon=True)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/bologna_tube_map.png", dpi=300)
    plt.close()

    # Save GraphML
    nx.write_graphml(G_tram, "data_output/bologna/bologna_network.graphml")

    print("\n=== Phase 2: Microscopic Centrality Analysis ===")
    df_micro = compute_centralities(G_bus)
    df_micro.to_csv("data_output/bologna/bologna_centralities.csv", index=False)

    print("\nTop 5 Stations by Betweenness Centrality (Bottlenecks):")
    print(
        df_micro.sort_values(by="Betweenness Centrality", ascending=False).head(5)[
            ["Station", "Betweenness Centrality"]
        ]
    )

    print("\n=== Phase 3: Macroscopic Analysis & Small-Worldness ===")
    sw_bus = compute_small_worldness(G_bus)
    sw_tram = compute_small_worldness(G_tram)

    print(f"{'Metrica':<30}{'Rete Bus':<15}{'Rete Bus+Tram':<15}")
    print("-" * 60)
    print(f"{'Avg Path Length L':<30}{sw_bus['L']:.4f}{'':<8}{sw_tram['L']:.4f}")
    print(f"{'Clustering Coeff C':<30}{sw_bus['C']:.4f}{'':<8}{sw_tram['C']:.4f}")
    print(
        f"{'Global Efficiency E_glob':<30}{sw_bus['E_glob']:.4f}{'':<8}{sw_tram['E_glob']:.4f}"
    )

    print("\n=== Phase 4: Resilience Stress-Test ===")
    # Ora il simulatore funzionerà perché il grafo non è direzionato!
    fracs, r_lcc_bus, t_lcc_bus, r_frag_bus, t_frag_bus, r_eff_bus, t_eff_bus = (
        run_resilience_simulation(G_bus, random_runs=10)
    )
    _, r_lcc_tram, t_lcc_tram, r_frag_tram, t_frag_tram, r_eff_tram, t_eff_tram = (
        run_resilience_simulation(G_tram, random_runs=10)
    )

    plt.figure(figsize=(7, 5))
    plt.plot(
        fracs * 100,
        t_lcc_bus,
        "s--",
        color="#e74c3c",
        label="Targeted Attack (Bus Only)",
        linewidth=2,
    )
    plt.plot(
        fracs * 100,
        t_lcc_tram,
        "s-",
        color="#27ae60",
        label="Targeted Attack (Bus+Tram)",
        linewidth=2,
    )
    plt.xlabel("Fraction of Nodes Removed (%)")
    plt.ylabel("Relative Size of LCC")
    plt.title("Connectedness decay (LCC) under Node Removal", fontweight="bold")
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/resilience_lcc.png", dpi=300)
    plt.close()

    print("\n=== Phase 5: Demographic Demand-Weighted Efficiency ===")
    # Il data_loader pulito non restituisce più df_demo. Lo carichiamo direttamente qui se esiste.
    demo_path = "dataset/bologna/bologna_demographics.csv"
    if os.path.exists(demo_path):
        df_demo = pd.read_csv(demo_path)
        eff_bus = compute_demand_weighted_efficiency(G_bus, df_demo)
        eff_real_tram = compute_demand_weighted_efficiency(G_tram, df_demo)

        print("Efficienza di Trasporto Pesata sulla Domanda:")
        print(f"  1. Rete Bus Attuale (Bus Only):                  {eff_bus:.6f}")
        print(
            f"  2. Rete Integrata con Tram Reale (Bus+Tram):      {eff_real_tram:.6f}"
        )
    else:
        print("Dataset Demografico non trovato, salto il calcolo di efficienza pesata.")

    print("\n[SUCCESS] Bologna transit network analysis complete!")


if __name__ == "__main__":
    main()
