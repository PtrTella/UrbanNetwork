# src/tram_optimizer.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import networkx as nx
from src.config import TransitConfig
from src.graph import load_cached_graph
from src.analyzer import compute_weighted_global_efficiency

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data_output" / "bologna"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def compute_edge_utilities(G_bus, alpha=10.0, beta=1.0, gamma=0.0001):
    """
    Calcola l'indice di utilità U(e) per ogni arco della rete dei bus.
    U(e) bilancia centralità di trazione, risparmio temporale orario e popolazione servita.
    """
    print(" -> Calcolo centralità di edge betweenness (pesata sui tempi)...")
    # Calcoliamo la edge betweenness pesata sui tempi di viaggio
    edge_bet = nx.edge_betweenness_centrality(G_bus, weight="weight")
    
    utilities = {}
    for u, v, data in G_bus.edges(data=True):
        eb = edge_bet.get((u, v), edge_bet.get((v, u), 0.0))
        dist_m = data.get("dist_meters", 100.0)
        
        # Tempo di viaggio del bus (BPR penalizzato) vs tram veloce
        t_bus = data.get("weight", 0.0)
        t_tram = dist_m / TransitConfig.TRAM_SPEED
        time_saved = max(0.0, t_bus - t_tram)
        
        # Popolazione servita dai nodi adiacenti
        pop_u = G_bus.nodes[u].get("population_served", 0.0)
        pop_v = G_bus.nodes[v].get("population_served", 0.0)
        avg_pop = (pop_u + pop_v) / 2.0
        
        # Calcolo dell'utilità combinata
        u_val = alpha * eb + beta * time_saved * eb + gamma * avg_pop
        
        utilities[(u, v)] = {
            "utility": u_val,
            "dist_meters": dist_m,
            "utility_per_meter": u_val / dist_m if dist_m > 0 else 0.0,
            "time_saved_sec": time_saved,
            "pop_served": avg_pop,
            "betweenness": eb
        }
        
    return utilities


def optimize_tram_layout(G_bus, budget_meters=20000, num_seeds=3):
    """
    Algoritmo Greedy Corridor Builder:
    Fa crescere le linee tram a partire dai top hub connettendoli
    ed espandendosi lungo gli archi con maggior rapporto utilità/metro.
    """
    # 1. Calcola le utilità degli archi
    utilities = compute_edge_utilities(G_bus)
    
    # 2. Identifica i nodi Seed (Hub centrali ad alta betweenness e demografia)
    print(" -> Identificazione dei nodi Seed per le linee...")
    node_bet = nx.betweenness_centrality(G_bus, weight="weight")
    
    node_scores = {}
    for n, data in G_bus.nodes(data=True):
        eb = node_bet.get(n, 0.0)
        pop = data.get("population_served", 0.0)
        node_scores[n] = eb * 1000 + pop / 1000.0
        
    sorted_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
    
    # Filtra per nomi unici di fermata/stazione per evitare duplicati fisici (es. Stazione Centrale)
    seen_names = set()
    seeds = []
    for n, score in sorted_nodes:
        name = G_bus.nodes[n].get("name", str(n)).strip().upper()
        if name not in seen_names:
            seen_names.add(name)
            seeds.append(n)
            if len(seeds) == num_seeds:
                break
    
    print(f"    Seeds identificati: {[G_bus.nodes[s].get('name', s) for s in seeds]}")
    
    # 3. Espansione Greedy
    active_nodes = set(seeds)
    selected_edges = set()
    total_length = 0.0
    
    while total_length < budget_meters:
        # Trova tutti gli archi candidati adiacenti alla rete attiva
        candidates = []
        for u, v in G_bus.edges():
            if (u, v) in selected_edges or (v, u) in selected_edges:
                continue
                
            # Almeno un nodo deve essere attivo (connessione della linea)
            if u in active_nodes or v in active_nodes:
                edge_data = utilities.get((u, v), utilities.get((v, u)))
                if edge_data:
                    candidates.append(((u, v), edge_data))
                    
        if not candidates:
            break
            
        # Sceglie l'arco con la miglior utilità per metro costruito
        best_candidate = max(candidates, key=lambda x: x[1]["utility_per_meter"])
        edge, data = best_candidate
        
        u, v = edge
        dist = data["dist_meters"]
        
        if total_length + dist > budget_meters:
            # Opzionale: aggiunge l'ultimo arco anche se sfora leggermente per completare il segmento
            break
            
        selected_edges.add((u, v))
        active_nodes.add(u)
        active_nodes.add(v)
        total_length += dist
        
    print(f" ✅ Ottimizzazione completata! Estensione totale: {total_length/1000.0:.2f} km | Archi tram: {len(selected_edges)}")
    return selected_edges, total_length


