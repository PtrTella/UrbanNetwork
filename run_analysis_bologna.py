import os
import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from src.data_loader_bologna import load_bologna_network, haversine
from src.analyzer_bologna import (
    compute_centralities,
    compute_small_worldness,
    compute_demand_weighted_efficiency
)
from src.simulator_bologna import run_resilience_simulation

def main():
    print("=== Phase 1: Data Ingestion & Preprocessing ===")
    os.makedirs("data_output/bologna", exist_ok=True)
    os.makedirs("latex/figures/bologna", exist_ok=True)
    
    # Load Networks
    G_bus, df_stations, df_connections, df_lines, df_demo = load_bologna_network(include_tram=False)
    G_tram, _, _, _, _ = load_bologna_network(include_tram=True)
    
    print(f"Bologna Bus-Only Network:")
    print(f"  Stations (Nodes, N): {len(G_bus.nodes)}")
    print(f"  Connections (Edges, M): {len(G_bus.edges)}")
    print(f"  Density (p): {nx.density(G_bus):.6f}")
    print(f"  Is Connected: {nx.is_connected(G_bus)}")
    
    print(f"Bologna Bus+Tram Network:")
    print(f"  Stations (Nodes, N): {len(G_tram.nodes)}")
    print(f"  Connections (Edges, M): {len(G_tram.edges)}")
    print(f"  Density (p): {nx.density(G_tram):.6f}")
    print(f"  Is Connected: {nx.is_connected(G_tram)}")

    # Plot network layouts
    pos = {node: (data['lon'], data['lat']) for node, data in G_tram.nodes(data=True)}
    line_colors_map = {int(row['line']): f"#{row['colour']}" for idx, row in df_lines.iterrows()}
    
    plt.figure(figsize=(10, 8))
    plt.gca().set_facecolor('#fdfefe')
    
    # Draw Bus Edges
    bus_edges = [(u, v) for u, v in G_tram.edges() if any(l < 100 for l in G_tram[u][v]['lines'])]
    nx.draw_networkx_edges(G_tram, pos, edgelist=bus_edges, edge_color='#bdc3c7', width=1.5, alpha=0.7, label='Bus Lines')
    
    # Draw Tram Edges
    tram_edges = [(u, v) for u, v in G_tram.edges() if any(l >= 100 for l in G_tram[u][v]['lines'])]
    tram_colors = [line_colors_map.get(G_tram[u][v]['lines'][0], '#C62828') for u, v in tram_edges]
    nx.draw_networkx_edges(G_tram, pos, edgelist=tram_edges, edge_color=tram_colors, width=3.5, alpha=0.9, label='Tram Lines')
    
    # Draw Nodes
    station_nodes = [node for node, data in G_tram.nodes(data=True) if data['type'] == 'Station']
    campus_nodes = [node for node, data in G_tram.nodes(data=True) if data['type'] == 'Campus']
    
    nx.draw_networkx_nodes(G_tram, pos, nodelist=station_nodes, node_size=40, node_color='black', alpha=0.8)
    nx.draw_networkx_nodes(G_tram, pos, nodelist=campus_nodes, node_size=120, node_color='#1976D2', node_shape='^', label='UNIBO Campus Hub')
    
    # Add labels to campus hubs
    campus_labels = {name: name for name in campus_nodes}
    label_pos = {name: (pos[name][0], pos[name][1] + 0.0015) for name in campus_nodes}
    nx.draw_networkx_labels(G_tram, label_pos, labels=campus_labels, font_size=8, font_weight='bold')
    
    plt.title("Bologna Integrated Public Transport Network (Bus + Planned Tram)", fontsize=13, fontweight='bold')
    plt.legend(loc='lower left', frameon=True)
    plt.axis('off')
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/bologna_tube_map.png", dpi=300)
    plt.close()
    
    # Save GraphML
    G_export = G_tram.copy()
    for node, data in G_export.nodes(data=True):
        if 'pos' in data:
            del data['pos']
    for u, v, data in G_export.edges(data=True):
        data['lines'] = str(data['lines'])
    nx.write_graphml(G_export, "data_output/bologna/bologna_network.graphml")

    print("\n=== Phase 2: Microscopic Centrality Analysis ===")
    df_micro = compute_centralities(G_bus)
    df_micro.to_csv("data_output/bologna/bologna_centralities.csv", index=False)
    
    print("\nTop 5 Stations by Betweenness Centrality (Bottlenecks):")
    print(df_micro.sort_values(by='Betweenness Centrality', ascending=False).head(5)[['Station', 'Betweenness Centrality']])
    
    # Plot Degree Distribution
    deg_counts = df_micro['Degree'].value_counts().sort_index()
    plt.figure(figsize=(7, 5))
    plt.bar(deg_counts.index, deg_counts.values, color='#2c3e50', edgecolor='black', alpha=0.8)
    plt.xlabel('Degree (k)')
    plt.ylabel('Frequency (Count)')
    plt.title('Bologna Bus Network: Bounded Node Degree Distribution', fontweight='bold')
    plt.xticks(deg_counts.index)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/bologna_degree_dist.png", dpi=300)
    plt.close()
    
    # Plot Centrality Hotspots
    bet_dict = dict(zip(df_micro['Station'], df_micro['Betweenness Centrality']))
    node_sizes = [20 + 500 * bet_dict.get(node, 0) for node in G_bus.nodes()]
    node_colors = [bet_dict.get(node, 0) for node in G_bus.nodes()]
    
    plt.figure(figsize=(10, 8))
    plt.gca().set_facecolor('#1a1a1a')
    nx.draw_networkx_edges(G_bus, pos, edge_color='#555555', width=1, alpha=0.5)
    sc = nx.draw_networkx_nodes(G_bus, pos, node_size=node_sizes, node_color=node_colors, cmap=plt.cm.plasma, alpha=0.9)
    plt.colorbar(sc, label='Betweenness Centrality', shrink=0.7)
    
    top_bot = df_micro.sort_values(by='Betweenness Centrality', ascending=False).head(4)['Station'].tolist()
    label_p = {name: (pos[name][0], pos[name][1] + 0.001) for name in top_bot}
    nx.draw_networkx_labels(G_bus, label_p, labels={name: name for name in top_bot}, font_color='white', font_size=8, font_weight='bold')
    
    plt.title("Bologna Bus Network: Betweenness Centrality Hotspots", color='white', fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/bologna_tube_hotspots.png", dpi=300)
    plt.close()

    print("\n=== Phase 3: Macroscopic Analysis & Small-Worldness ===")
    sw_bus = compute_small_worldness(G_bus)
    sw_tram = compute_small_worldness(G_tram)
    
    print(f"{'Metrica':<30}{'Rete Bus':<15}{'Rete Bus+Tram':<15}")
    print("-" * 60)
    print(f"{'Avg Path Length L':<30}{sw_bus['L']:.4f}{'':<8}{sw_tram['L']:.4f}")
    print(f"{'Clustering Coeff C':<30}{sw_bus['C']:.4f}{'':<8}{sw_tram['C']:.4f}")
    print(f"{'Global Efficiency E_glob':<30}{sw_bus['E_glob']:.4f}{'':<8}{sw_tram['E_glob']:.4f}")
    print(f"{'Local Efficiency E_loc':<30}{sw_bus['E_loc']:.4f}{'':<8}{sw_tram['E_loc']:.4f}")
    print(f"{'Small-Worldness Sigma':<30}{sw_bus['sigma']:.4f}{'':<8}{sw_tram['sigma']:.4f}")
    print(f"{'Small-Worldness Omega':<30}{sw_bus['omega']:.4f}{'':<8}{sw_tram['omega']:.4f}")

    print("\n=== Phase 4: Resilience Stress-Test ===")
    fracs, r_lcc_bus, t_lcc_bus, r_frag_bus, t_frag_bus, r_eff_bus, t_eff_bus = run_resilience_simulation(G_bus, random_runs=50)
    _, r_lcc_tram, t_lcc_tram, r_frag_tram, t_frag_tram, r_eff_tram, t_eff_tram = run_resilience_simulation(G_tram, random_runs=50)
    
    # Plot LCC Decay
    plt.figure(figsize=(7, 5))
    plt.plot(fracs * 100, t_lcc_bus, 's--', color='#e74c3c', label='Targeted Attack (Bus Only)', linewidth=2)
    plt.plot(fracs * 100, t_lcc_tram, 's-', color='#27ae60', label='Targeted Attack (Bus+Tram)', linewidth=2)
    plt.plot(fracs * 100, r_lcc_bus, 'o--', color='#3498db', label='Random Failure (Bus Only)', linewidth=1.5)
    plt.xlabel('Fraction of Nodes Removed (%)')
    plt.ylabel('Relative Size of LCC')
    plt.title('Connectedness decay (LCC) under Node Removal', fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/resilience_lcc.png", dpi=300)
    plt.close()
    
    # Plot Fragmentation
    plt.figure(figsize=(7, 5))
    plt.plot(fracs * 100, t_frag_bus, 's--', color='#e74c3c', label='Targeted Attack (Bus Only)', linewidth=2)
    plt.plot(fracs * 100, t_frag_tram, 's-', color='#27ae60', label='Targeted Attack (Bus+Tram)', linewidth=2)
    plt.plot(fracs * 100, r_frag_bus, 'o--', color='#3498db', label='Random Failure (Bus Only)', linewidth=1.5)
    plt.xlabel('Fraction of Nodes Removed (%)')
    plt.ylabel('Number of Connected Components')
    plt.title('Network Fragmentation under Node Removal', fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/resilience_frag.png", dpi=300)
    plt.close()
    
    # Plot Global Efficiency Decay
    plt.figure(figsize=(7, 5))
    plt.plot(fracs * 100, t_eff_bus, 's--', color='#e74c3c', label='Targeted Attack (Bus Only)', linewidth=2)
    plt.plot(fracs * 100, t_eff_tram, 's-', color='#27ae60', label='Targeted Attack (Bus+Tram)', linewidth=2)
    plt.plot(fracs * 100, r_eff_bus, 'o--', color='#3498db', label='Random Failure (Bus Only)', linewidth=1.5)
    plt.xlabel('Fraction of Nodes Removed (%)')
    plt.ylabel('Relative Global Efficiency')
    plt.title('Global Efficiency Decay under Node Removal', fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/resilience_eff.png", dpi=300)
    plt.close()

    print("\n=== Phase 5: Demographic Demand-Weighted Efficiency & Justification ===")
    eff_bus = compute_demand_weighted_efficiency(G_bus, df_demo)
    eff_real_tram = compute_demand_weighted_efficiency(G_tram, df_demo)
    
    # What-if alternative campus line
    G_alt = G_bus.copy()
    alt_edges = [
        ("Lazzaretto", "Navile", 3.0),
        ("Navile", "Piazza Spadolini", 4.0),
        ("Piazza Spadolini", "Porta San Donato", 3.0)
    ]
    for u, v, t in alt_edges:
        if G_alt.has_edge(u, v):
            if 104 not in G_alt[u][v]['lines']:
                G_alt[u][v]['lines'].append(104)
        else:
            lat1, lon1 = G_alt.nodes[u]['lat'], G_alt.nodes[u]['lon']
            lat2, lon2 = G_alt.nodes[v]['lat'], G_alt.nodes[v]['lon']
            dist = haversine(lat1, lon1, lat2, lon2)
            G_alt.add_edge(u, v, weight=dist, time=t, lines=[104])
            
    eff_alt_tram = compute_demand_weighted_efficiency(G_alt, df_demo)
    
    print(f"Efficienza di Trasporto Pesata sulla Domanda (UNIBO Campus Accessibility):")
    print(f"  1. Rete Bus Attuale (Bus Only):                  {eff_bus:.6f}")
    print(f"  2. Rete Integrata con Tram Reale (Bus+Tram):      {eff_real_tram:.6f} (+{((eff_real_tram - eff_bus)/eff_bus)*100:.2f}%)")
    print(f"  3. Rete Integrata con Tram Alternativo Campus:    {eff_alt_tram:.6f} (+{((eff_alt_tram - eff_bus)/eff_bus)*100:.2f}%)")
    
    # Plot justification comparison
    plt.figure(figsize=(7, 5))
    scenarios = ['Bus Only', 'Real Tram (Linea Rossa/Verde)', 'Alternative Campus Tram']
    efficiencies = [eff_bus, eff_real_tram, eff_alt_tram]
    colors = ['#7f8c8d', '#27ae60', '#2980b9']
    
    plt.bar(scenarios, efficiencies, color=colors, edgecolor='black', width=0.5, alpha=0.85)
    plt.ylabel('Demand-Weighted Transport Efficiency')
    plt.title('Bologna: Comparing Transit Layout Efficiencies', fontweight='bold', pad=15)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    for i, v in enumerate(efficiencies):
        plt.text(i, v + 0.005, f"{v:.4f}", ha='center', fontweight='bold')
    plt.ylim(0, max(efficiencies) * 1.2)
    plt.tight_layout()
    plt.savefig("latex/figures/bologna/bologna_tram_comparison.png", dpi=300)
    plt.close()

    print("\n[SUCCESS] Bologna transit network analysis complete! Figures exported to latex/figures/bologna/.")

if __name__ == "__main__":
    main()
