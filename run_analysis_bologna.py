import warnings
import pandas as pd
from pathlib import Path

# Importiamo i nostri Specialisti
from src.graph import load_cached_graph
from src.analyzer import (
    compute_centralities,
    compute_small_worldness,
)
from src.demographic import calculate_demographics_weight
from src.simulator import run_resilience_simulation, simulate_targeted_hub_attack
from src.plottings import (
    plot_resilience_curves,
    plot_centrality_analysis,
    plot_static_network,
)
from src.visualize import generate_interactive_map

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "dataset" / "bologna" / "raw"
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"


def main():
    print("\n" + "=" * 110)
    print(
        "🚀 BOLOGNA L-SPACE TRANSIT NETWORK ANALYSIS (WITH PREDICTIVE SCENARIO) 🚀".center(
            110
        )
    )
    print("=" * 110 + "\n")

    # =========================================================================
    print("=== PHASE 1: Data Ingestion & Preprocessing ===")
    # =========================================================================
    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")
    G_multi = load_cached_graph("G_multiplex")

    G_futuro = load_cached_graph("G_futuro")

    print("\n📊 Riepilogo Topologia:")
    print(
        f"  🚌 Solo Bus:        {G_bus.number_of_nodes()} Nodi | {G_bus.number_of_edges()} Archi"
    )
    print(
        f"  🔗 Fused (Bus+Tram):  {G_fused.number_of_nodes()} Nodi | {G_fused.number_of_edges()} Archi"
    )
    print(
        f"  🚶 Multiplex:       {G_multi.number_of_nodes()} Nodi | {G_multi.number_of_edges()} Archi"
    )
    print(
        f"  🔮 Futuro (Circolare): {G_futuro.number_of_nodes()} Nodi | {G_futuro.number_of_edges()} Archi"
    )

    # =========================================================================
    print("\n=== PHASE 2: Microscopic Centrality (Vulnerabilità) ===")
    # =========================================================================
    df_centrality = compute_centralities(G_bus)
    df_top_5 = df_centrality.sort_values(
        by="Betweenness Centrality", ascending=False
    ).head(5)

    print("⚠️ Top 5 Bottlenecks (Vene Giugulari della città):")
    print("-" * 50)
    print(f"{'Stazione':<32} | {'Betweenness Score':<15}")
    print("-" * 50)
    for _, row in df_top_5.iterrows():
        print(f"{row['Station_Name']:<32} | {row['Betweenness Centrality']:.5f}")

    top_node_data = list(zip(df_top_5["Station_ID"], df_top_5["Station_Name"]))

    # =========================================================================
    print("\n=== PHASE 3: Macroscopic Analysis (Efficienza Globale) ===")
    # =========================================================================
    m_bus = compute_small_worldness(G_bus)
    m_fused = compute_small_worldness(G_fused)
    m_multi = compute_small_worldness(G_multi)
    m_futuro = compute_small_worldness(G_futuro)

    print("-" * 115)
    print(
        f"{'Metrica Topologica':<25} | {'🚌 Solo Bus':<16} | {'🔗 Fused':<16} | {'🚶 Multiplex':<16} | {'🔮 Fused+Circolare':<18}"
    )
    print("-" * 115)
    print(
        f"{'Avg Path Length (L)':<25} | {m_bus['L']:<16.4f} | {m_fused['L']:<16.4f} | {m_multi['L']:<16.4f} | {m_futuro['L']:<18.4f}"
    )
    print(
        f"{'Clustering Coeff (C)':<25} | {m_bus['C']:<16.4f} | {m_fused['C']:<16.4f} | {m_multi['C']:<16.4f} | {m_futuro['C']:<18.4f}"
    )
    print(
        f"{'Global Efficiency (E)':<25} | {m_bus['E_glob']:<16.6f} | {m_fused['E_glob']:<16.6f} | {m_multi['E_glob']:<16.6f} | {m_futuro['E_glob']:<18.6f}"
    )
    print(
        f"{'Small-World Sigma (σ)':<25} | {m_bus.get('Sigma', 0.0):<16.2f} | {m_fused.get('Sigma', 0.0):<16.2f} | {m_multi.get('Sigma', 0.0):<16.2f} | {m_futuro.get('Sigma', 0.0):<18.2f}"
    )
    print(
        f"{'Small-World Omega (ω)':<25} | {m_bus.get('Omega', 0.0):<16.2f} | {m_fused.get('Omega', 0.0):<16.2f} | {m_multi.get('Omega', 0.0):<16.2f} | {m_futuro.get('Omega', 0.0):<18.2f}"
    )
    print("-" * 115)

    # =========================================================================
    print("\n=== PHASE 4: Resilience Stress-Test (Attacco ai Bottlenecks) ===")
    # =========================================================================
    print("A) Simulazione di Crollo Infrastrutturale Mirato (Top 5 Hub)...")
    graphs_to_test = {
        "Bus": G_bus,
        "Fused": G_fused,
        "Multi": G_multi,
        "Futuro": G_futuro,
    }
    simulate_targeted_hub_attack(graphs_to_test, top_node_data)

    print(
        "\nB) Simulazione di Percolazione Globale (Random vs Targeted vs Accidents)..."
    )
    print("   -> Calcolo in corso sulla rete integrata Bus+Tram (Scenario Fused)...")

    # [FIX SIMULATORE]: Estratte tutte e 10 le variabili, incluso lo scenario Incidenti!
    (
        fracs,
        rand_lcc,
        targ_lcc,
        acc_lcc,
        rand_frag,
        targ_frag,
        acc_frag,
        rand_eff,
        targ_eff,
        acc_eff,
    ) = run_resilience_simulation(G_fused, random_runs=20)

    df_percolation = pd.DataFrame({
        "Removal_Fraction": fracs,
        "Random_LCC_Size": rand_lcc,
        "Targeted_LCC_Size": targ_lcc,
        "Accidents_LCC_Size": acc_lcc,
        "Random_Efficiency": rand_eff,
        "Targeted_Efficiency": targ_eff,
        "Accidents_Efficiency": acc_eff,
    })
    df_percolation.to_csv(
        PROCESSED_DIR / "resilience_percolation_results.csv", index=False
    )
    print("   ✅ Simulazione completata! Risultati (3 Scenari) salvati in CSV.")

    # =========================================================================
    print("\n=== PHASE 5: Demographic Demand (Pressione Urbana) ===")
    # =========================================================================
    calculate_demographics_weight(G_fused, RAW_DIR)

    # =========================================================================
    print("\n=== PHASE 6: Post-Processing & Visualizations ===")
    # =========================================================================
    # 1. Generate resilience curves
    plot_resilience_curves()

    # 2. Generate centrality correlation scatter plot and betweenness histogram
    plot_centrality_analysis(df_centrality)

    # 3. Generate interactive HTML map
    generate_interactive_map()

    # 4. Generate static map with transparent street basemap
    plot_static_network(G_fused)

    print(
        "\n✅ [SUCCESS] Pipeline analitica, predittiva e di resilienza completata al 100%."
    )


if __name__ == "__main__":
    main()
