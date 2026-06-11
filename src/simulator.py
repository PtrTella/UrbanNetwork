import networkx as nx
import numpy as np

# IMPORTIAMO LA VERA EFFICIENZA TEMPORALE
from src.analyzer import compute_weighted_global_efficiency


def simulate_removal(
    G, removal_fraction, scenario="random", seed=None, sorted_nodes=None
):
    """
    Simula la rimozione dei nodi su G.
    Ritorna:
    - relative_lcc: dimensione della componente connessa principale diviso dimensione originale.
    - num_components: numero totale di componenti connesse.
    - glob_eff: vera efficienza globale (pesata sui tempi) della rete rimanente.
    """
    N = len(G.nodes)
    num_to_remove = int(round(removal_fraction * N))
    G_temp = G.copy()

    if num_to_remove == 0:
        lcc = max(nx.connected_components(G_temp), key=len) if N > 0 else []
        # FIX: Usiamo l'efficienza temporale
        return len(lcc) / N, 1, compute_weighted_global_efficiency(G_temp)

    # Random attack
    if scenario == "random":
        if seed is not None:
            np.random.seed(seed)
        nodes_to_remove = np.random.choice(
            list(G_temp.nodes), size=num_to_remove, replace=False
        )

    # Attack to the top hubs
    elif scenario == "targeted":
        if sorted_nodes is None:
            original_bet = nx.betweenness_centrality(G, weight="weight")
            sorted_nodes = [
                node
                for node, val in sorted(
                    original_bet.items(), key=lambda x: x[1], reverse=True
                )
            ]
        nodes_to_remove = sorted_nodes[:num_to_remove]

    elif scenario == "accidents":
        if seed is not None:
            np.random.seed(seed)

        nodi_lista = list(G_temp.nodes)
        # Estraiamo gli incidenti per ogni nodo (base_risk = 1.0)
        rischi = np.array([
            G_temp.nodes[n].get("accidents", 0) + 1.0 for n in nodi_lista
        ])

        # Normalizziamo le probabilità
        probabilita = rischi / rischi.sum()

        # Rimozione ponderata sul rischio storico
        nodes_to_remove = np.random.choice(
            nodi_lista, size=num_to_remove, replace=False, p=probabilita
        )

    else:
        raise ValueError("Invalid scenario. Scegli tra: random, targeted, accidents.")

    G_temp.remove_nodes_from(nodes_to_remove)

    if len(G_temp.nodes) == 0:
        return 0.0, 0, 0.0

    components = list(nx.connected_components(G_temp))
    lcc = max(components, key=len)

    # FIX: Usiamo l'efficienza temporale anche qui
    eff = compute_weighted_global_efficiency(G_temp)
    return len(lcc) / N, len(components), eff


