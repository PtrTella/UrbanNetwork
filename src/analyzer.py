import networkx as nx
import pandas as pd
import numpy as np


def compute_weighted_global_efficiency(G):
    r"""
    Calcola la vera Efficienza Globale della rete pesata sui TEMPI DI VIAGGIO (secondi).
    E = 1 / (N*(N-1)) * \sum_{u != v} 1 / d_weighted(u,v)
    Più l'efficienza è alta, più la città è rapida da navigare.
    """
    N = len(G.nodes)
    if N <= 1:
        return 0.0

    # Calcoliamo tutte le distanze minime in secondi usando Dijkstra
    path_lengths = nx.all_pairs_dijkstra_path_length(G, weight="weight")

    sum_inverse_eff = 0.0
    for u, targets in path_lengths:
        for v, travel_time in targets.items():
            if u != v and travel_time > 0:
                sum_inverse_eff += 1.0 / travel_time

    return sum_inverse_eff / (N * (N - 1))


def compute_centralities(G):
    """
    Calcola le metriche di centralità microscopica per i nodi basate sul tempo di percorrenza.
    """
    degree_dict = dict(G.degree())
    deg_cent = nx.degree_centrality(G)

    if nx.is_connected(G):
        clos_cent = nx.closeness_centrality(G, distance="weight")
    else:
        clos_cent = {}
        for comp in nx.connected_components(G):
            subG = G.subgraph(comp)
            sub_clos = nx.closeness_centrality(subG, distance="weight")
            clos_cent.update(sub_clos)

    # I colli di bottiglia ora sono calcolati sui percorsi più veloci in secondi
    bet_cent = nx.betweenness_centrality(G, weight="weight")

    G_self = G.copy()
    G_self.remove_edges_from(nx.selfloop_edges(G_self))
    coreness = nx.core_number(G_self)

    data = []
    for node, attr in G.nodes(data=True):
        station_name = attr.get("name", str(node))
        data.append(
            {
                "Station_ID": str(node),
                "Station_Name": station_name,
                "Degree": degree_dict.get(node, 0),
                "Degree Centrality": deg_cent.get(node, 0),
                "Closeness Centrality": clos_cent.get(node, 0),
                "Betweenness Centrality": bet_cent.get(node, 0),
                "Coreness": coreness.get(node, 0),
            }
        )
    return pd.DataFrame(data)


def compute_small_worldness(G, er_runs=5):
    """
    Calcola le metriche globali della rete.
    Risolve il bug di NetworkX calcolando la vera efficienza pesata
    e isolando la topologia non pesata per gli indici Sigma e Omega dello Small-World.
    """
    if nx.is_connected(G):
        G_lcc = G
    else:
        components = sorted(nx.connected_components(G), key=len, reverse=True)
        G_lcc = G.subgraph(components[0]).copy()

    N_lcc = len(G_lcc.nodes)
    M_lcc = len(G_lcc.edges)

    # 1. METRICHE REALI PESATE (Output per l'utente)
    L_time = nx.average_shortest_path_length(
        G_lcc, weight="weight"
    )  # Tempo medio in secondi
    C = nx.average_clustering(G)  # Clustering topologico

    # Vera efficienza calcolata sul tempo
    E_glob = compute_weighted_global_efficiency(G)
    E_loc = nx.local_efficiency(G)  # Strutturale geometrico

    # 2. METRICHE REALI TOPOLOGICHE PURA (Per confronto Small-World Watts-Strogatz)
    L_hops = nx.average_shortest_path_length(G_lcc, weight=None)

    # --- Modello Nullo: Erdős-Rényi (Random Graph) ---
    p = (2.0 * M_lcc) / (N_lcc * (N_lcc - 1)) if N_lcc > 1 else 0
    rand_L_list = []
    rand_C_list = []

    for _ in range(er_runs):
        G_rand = nx.fast_gnp_random_graph(N_lcc, p, seed=42 + _)
        if nx.is_connected(G_rand):
            rand_L_list.append(nx.average_shortest_path_length(G_rand, weight=None))
            rand_C_list.append(nx.average_clustering(G_rand))
        else:
            r_comps = sorted(nx.connected_components(G_rand), key=len, reverse=True)
            if len(r_comps[0]) > 1:
                rand_L_list.append(
                    nx.average_shortest_path_length(
                        G_rand.subgraph(r_comps[0]), weight=None
                    )
                )
                rand_C_list.append(nx.average_clustering(G_rand))

    L_rand = np.mean(rand_L_list) if rand_L_list else 1.0
    C_rand = np.mean(rand_C_list) if rand_C_list else p

    # --- Modello Nullo: Lattice (Rete Regolare) ---
    avg_k = max(2, int(round(2.0 * M_lcc / N_lcc)))
    G_lat = nx.Graph()
    G_lat.add_nodes_from(range(N_lcc))
    for i in range(N_lcc):
        for j in range(1, avg_k // 2 + 1):
            G_lat.add_edge(i, (i + j) % N_lcc)
            G_lat.add_edge(i, (i - j) % N_lcc)

    L_lat = (
        nx.average_shortest_path_length(G_lat, weight=None)
        if nx.is_connected(G_lat)
        else float("inf")
    )
    C_lat = nx.average_clustering(G_lat)

    # --- Calcolo Coefficienti Corretti (Hops vs Hops) ---
    sigma = (C / C_rand) / (L_hops / L_rand) if L_rand > 0 and C_rand > 0 else 0.0
    omega = (L_rand / L_hops) - (C / C_lat) if C_lat > 0 else 0.0

    # Restituiamo sia le chiavi minuscole che maiuscole per evitare crash nel main
    return {
        "N": N_lcc,
        "M": M_lcc,
        "L": L_time,  # Tempo medio in secondi (mantiene la struttura del main)
        "L_hops": L_hops,  # Distanza in fermate
        "C": C,
        "E_glob": E_glob,  # Vera efficienza temporale
        "E_loc": E_loc,
        "sigma": sigma,
        "Sigma": sigma,  # Duplicato per robustezza maiuscole
        "omega": omega,
        "Omega": omega,
    }
