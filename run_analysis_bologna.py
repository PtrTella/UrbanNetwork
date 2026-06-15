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
    print("\\n" + "=" * 110)
    print("🚀 BOLOGNA TRANSIT NETWORK: L-SPACE & P-SPACE ANALYSIS 🚀".center(110))
    print("=" * 110 + "\\n")

    # Load core graphs
    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")

    # --- ACT 1 ---
    print("\\n" + "=" * 110)
    print("🎭 ACT 1: COGNITIVE TOPOLOGY (P-SPACE)".center(110))
    print("=" * 110)
    print(" -> Analyzing how citizens 'use' the network (Communities & Assortativity).")
    try:
        from src.plottings import plot_communities_map
        plot_communities_map()
    except ImportError:
        pass

    # --- ACT 2 ---
    print("\\n" + "=" * 110)
    print("🏭 ACT 2: INFRASTRUCTURE VULNERABILITY (L-SPACE)".center(110))
    print("=" * 110)
    print(" -> Evaluating physical constraints: Bottlenecks, Accidents, and Demographic Overload.")
    
    df_centrality = compute_centralities(G_bus)
    df_top_5 = df_centrality.sort_values(by="Betweenness Centrality", ascending=False).head(5)
    print("\n⚠️ Top 5 Physical Bottlenecks (Vene Giugulari della città):")
    for _, row in df_top_5.iterrows():
        print(f"  - {row['Station_Name']:<32} | Score: {row['Betweenness Centrality']:.5f}")
    
    plot_centrality_analysis(df_centrality)
    
    try:
        from src.plottings import plot_bottlenecks_map
        plot_bottlenecks_map()
    except ImportError:
        pass

    print("\\n -> A) Stress Operativo: Simulazione Percolazione (Random vs Targeted vs Accidents)")
    (fracs, rand_lcc, targ_lcc, acc_lcc, rand_frag, targ_frag, acc_frag, rand_eff, targ_eff, acc_eff) = run_resilience_simulation(G_bus, random_runs=20)
    df_percolation = pd.DataFrame({
        "Removal_Fraction": fracs, "Random_LCC_Size": rand_lcc, "Targeted_LCC_Size": targ_lcc, "Accidents_LCC_Size": acc_lcc,
        "Random_Efficiency": rand_eff, "Targeted_Efficiency": targ_eff, "Accidents_Efficiency": acc_eff
    })
    df_percolation.to_csv(PROCESSED_DIR / "resilience_percolation_results.csv", index=False)
    plot_resilience_curves()

    print("\\n -> B) Stress Esogeno: Pressione Demografica")
    calculate_demographics_weight(G_fused, RAW_DIR)
    try:
        from src.plottings import plot_demographic_pressure_maps
        plot_demographic_pressure_maps()
    except ImportError:
        pass

    # --- ACT 3 ---
    print("\\n" + "=" * 110)
    print("🛠️ ACT 3: MITIGATION & SOLUTION (FUSED TRAM)".center(110))
    print("=" * 110)
    print(" -> Evaluating Tram integration as a shock absorber.")
    try:
        from src.plottings import plot_comparative_resilience
        plot_comparative_resilience()
    except ImportError:
        pass
    
    # --- ACT 4 ---
    print("\\n" + "=" * 110)
    print("🚄 ACT 4: TRAM IMPACT & FORCED STATION INJECTION".center(110))
    print("=" * 110)
    print(" -> Simulating extreme commuter injection at Stazione Centrale & Autostazione...")
    try:
        from src.simulator import simulate_hub_injection
        from src.plottings import plot_tram_impact_map, plot_forced_injection_shock
        
        # 1. Mappa del tracciato tram
        plot_tram_impact_map()
        
        # 2. Carica G_futuro e G_opt
        G_futuro = load_cached_graph("G_futuro")
        G_opt = load_cached_graph("G_opt_tram")
        
        # 3. Simulazione iniezione
        injection_steps = [0, 5000, 10000, 25000, 50000, 100000]
        bus_times = simulate_hub_injection(G_bus, injection_steps)
        tram_times = simulate_hub_injection(G_fused, injection_steps)
        futuro_times = simulate_hub_injection(G_futuro, injection_steps)
        opt_times = simulate_hub_injection(G_opt, injection_steps) if G_opt else None
        
        # Stampiamo la tabella comparativa dei tempi di viaggio in minuti per copiare i dati in LaTeX
        print("\n📈 Risultati Iniezione di Shock (Tempi Medi di Viaggio in minuti):")
        print("-" * 90)
        print(f"{'Passeggeri':<12} | {'Solo Bus':<12} | {'Tram TPER':<12} | {'Tram+Circolare':<15} | {'Tram Ottimizzato':<16}")
        print("-" * 90)
        for i, pop in enumerate(injection_steps):
            b_m = bus_times[i] / 60.0
            t_m = tram_times[i] / 60.0
            f_m = futuro_times[i] / 60.0
            o_m = (opt_times[i] / 60.0) if opt_times else 0.0
            print(f"{pop:<12} | {b_m:<12.2f} | {t_m:<12.2f} | {f_m:<15.2f} | {o_m:<16.2f}")
        print("-" * 90)
        
        plot_forced_injection_shock(injection_steps, bus_times, tram_times, futuro_times, opt_times)
        print("    [!] Shock simulation and Tram maps generated successfully.")
    except Exception as e:
        print(f"    [X] Error running Act 4: {e}")
        import traceback
        traceback.print_exc()

    print("\\n✅ [SUCCESS] Pipeline analitica (Act 1, 2, 3, 4) completata al 100%.")

if __name__ == "__main__":
    main()
