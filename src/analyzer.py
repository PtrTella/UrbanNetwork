import networkx as nx
import pandas as pd
import numpy as np

def compute_centralities(G):
    """
    Computes degree centrality, closeness centrality (weighted), and betweenness centrality (weighted).
    Returns a pandas DataFrame.
    """
    deg_raw = dict(G.degree())
    deg_cent = nx.degree_centrality(G)
    close_cent = nx.closeness_centrality(G, distance='weight')
    bet_cent = nx.betweenness_centrality(G, weight='weight', normalized=True)

    df_micro = pd.DataFrame({
        'Station': list(G.nodes),
        'Degree': [deg_raw[n] for n in G.nodes],
        'Degree Centrality': [deg_cent[n] for n in G.nodes],
        'Closeness Centrality': [close_cent[n] for n in G.nodes],
        'Betweenness Centrality': [bet_cent[n] for n in G.nodes]
    })
    return df_micro

def compute_small_worldness(G, er_runs=50):
    """
    Computes average path length, clustering coefficient, and compares with Erdos-Renyi
    and regular lattice models to return sigma and omega.
    Does not loop infinitely for sparse random graphs.
    """
    N = len(G.nodes)
    M = len(G.edges)
    density = nx.density(G)

    # Real network metrics
    L = nx.average_shortest_path_length(G)
    C = nx.average_clustering(G)
    E_glob = nx.global_efficiency(G)
    E_loc = nx.local_efficiency(G)

    # Erdos-Renyi Null Model
    L_rands, C_rands = [], []
    for i in range(er_runs):
        G_rand = nx.erdos_renyi_graph(N, density, seed=i*13)
        components = list(nx.connected_components(G_rand))
        if components:
            lcc = G_rand.subgraph(max(components, key=len))
            if len(lcc.nodes) > 1:
                L_rands.append(nx.average_shortest_path_length(lcc))
            else:
                L_rands.append(1.0)
        else:
            L_rands.append(1.0)
        C_rands.append(nx.average_clustering(G_rand))

    L_rand = np.mean(L_rands)
    C_rand = np.mean(C_rands)

    # Sigma coefficient
    sigma = (C / C_rand) / (L / L_rand) if C_rand > 0 else 1.0

    # 1D regular lattice
    k_avg = int(round(2 * M / N))
    G_lat = nx.watts_strogatz_graph(N, k_avg, 0)
    L_lat = nx.average_shortest_path_length(G_lat)
    C_lat = nx.average_clustering(G_lat)

    # Omega coefficient
    omega = (L_rand / L) - (C / C_lat) if C_lat > 0 else 0.0

    results = {
        'L': L,
        'C': C,
        'L_rand': L_rand,
        'C_rand': C_rand,
        'sigma': sigma,
        'L_lat': L_lat,
        'C_lat': C_lat,
        'omega': omega,
        'density': density,
        'E_glob': E_glob,
        'E_loc': E_loc
    }
    return results
