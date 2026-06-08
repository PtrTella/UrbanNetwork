import networkx as nx
import pandas as pd
import numpy as np


def compute_centralities(G):
    """
    Computes Degree, Closeness, and Betweenness Centralities for G,
    and performs a k-core decomposition.
    """
    # Degree
    degree_dict = dict(G.degree())
    deg_cent = nx.degree_centrality(G)

    # Closeness (weighted by geographical distance 'weight')
    clos_cent = nx.closeness_centrality(G, distance="weight")

    # Betweenness (weighted by geographical distance 'weight')
    bet_cent = nx.betweenness_centrality(G, weight="weight")

    # k-Core Decomposition
    # To run k_core we need to remove self-loops if any
    G_self = G.copy()
    G_self.remove_edges_from(nx.selfloop_edges(G_self))
    coreness = nx.core_number(G_self)

    # Build DataFrame
    data = []
    for node in G.nodes():
        data.append(
            {
                "Station": node,
                "Degree": degree_dict[node],
                "Degree Centrality": deg_cent[node],
                "Closeness Centrality": clos_cent[node],
                "Betweenness Centrality": bet_cent[node],
                "Coreness": coreness.get(node, 0),
            }
        )

    return pd.DataFrame(data)


def compute_small_worldness(G, er_runs=50):
    """
    Computes global metrics and compares with random and lattice null models.
    """
    # Extract Largest Connected Component (LCC) for path metrics
    if nx.is_connected(G):
        G_lcc = G
    else:
        components = sorted(nx.connected_components(G), key=len, reverse=True)
        G_lcc = G.subgraph(components[0]).copy()

    N_lcc = len(G_lcc.nodes)
    M_lcc = len(G_lcc.edges)

    L = nx.average_shortest_path_length(G_lcc)
    C = nx.average_clustering(G)

    # Global & Local Efficiency
    E_glob = nx.global_efficiency(G)
    E_loc = nx.local_efficiency(G)

    # Erdős-Rényi Null Model
    p = (2.0 * M_lcc) / (N_lcc * (N_lcc - 1)) if N_lcc > 1 else 0
    rand_L_list = []
    rand_C_list = []

    for _ in range(er_runs):
        G_rand = nx.fast_gnp_random_graph(N_lcc, p)
        # Ensure random graph has a valid path length
        if nx.is_connected(G_rand):
            rand_L_list.append(nx.average_shortest_path_length(G_rand))
            rand_C_list.append(nx.average_clustering(G_rand))
        else:
            r_comps = sorted(nx.connected_components(G_rand), key=len, reverse=True)
            if len(r_comps[0]) > 1:
                rand_L_list.append(
                    nx.average_shortest_path_length(G_rand.subgraph(r_comps[0]))
                )
                rand_C_list.append(nx.average_clustering(G_rand))

    L_rand = np.mean(rand_L_list) if rand_L_list else 1.0
    C_rand = np.mean(rand_C_list) if rand_C_list else p

    # 1D Regular Lattice Null Model (Ring Lattice)
    avg_k = int(round(2.0 * M_lcc / N_lcc))
    if avg_k < 2:
        avg_k = 2
    G_lat = nx.navigable_small_world_graph(N_lcc, p=1, q=0, r=2, dim=1)  # approximation
    # Build simple ring lattice
    G_lat = nx.Graph()
    G_lat.add_nodes_from(range(N_lcc))
    for i in range(N_lcc):
        for j in range(1, avg_k // 2 + 1):
            G_lat.add_edge(i, (i + j) % N_lcc)
            G_lat.add_edge(i, (i - j) % N_lcc)

    L_lat = (
        nx.average_shortest_path_length(G_lat)
        if nx.is_connected(G_lat)
        else float("inf")
    )
    C_lat = nx.average_clustering(G_lat)

    # Coefficients
    sigma = (C / C_rand) / (L / L_rand) if L_rand > 0 and C_rand > 0 else 0.0
    # Telesford et al. omega
    # omega = (L_rand / L) - (C / C_lat)
    omega = (L_rand / L) - (C / C_lat) if C_lat > 0 else 0.0

    return {
        "L": L,
        "C": C,
        "E_glob": E_glob,
        "E_loc": E_loc,
        "L_rand": L_rand,
        "C_rand": C_rand,
        "sigma": sigma,
        "L_lat": L_lat,
        "C_lat": C_lat,
        "omega": omega,
    }


def compute_demand_weighted_efficiency(G, df_demo):
    """
    Computes global transport efficiency weighted by neighborhood population density
    (as origin weights) and university (UNIBO) campus attraction weights (as destination weights).
    Formula:
      E_demand = Sum_{i != j} [P_i * D_j / d_ij] / Sum_{i != j} [P_i * D_j]
    where d_ij is the topological distance. If disconnected, d_ij = inf -> 1/d_ij = 0.
    """
    # Map station names to demographics
    pop_dict = dict(zip(df_demo["station_name"], df_demo["population_density"]))
    attr_dict = dict(zip(df_demo["station_name"], df_demo["unibo_attraction"]))

    total_demand = 0.0
    weighted_sum = 0.0

    nodes = list(G.nodes())
    path_lengths = dict(nx.all_pairs_shortest_path_length(G))

    for i in range(len(nodes)):
        u = nodes[i]
        p_u = pop_dict.get(u, 0.0)
        for j in range(len(nodes)):
            if i == j:
                continue
            v = nodes[j]
            d_v = attr_dict.get(v, 0.0)

            demand_weight = p_u * d_v
            total_demand += demand_weight

            d_uv = path_lengths.get(u, {}).get(v, float("inf"))
            if d_uv != float("inf") and d_uv > 0:
                weighted_sum += demand_weight / d_uv

    if total_demand == 0.0:
        return 0.0
    return weighted_sum / total_demand
