import networkx as nx
import numpy as np

def simulate_removal(G, removal_fraction, scenario="random", seed=None, sorted_nodes=None):
    """
    Simulates node removal.
    Returns:
    - relative_lcc: size of the largest connected component divided by original size.
    - num_components: total connected components left.
    - glob_eff: absolute global efficiency of the remaining network.
    """
    N = len(G.nodes)
    num_to_remove = int(round(removal_fraction * N))
    G_temp = G.copy()
    
    if num_to_remove == 0:
        lcc = max(nx.connected_components(G_temp), key=len)
        return len(lcc) / N, 1, nx.global_efficiency(G_temp)
        
    if scenario == "random":
        if seed is not None:
            np.random.seed(seed)
        nodes_to_remove = np.random.choice(list(G_temp.nodes), size=num_to_remove, replace=False)
    elif scenario == "targeted":
        if sorted_nodes is None:
            original_bet = nx.betweenness_centrality(G, weight='weight')
            sorted_nodes = [node for node, val in sorted(original_bet.items(), key=lambda x: x[1], reverse=True)]
        nodes_to_remove = sorted_nodes[:num_to_remove]
    else:
        raise ValueError("Invalid scenario")
        
    G_temp.remove_nodes_from(nodes_to_remove)
    if len(G_temp.nodes) == 0:
        return 0.0, 0, 0.0
        
    components = list(nx.connected_components(G_temp))
    lcc = max(components, key=len)
    eff = nx.global_efficiency(G_temp)
    return len(lcc) / N, len(components), eff

def run_resilience_simulation(G, fractions=None, random_runs=50):
    """
    Runs the full resilience simulation over multiple fractions.
    Pre-computes betweenness centrality once to optimize execution speed.
    Also tracks global efficiency decay.
    """
    if fractions is None:
        fractions = np.linspace(0.0, 0.5, 11)
        
    # Pre-compute targeted nodes sorted by betweenness centrality once
    original_bet = nx.betweenness_centrality(G, weight='weight')
    sorted_nodes = [node for node, val in sorted(original_bet.items(), key=lambda x: x[1], reverse=True)]
    
    # Calculate original global efficiency for normalization
    eff_original = nx.global_efficiency(G)
    if eff_original == 0:
        eff_original = 1.0
    
    targeted_lcc = []
    targeted_frag = []
    targeted_eff = []
    for f in fractions:
        lcc_f, frag_f, eff_f = simulate_removal(G, f, scenario="targeted", sorted_nodes=sorted_nodes)
        targeted_lcc.append(lcc_f)
        targeted_frag.append(frag_f)
        targeted_eff.append(eff_f / eff_original)
        
    random_lcc_matrix = []
    random_frag_matrix = []
    random_eff_matrix = []
    for run in range(random_runs):
        run_lcc = []
        run_frag = []
        run_eff = []
        for f in fractions:
            lcc_f, frag_f, eff_f = simulate_removal(G, f, scenario="random", seed=run*100 + 42)
            run_lcc.append(lcc_f)
            run_frag.append(frag_f)
            run_eff.append(eff_f / eff_original)
        random_lcc_matrix.append(run_lcc)
        random_frag_matrix.append(run_frag)
        random_eff_matrix.append(run_eff)
        
    random_lcc = np.mean(random_lcc_matrix, axis=0)
    random_frag = np.mean(random_frag_matrix, axis=0)
    random_eff = np.mean(random_eff_matrix, axis=0)
    
    return fractions, random_lcc, targeted_lcc, random_frag, targeted_frag, random_eff, targeted_eff