def run_resilience_simulation(G, fractions=None, random_runs=30):
    """
    Esegue la simulazione di resilienza su più frazioni di rimozione.
    Confronta 3 scenari: Casuale, Mirato (Betweenness), e Rischio (Incidenti).
    """
    if fractions is None:
        fractions = np.linspace(0.0, 0.5, 11)

    # Pre-calcoliamo la Betweenness per lo scenario mirato
    original_bet = nx.betweenness_centrality(G, weight="weight")
    sorted_nodes = [
        node
        for node, val in sorted(original_bet.items(), key=lambda x: x[1], reverse=True)
    ]

    # FIX: Calcoliamo l'efficienza base in SECONDI per la normalizzazione
    eff_original = compute_weighted_global_efficiency(G)
    if eff_original == 0:
        eff_original = 1.0

    # Liste per lo scenario TARGETED
    targeted_lcc, targeted_frag, targeted_eff = [], [], []
    for f in fractions:
        lcc_f, frag_f, eff_f = simulate_removal(
            G, f, scenario="targeted", sorted_nodes=sorted_nodes
        )
        targeted_lcc.append(lcc_f)
        targeted_frag.append(frag_f)
        targeted_eff.append(eff_f / eff_original)

    # Matrici per gli scenari stocastici (RANDOM e ACCIDENTS)
    random_lcc_matrix, random_frag_matrix, random_eff_matrix = [], [], []
    accidents_lcc_matrix, accidents_frag_matrix, accidents_eff_matrix = [], [], []

    for run in range(random_runs):
        r_lcc, r_frag, r_eff = [], [], []
        a_lcc, a_frag, a_eff = [], [], []

        for f in fractions:
            # Simulazione Random pura
            l_r, fr_r, e_r = simulate_removal(
                G, f, scenario="random", seed=run * 100 + 42
            )
            r_lcc.append(l_r)
            r_frag.append(fr_r)
            r_eff.append(e_r / eff_original)

            # Simulazione basata sul Rischio Incidenti
            l_a, fr_a, e_a = simulate_removal(
                G, f, scenario="accidents", seed=run * 100 + 43
            )
            a_lcc.append(l_a)
            a_frag.append(fr_a)
            a_eff.append(e_a / eff_original)

        random_lcc_matrix.append(r_lcc)
        random_frag_matrix.append(r_frag)
        random_eff_matrix.append(r_eff)

        accidents_lcc_matrix.append(a_lcc)
        accidents_frag_matrix.append(a_frag)
        accidents_eff_matrix.append(a_eff)

    # Medie sulle run stocastiche
    random_lcc = np.mean(random_lcc_matrix, axis=0)
    random_frag = np.mean(random_frag_matrix, axis=0)
    random_eff = np.mean(random_eff_matrix, axis=0)

    accidents_lcc = np.mean(accidents_lcc_matrix, axis=0)
    accidents_frag = np.mean(accidents_frag_matrix, axis=0)
    accidents_eff = np.mean(accidents_eff_matrix, axis=0)

    return (
        fractions,
        random_lcc,
        targeted_lcc,
        accidents_lcc,
        random_frag,
        targeted_frag,
        accidents_frag,
        random_eff,
        targeted_eff,
        accidents_eff,
    )


def simulate_targeted_hub_attack(graphs_dict, top_node_data):
    """
    Simula l'attacco mirato a cascata sui Top 5 Hub (Betweenness) su un insieme di grafi.
    Stampa la tabella dei risultati.
    """
    # Copiamo i grafi per non alterare gli originali
    graph_copies = {name: G.copy() for name, G in graphs_dict.items()}
    
    # Calcoliamo l'efficienza base per ciascun grafo
    base_efficiencies = {
        name: compute_weighted_global_efficiency(G) 
        for name, G in graphs_dict.items()
    }

    # Intestazione della tabella dinamica
    headers = [f"📉 Crollo {name}" for name in graphs_dict.keys()]
    header_str = " | ".join(f"{h:<16}" for h in headers)
    print("-" * (25 + len(headers) * 19))
    print(f"{'Hub Compromesso':<22} | {header_str}")
    print("-" * (25 + len(headers) * 19))

    results = []

    for node_id, node_name in top_node_data:
        drops = {}
        for name, G_copy in graph_copies.items():
            if G_copy.has_node(node_id):
                G_copy.remove_node(node_id)
            
            # Calcola il crollo percentuale dell'efficienza
            eff_base = base_efficiencies[name]
            eff_current = compute_weighted_global_efficiency(G_copy)
            drops[name] = ((eff_base - eff_current) / eff_base * 100) if eff_base > 0 else 0.0

        name_short = node_name[:20] + ".." if len(node_name) > 20 else node_name
        drops_str = " | ".join(f"-{drops[name]:.2f}%{'':<10}" for name in graphs_dict.keys())
        print(f"{name_short:<22} | {drops_str}")
        
        node_results = {"node_id": node_id, "node_name": node_name}
        for name in graphs_dict.keys():
            node_results[f"drop_{name.lower()}"] = drops[name]
        results.append(node_results)

    print("-" * (25 + len(headers) * 19))
    return results

