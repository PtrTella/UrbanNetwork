import networkx as nx
import pandas as pd
import numpy as np


def compute_centralities(G):
    """
    Calcola le metriche di centralità microscopica per i nodi.
    Aggiornato per usare l'attributo 'name' dei nodi al posto dell'ID.
    """
    degree_dict = dict(G.degree())
    deg_cent = nx.degree_centrality(G)

    # La closeness soffre se il grafo non è completamente connesso
    if nx.is_connected(G):
        clos_cent = nx.closeness_centrality(G, distance="weight")
    else:
        clos_cent = {}
        for comp in nx.connected_components(G):
            subG = G.subgraph(comp)
            sub_clos = nx.closeness_centrality(subG, distance="weight")
            clos_cent.update(sub_clos)

    # Betweenness pesata sui colli di bottiglia e distanze
    bet_cent = nx.betweenness_centrality(G, weight="weight")

    # k-Core Decomposition
    G_self = G.copy()
    G_self.remove_edges_from(nx.selfloop_edges(G_self))
    coreness = nx.core_number(G_self)

    # Build DataFrame
    data = []
    for node, attr in G.nodes(data=True):
        # Usiamo 'name' che è l'attributo che abbiamo assegnato nel graph.py
        station_name = attr.get("name", str(node))

        data.append(
            {
                "Station": station_name,
                "Degree": degree_dict.get(node, 0),
                "Degree Centrality": deg_cent.get(node, 0),
                "Closeness Centrality": clos_cent.get(node, 0),
                "Betweenness Centrality": bet_cent.get(node, 0),
                "Coreness": coreness.get(node, 0),
            }
        )
    return pd.DataFrame(data)


def compute_small_worldness(G, er_runs=50):
    """
    Computes global metrics and compares with random and lattice null models.
    """
    if nx.is_connected(G):
        G_lcc = G
    else:
        components = sorted(nx.connected_components(G), key=len, reverse=True)
        G_lcc = G.subgraph(components[0]).copy()

    N_lcc = len(G_lcc.nodes)
    M_lcc = len(G_lcc.edges)

    L = nx.average_shortest_path_length(G_lcc, weight="weight")
    C = nx.average_clustering(G)

    E_glob = nx.global_efficiency(G)
    E_loc = nx.local_efficiency(G)

    # Erdős-Rényi Null Model
    p = (2.0 * M_lcc) / (N_lcc * (N_lcc - 1)) if N_lcc > 1 else 0
    rand_L_list = []
    rand_C_list = []

    for _ in range(er_runs):
        G_rand = nx.fast_gnp_random_graph(N_lcc, p)
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

    # Lattice Model
    avg_k = max(2, int(round(2.0 * M_lcc / N_lcc)))
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

    # Coefficienti Small World
    sigma = (C / C_rand) / (L / L_rand) if L_rand > 0 and C_rand > 0 else 0.0
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
    and university (UNIBO) campus attraction weights.
    Aggiornato per usare l'attributo 'name' del nodo e non il suo ID.
    """
    # Mappiamo i nomi formattati sulle densità
    pop_dict = dict(zip(df_demo["station_name"], df_demo["population_density"]))
    attr_dict = dict(zip(df_demo["station_name"], df_demo["unibo_attraction"]))

    total_demand = 0.0
    weighted_sum = 0.0

    nodes = list(G.nodes(data=True))

    # Pre-calcoliamo le distanze minime pesate (costo del traffico/tram)
    path_lengths = dict(nx.all_pairs_dijkstra_path_length(G, weight="weight"))

    for i in range(len(nodes)):
        u_id, u_data = nodes[i]
        u_name = u_data.get("name", "")

        p_u = pop_dict.get(u_name, 0.0)
        if p_u == 0:
            continue  # Ottimizzazione: se la pop è zero salta

        for j in range(len(nodes)):
            if i == j:
                continue

            v_id, v_data = nodes[j]
            v_name = v_data.get("name", "")
            d_v = attr_dict.get(v_name, 0.0)

            demand_weight = p_u * d_v
            if demand_weight == 0:
                continue

            total_demand += demand_weight

            # Usiamo la distanza pesata salvata dal Dijkstra
            d_uv = path_lengths.get(u_id, {}).get(v_id, float("inf"))
            if d_uv != float("inf") and d_uv > 0:
                weighted_sum += demand_weight / d_uv

    if total_demand == 0.0:
        return 0.0
    return weighted_sum / total_demand