def evaluate_networks():
    print("\n" + "="*80)
    print("📊 COMPARATIVE TRAM NETWORK OPTIMIZATION".center(80))
    print("="*80 + "\n")
    
    # 1. Carica i grafi di baseline e pianificati
    G_bus = load_cached_graph("G_bus")
    G_planned = load_cached_graph("G_fused")
    
    # Assicurati che G_bus e G_planned abbiano le popolazioni (se non presenti, carica da demographic)
    from src.demographic import calculate_demographics_weight
    if "population_served" not in nx.get_node_attributes(G_bus, "population_served") or sum(nx.get_node_attributes(G_bus, "population_served").values()) == 0:
        print(" ⚠️ Popolazione non trovata o pari a zero in G_bus. Esecuzione pesatura demografica...")
        calculate_demographics_weight(G_bus, BASE_DIR / "dataset" / "bologna" / "raw")
        
    if "population_served" not in nx.get_node_attributes(G_planned, "population_served") or sum(nx.get_node_attributes(G_planned, "population_served").values()) == 0:
        print(" ⚠️ Popolazione non trovata o pari a zero in G_planned (TPER). Esecuzione pesatura demografica...")
        calculate_demographics_weight(G_planned, BASE_DIR / "dataset" / "bologna" / "raw")
        
    # 2. Esegui l'ottimizzatore
    # Impostiamo un budget simile alla rete programmata (circa 20 km complessivi di linee tram)
    budget = 20000  # 20 km
    opt_edges, opt_length = optimize_tram_layout(G_bus, budget_meters=budget)
    
    # 3. Costruisci il grafo Ottimizzato
    G_opt = G_bus.copy()
    for u, v in opt_edges:
        dist_m = G_bus.edges[u, v].get("dist_meters", 100.0)
        tram_time_sec = dist_m / TransitConfig.TRAM_SPEED
        G_opt.add_edge(u, v, weight=tram_time_sec, type="tram", route="TRAM_OTTIMIZZATA")
        G_opt.nodes[u]["type"] = "intersezione_bus_tram"
        G_opt.nodes[v]["type"] = "intersezione_bus_tram"
        
    # 4. Calcolo Metriche
    print("\n -> Calcolo efficienza delle 3 reti...")
    
    # A) Solo Bus
    eff_bus = compute_weighted_global_efficiency(G_bus)
    l_bus = nx.average_shortest_path_length(G_bus, weight="weight") if nx.is_connected(G_bus) else nx.average_shortest_path_length(G_bus.subgraph(max(nx.connected_components(G_bus), key=len)), weight="weight")
    
    # B) Pianificato (Fused)
    eff_planned = compute_weighted_global_efficiency(G_planned)
    l_planned = nx.average_shortest_path_length(G_planned, weight="weight") if nx.is_connected(G_planned) else nx.average_shortest_path_length(G_planned.subgraph(max(nx.connected_components(G_planned), key=len)), weight="weight")
    
    # C) Ottimizzato
    eff_opt = compute_weighted_global_efficiency(G_opt)
    l_opt = nx.average_shortest_path_length(G_opt, weight="weight") if nx.is_connected(G_opt) else nx.average_shortest_path_length(G_opt.subgraph(max(nx.connected_components(G_opt), key=len)), weight="weight")
    
    # 5. Calcolo Copertura Demografica (Popolazione servita direttamente dalle stazioni Tram)
    def get_tram_coverage(G):
        tram_stops = [n for n, d in G.nodes(data=True) if d.get("type") in ["tram", "intersezione_bus_tram"]]
        # Raggruppa per nome unico per evitare di conteggiare più volte la stessa fermata/stazione (piattaforme/direzioni multiple)
        unique_stops = {}
        for ts in tram_stops:
            name = G.nodes[ts].get("name", str(ts)).strip().upper()
            pop = G.nodes[ts].get("population_served", 0.0)
            unique_stops[name] = max(unique_stops.get(name, 0.0), pop)
        pop_served = sum(unique_stops.values())
        return pop_served, len(unique_stops)
        
    pop_planned, count_planned = get_tram_coverage(G_planned)
    pop_opt, count_opt = get_tram_coverage(G_opt)
    
    # 6. Tabella Comparativa
    print("\n" + "-"*85)
    print(f"{'Scenario di Rete':<28} | {'Avg Travel Time (sec)':<22} | {'Global Efficiency':<18} | {'Pop. Tram (Abitanti)':<19}")
    print("-"*85)
    print(f"{'🚌 Solo Bus (Baseline)':<28} | {l_bus:<22.2f} | {eff_bus:<18.6f} | {'N/D':<19}")
    print(f"{'🔗 Tram Pianificato (TPER)':<28} | {l_planned:<22.2f} | {eff_planned:<18.6f} | {int(pop_planned):<19}")
    print(f"{'🔮 Tram Ottimizzato (Greedy)':<28} | {l_opt:<22.2f} | {eff_opt:<18.6f} | {int(pop_opt):<19}")
    print("-"*85)
    
    # Salviamo i risultati comparativi in CSV
    df_results = pd.DataFrame([
        {"Scenario": "Solo Bus", "Avg_Travel_Time_Sec": l_bus, "Global_Efficiency": eff_bus, "Tram_Pop_Served": 0},
        {"Scenario": "Tram Pianificato (TPER)", "Avg_Travel_Time_Sec": l_planned, "Global_Efficiency": eff_planned, "Tram_Pop_Served": pop_planned},
        {"Scenario": "Tram Ottimizzato (Algorithm)", "Avg_Travel_Time_Sec": l_opt, "Global_Efficiency": eff_opt, "Tram_Pop_Served": pop_opt}
    ])
    df_results.to_csv(OUTPUT_DIR / "tram_optimization_comparison.csv", index=False)
    print(f"\n📊 Risultati comparativi salvati in: {OUTPUT_DIR / 'tram_optimization_comparison.csv'}")
    
    # Salviamo la rete ottimizzata in formato pickle
    graphs_dir = OUTPUT_DIR / "graphs"
    graphs_dir.mkdir(parents=True, exist_ok=True)
    import pickle
    with open(graphs_dir / "G_opt_tram.pkl", "wb") as f:
        pickle.dump(G_opt, f)
    print(f"💾 Grafo ottimizzato salvato in: {graphs_dir / 'G_opt_tram.pkl'}")
    
    # Generiamo il plot
    try:
        from src.plottings import plot_optimized_layout
        plot_path = OUTPUT_DIR / "bologna_tram_layout_comparison.png"
        plot_optimized_layout(G_planned, G_opt, plot_path)
    except Exception as e:
        print(f"⚠️ Errore durante la generazione del grafico: {e}")
        
    return G_opt


if __name__ == "__main__":
    evaluate_networks()
