import warnings
import pandas as pd
import numpy as np
import networkx as nx
from pathlib import Path

# Importiamo i nostri Specialisti
from src.graph import load_cached_graph, load_pspace_graph
from src.analyzer import (
    compute_centralities,
    compute_small_worldness,
    compute_weighted_global_efficiency,
    compute_assortativity,
)
from src.demographic import calculate_demographics_weight
from src.simulator import run_resilience_simulation, simulate_targeted_hub_attack
from src.plottings import (
    plot_resilience_curves,
    plot_centrality_analysis,
    plot_static_network,
    plot_comparative_resilience,
    plot_tram_impact_map,
    plot_forced_injection_shock,
    plot_communities_map,
    plot_bottlenecks_map,
    plot_optimized_layout,
    plot_demographic_pressure_maps,
)

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "dataset" / "bologna" / "raw"
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
OUTPUT_DIR = BASE_DIR / "data_output" / "bologna"

def get_tram_coverage(G):
    tram_stops = [
        n
        for n, d in G.nodes(data=True)
        if d.get("type") in ["tram", "intersezione_bus_tram"]
    ]
    unique_stops = {}
    for ts in tram_stops:
        name = G.nodes[ts].get("name", str(ts)).strip().upper()
        pop = G.nodes[ts].get("population_served", 0.0)
        unique_stops[name] = max(unique_stops.get(name, 0.0), pop)
    return sum(unique_stops.values()), len(unique_stops)

def main():
    print("\n" + "=" * 110)
    print("🚀 MASTER PIPELINE: BOLOGNA TRANSIT NETWORK SNA ANALYSIS 🚀".center(110))
    print("=" * 110 + "\n")

    # Caricamento dei grafi in L-Space
    print("📥 Loading L-Space networks...")
    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")
    G_futuro = load_cached_graph("G_futuro")
    G_opt = load_cached_graph("G_opt_tram")
    
    # Assicuriamoci che tutti i grafi L-Space abbiano pesi demografici e dwell times aggiornati
    print("📊 Ensuring demographics are snapped and L-Space travel times are loaded...")
    calculate_demographics_weight(G_bus, RAW_DIR)
    calculate_demographics_weight(G_fused, RAW_DIR)
    calculate_demographics_weight(G_futuro, RAW_DIR)
    if G_opt:
        calculate_demographics_weight(G_opt, RAW_DIR)

    # --- ACT 1: COGNITIVE TOPOLOGY (P-SPACE) ---
    print("\n" + "=" * 110)
    print("🎭 ACT 1: COGNITIVE TOPOLOGY (P-SPACE) ANALYSIS".center(110))
    print("=" * 110)
    
    print(" -> Loading P-Space networks...")
    G_pspace_bus = load_pspace_graph("bus_only")
    G_pspace_fused = load_pspace_graph("fused")
    
    print(" -> Computing cognitive degree assortativity...")
    assort_bus = compute_assortativity(G_pspace_bus)
    assort_fused = compute_assortativity(G_pspace_fused)
    
    print("\n📈 Act 1 Metrics and Comparisons:")
    print(f"  - Bus-Only P-Space: {G_pspace_bus.number_of_nodes()} stops, {G_pspace_bus.number_of_edges()} cognitive edges.")
    print(f"  - Planned Tram P-Space: {G_pspace_fused.number_of_nodes()} stops, {G_pspace_fused.number_of_edges()} cognitive edges.")
    print(f"  - Degree Assortativity (Bus Only):  r = {assort_bus:.4f}")
    print(f"  - Degree Assortativity (Planned Tram): r = {assort_fused:.4f}")

    # Coesione e struttura core-periferia (densita' e k-core, citate nel report)
    dens_lspace = nx.density(G_bus)
    dens_pspace = nx.density(G_pspace_bus)
    core_pspace = nx.core_number(G_pspace_bus)
    k_max = max(core_pspace.values())
    inner_core_size = sum(1 for v in core_pspace.values() if v == k_max)
    print(f"  - Density: L-Space (bus) = {dens_lspace:.5f} | P-Space (bus) = {dens_pspace:.4f}")
    print(f"  - P-Space k-core (bus): {len(set(core_pspace.values()))} shells, innermost k = {k_max} with {inner_core_size} stops")
    
    # Salviamo i risultati dell'assortatività
    with open(OUTPUT_DIR / "assortativity_results.txt", "w") as f:
        f.write(f"Assortativity (P-Space Bus): {assort_bus:.4f}\n")
        f.write(f"Assortativity (P-Space Fused): {assort_fused:.4f}\n")

    print("\n -> Generating communities map plot...")
    plot_communities_map()

    # --- ACT 2: PHYSICAL BOTTLENECKS (L-SPACE) ---
    print("\n" + "=" * 110)
    print("🏭 ACT 2: L-SPACE PHYSICAL BOTTLENECKS & CENTRALITY CORRELATIONS".center(110))
    print("=" * 110)
    
    print(" -> Computing Betweenness Centrality on travel times...")
    df_cent_bus = compute_centralities(G_bus)
    df_cent_tram = compute_centralities(G_fused)
    
    # Salviamo i risultati delle centralità
    df_cent_bus.to_csv(OUTPUT_DIR / "centrality_results.csv", index=False)
    
    # Stampa Tabella Comparativa Bottleneck (Table 2 nel Report)
    print("\n🏆 Top 5 L-Space Betweenness Centrality Bottlenecks Comparison:")
    print("-" * 110)
    print(f"{'Rank':<5} | {'Bus Only (Baseline) Station':<35} | {'Score':<10} | {'Planned Tram (TPER) Station':<35} | {'Score':<10}")
    print("-" * 110)
    top_5_bus = df_cent_bus.nlargest(5, "Betweenness Centrality")
    top_5_tram = df_cent_tram.nlargest(5, "Betweenness Centrality")
    for idx in range(5):
        bus_row = top_5_bus.iloc[idx]
        tram_row = top_5_tram.iloc[idx]
        print(f"{idx+1:<5} | {bus_row['Station_Name']:<35} | {bus_row['Betweenness Centrality']:<10.5f} | {tram_row['Station_Name']:<35} | {tram_row['Betweenness Centrality']:<10.5f}")
    print("-" * 110)
    
    print("\n -> Generating comparative centrality plots (overlaid scatter, hist, map)...")
    plot_centrality_analysis(df_cent_bus, df_cent_tram)
    plot_bottlenecks_map(df_cent_bus, df_cent_tram)

    # --- L-SPACE MACROSCOPIC METRICS ---
    print("\n" + "=" * 110)
    print("🌐 L-SPACE MACROSCOPIC METRICS & NULL-MODEL COMPARISON (TABLE 3)".center(110))
    print("=" * 110)
    
    print(" -> Computing macroscopic metrics (Small-Worldness & Efficiency)...")
    macro_bus = compute_small_worldness(G_bus, er_runs=5)
    macro_fused = compute_small_worldness(G_fused, er_runs=5)
    
    # Stampiamo la Tabella 3 del Report
    print("\n📊 Table 3: Macroscopic Network Metrics (Loaded Travel Times):")
    print("-" * 80)
    print(f"{'Metric':<40} | {'Bus Only (Baseline)':<18} | {'Planned Tram (TPER)':<18}")
    print("-" * 80)
    print(f"{'Nodes (N_lcc)':<40} | {macro_bus['N']:<18} | {macro_fused['N']:<18}")
    print(f"{'Edges (M_lcc)':<40} | {macro_bus['M']:<18} | {macro_fused['M']:<18}")
    print(f"{'Avg Travel Time L (sec)':<40} | {macro_bus['L']:<18.2f} | {macro_fused['L']:<18.2f}")
    print(f"{'Clustering Coeff (C)':<40} | {macro_bus['C']:<18.4f} | {macro_fused['C']:<18.4f}")
    print(f"{'Global Efficiency E_glob (s^-1)':<40} | {macro_bus['E_glob']:<18.6f} | {macro_fused['E_glob']:<18.6f}")
    print(f"{'Small-World Sigma (sigma)':<40} | {macro_bus['Sigma']:<18.2f} | {macro_fused['Sigma']:<18.2f}")
    print(f"{'Small-World Omega (omega)':<40} | {macro_bus['Omega']:<18.2f} | {macro_fused['Omega']:<18.2f}")
    print("-" * 80)

    # Salviamo i risultati macroscopici
    df_macro = pd.DataFrame([
        {"Scenario": "Bus Only", "N": macro_bus['N'], "M": macro_bus['M'], "L": macro_bus['L'], "C": macro_bus['C'], "E_glob": macro_bus['E_glob'], "Sigma": macro_bus['Sigma'], "Omega": macro_bus['Omega']},
        {"Scenario": "Planned Tram", "N": macro_fused['N'], "M": macro_fused['M'], "L": macro_fused['L'], "C": macro_fused['C'], "E_glob": macro_fused['E_glob'], "Sigma": macro_fused['Sigma'], "Omega": macro_fused['Omega']}
    ])
    df_macro.to_csv(OUTPUT_DIR / "macroscopic_results.csv", index=False)

    # --- ACT 3: RESILIENCE STRESS-TESTS ---
    print("\n" + "=" * 110)
    print("🛡️ ACT 3: RESILIENCE STRESS-TESTS & PERCOLATION ANALYSIS".center(110))
    print("=" * 110)
    
    print(" -> Running sequential targeted attack drops (Table 4 in Report)...")
    graphs_dict = {
        "Bus Only": G_bus,
        "Planned Tram": G_fused
    }
    simulate_targeted_hub_attack(graphs_dict, num_steps=5)
    
    print("\n -> Simulating global percolation curves (Random vs Accidents vs Targeted)...")
    (fracs, rand_lcc, targ_lcc, acc_lcc, rand_frag, targ_frag, acc_frag, rand_eff, targ_eff, acc_eff) = run_resilience_simulation(G_bus, random_runs=20)
    
    df_percolation = pd.DataFrame({
        "Removal_Fraction": fracs,
        "Random_LCC_Size": rand_lcc,
        "Targeted_LCC_Size": targ_lcc,
        "Accidents_LCC_Size": acc_lcc,
        "Random_Efficiency": rand_eff,
        "Targeted_Efficiency": targ_eff,
        "Accidents_Efficiency": acc_eff
    })
    df_percolation.to_csv(PROCESSED_DIR / "resilience_percolation_results.csv", index=False)
    
    print(" -> Generating resilience curves and comparative resilience plots...")
    plot_resilience_curves()
    plot_comparative_resilience()

    # --- ACT 4: FUTURE SCENARIOS & SHOCK INJECTION ---
    print("\n" + "=" * 110)
    print("🚄 ACT 4: FUTURE SCENARIOS COMPARATIVE PERFORMANCE & SHOCK INJECTION".center(110))
    print("=" * 110)
    
    # Calcolo metriche per i 4 scenari futuristici
    print(" -> Computing comparative metrics for future scenarios...")
    
    l_bus = macro_bus['L']
    eff_bus = macro_bus['E_glob']
    pop_bus = 0
    
    l_planned = macro_fused['L']
    eff_planned = macro_fused['E_glob']
    pop_planned, _ = get_tram_coverage(G_fused)
    
    l_circular = nx.average_shortest_path_length(
        G_futuro if nx.is_connected(G_futuro) else G_futuro.subgraph(max(nx.connected_components(G_futuro), key=len)),
        weight="weight"
    )
    eff_circular = compute_weighted_global_efficiency(G_futuro)
    pop_circular, _ = get_tram_coverage(G_futuro)
    
    if G_opt:
        l_opt = nx.average_shortest_path_length(
            G_opt if nx.is_connected(G_opt) else G_opt.subgraph(max(nx.connected_components(G_opt), key=len)),
            weight="weight"
        )
        eff_opt = compute_weighted_global_efficiency(G_opt)
        pop_opt, _ = get_tram_coverage(G_opt)
    else:
        l_opt = 0.0
        eff_opt = 0.0
        pop_opt = 0
        
    print("\n🏆 Table 5: Comparative Performance under Demographic Load:")
    print("-" * 95)
    print(f"{'Scenario':<28} | {'Avg Travel Time L (sec)':<25} | {'Global Efficiency E_glob (s^-1)':<32} | {'Tram Pop Served':<15}")
    print("-" * 95)
    print(f"{'Bus Only':<28} | {l_bus:<25.2f} | {eff_bus:<32.6f} | {'N/D':<15}")
    print(f"{'Planned Tram':<28} | {l_planned:<25.2f} | {eff_planned:<32.6f} | {int(pop_planned):<15,}")
    print(f"{'Circular Tram':<28} | {l_circular:<25.2f} | {eff_circular:<32.6f} | {int(pop_circular):<15,}")
    if G_opt:
        print(f"{'Optimal Tram':<28} | {l_opt:<25.2f} | {eff_opt:<32.6f} | {int(pop_opt):<15,}")
    print("-" * 95)

    # Salviamo i dati comparativi di performance
    df_scenarios = pd.DataFrame([
        {"Scenario": "Bus Only", "Avg_Travel_Time_Sec": l_bus, "Global_Efficiency": eff_bus, "Tram_Pop_Served": 0},
        {"Scenario": "Planned Tram", "Avg_Travel_Time_Sec": l_planned, "Global_Efficiency": eff_planned, "Tram_Pop_Served": int(pop_planned)},
        {"Scenario": "Circular Tram", "Avg_Travel_Time_Sec": l_circular, "Global_Efficiency": eff_circular, "Tram_Pop_Served": int(pop_circular)},
        {"Scenario": "Optimal Tram", "Avg_Travel_Time_Sec": l_opt, "Global_Efficiency": eff_opt, "Tram_Pop_Served": int(pop_opt)}
    ])
    df_scenarios.to_csv(OUTPUT_DIR / "scenarios_comparative_results.csv", index=False)

    # Simulazione Commuter Shock (Forced Hub passenger injection)
    print("\n -> Running forced commuter shock injection at main hubs...")
    from src.simulator import simulate_hub_injection
    injection_steps = [0, 5000, 10000, 25000, 50000, 100000]
    bus_shock = simulate_hub_injection(G_bus, injection_steps)
    tram_shock = simulate_hub_injection(G_fused, injection_steps)
    circular_shock = simulate_hub_injection(G_futuro, injection_steps)
    opt_shock = simulate_hub_injection(G_opt, injection_steps) if G_opt else None

    # Stampiamo la Tabella 6
    print("\n🏆 Table 6: Travel Times under Commuter Shock (in minutes):")
    print("-" * 95)
    print(f"{'Shock Population':<18} | {'Bus Only (min)':<16} | {'Planned Tram (min)':<18} | {'Circular Tram (min)':<19} | {'Optimal Tram (min)':<18}")
    print("-" * 95)
    for i, pop in enumerate(injection_steps):
        b_m = bus_shock[i] / 60.0
        t_m = tram_shock[i] / 60.0
        c_m = circular_shock[i] / 60.0
        o_m = (opt_shock[i] / 60.0) if opt_shock else 0.0
        print(f"{pop:<18,} | {b_m:<16.2f} | {t_m:<18.2f} | {c_m:<19.2f} | {o_m:<18.2f}")
    print("-" * 95)

    print("\n -> Generating future scenarios plots...")
    plot_tram_impact_map()
    plot_forced_injection_shock(injection_steps, bus_shock, tram_shock, circular_shock, opt_shock)
    plot_demographic_pressure_maps()

    # Map visualizer
    print("\n -> Generating static transit layout map...")
    plot_static_network(G_fused)

    # Future scenarios comparisons
    print("\n -> Generating planned vs optimized layouts map...")
    plot_optimized_layout(G_fused, G_opt)

    print("\n✅ Master Pipeline execution completed successfully! All data files saved and plots updated.")

if __name__ == "__main__":
    main()
