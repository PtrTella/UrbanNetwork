import os
import networkx as nx
import matplotlib.pyplot as plt

# Import from our modular source code package
from src.data_loader import load_london_network
from src.analyzer import compute_centralities, compute_small_worldness
from src.simulator import run_resilience_simulation

# Create target directories
os.makedirs("data_output", exist_ok=True)
os.makedirs("latex/figures", exist_ok=True)

# -------------------------------------------------------------
# 1. DATA ACQUISITION & PREPROCESSING (London Underground)
# -------------------------------------------------------------
print("=== Phase 1: Data Ingestion & Preprocessing ===")
G_L, df_stations, df_connections, df_lines = load_london_network()

N = len(G_L.nodes)
M = len(G_L.edges)
print("Network Statistics:")
print(f"  Stations (Nodes, N): {N}")
print(f"  Connections (Edges, M): {M}")
print(f"  Density (p): {nx.density(G_L):.6f}")
print(f"  Is Connected: {nx.is_connected(G_L)}")

# Save Geographical Layout
print("  Generating official geographical layout plot...")
line_colors = {
    int(row["line"]): f"#{row['colour']}" for idx, row in df_lines.iterrows()
}
pos = {node: (data["lon"], data["lat"]) for node, data in G_L.nodes(data=True)}
edge_colors = [
    line_colors.get(G_L[u][v]["lines"][0], "#999999") for u, v in G_L.edges()
]

plt.figure(figsize=(12, 10))
plt.gca().set_facecolor("#fdfefe")
nx.draw_networkx_edges(G_L, pos, edge_color=edge_colors, width=2, alpha=0.8)
nx.draw_networkx_nodes(G_L, pos, node_size=20, node_color="black", alpha=0.8)
plt.title(
    "Geographical Layout of the London Underground (Tube) in L-Space",
    fontsize=15,
    fontweight="bold",
)
plt.axis("off")
plt.tight_layout()
plt.savefig("latex/figures/london_tube_map.png", dpi=300)
plt.close()
print("  Saved geographical map to: latex/figures/london_tube_map.png")

# Export as GraphML (strip tuple attributes to prevent GraphML serialization error)
print("  Serializing network to GraphML...")
G_export = G_L.copy()
for node, data in G_export.nodes(data=True):
    if "pos" in data:
        del data["pos"]
for u, v, data in G_export.edges(data=True):
    data["lines"] = str(data["lines"])
nx.write_graphml(G_export, "data_output/london_tube.graphml")
print("  Saved graph file to: data_output/london_tube.graphml")


# -------------------------------------------------------------
# 2. MICROSCOPIC, K-CORE, & DEGREE DISTRIBUTION ANALYSIS
# -------------------------------------------------------------
print("\n=== Phase 2: Microscopic & k-Core Analysis ===")
df_micro = compute_centralities(G_L)

print("\nTop 5 Stations by Degree (Physical Interchange Hubs):")
print(df_micro.sort_values(by="Degree", ascending=False).head(5)[["Station", "Degree"]])

print("\nTop 5 Stations by Closeness Centrality (Geometric Centers):")
print(
    df_micro.sort_values(by="Closeness Centrality", ascending=False).head(5)[
        ["Station", "Closeness Centrality"]
    ]
)

print("\nTop 5 Stations by Betweenness Centrality (Structural Bottlenecks):")
print(
    df_micro.sort_values(by="Betweenness Centrality", ascending=False).head(5)[
        ["Station", "Betweenness Centrality"]
    ]
)

# Coreness stats
print("\nCoreness Shell Distribution:")
print(df_micro["Coreness"].value_counts())
k_max = df_micro["Coreness"].max()
print(f"Maximum Coreness (k_max): {k_max}")
max_core_stations = df_micro[df_micro["Coreness"] == k_max]["Station"].tolist()
print(
    f"Number of stations in the innermost ({k_max}-core) shell: {len(max_core_stations)}"
)

# Plot and save node degree distribution
print("\n  Generating degree distribution plot...")
deg_counts = df_micro["Degree"].value_counts().sort_index()
plt.figure(figsize=(7, 5))
plt.bar(
    deg_counts.index, deg_counts.values, color="#8e44ad", edgecolor="black", alpha=0.8
)
plt.xlabel("Degree (k)", fontsize=12)
plt.ylabel("Frequency (Count)", fontsize=12)
plt.title(
    "London Tube: Bounded Node Degree Distribution",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
plt.xticks(deg_counts.index)
plt.grid(axis="y", linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig("latex/figures/london_degree_dist.png", dpi=300)
plt.close()
print("  Saved degree distribution plot to: latex/figures/london_degree_dist.png")

# Save centrality plots
print("  Generating centrality hotspots visualization...")
bet_dict = dict(zip(df_micro["Station"], df_micro["Betweenness Centrality"]))
node_sizes = [15 + 450 * bet_dict[node] for node in G_L.nodes()]
node_colors = [bet_dict[node] for node in G_L.nodes()]

plt.figure(figsize=(12, 10))
plt.gca().set_facecolor("#1a1a1a")
nx.draw_networkx_edges(G_L, pos, edge_color="#555555", width=1, alpha=0.5)
sc = nx.draw_networkx_nodes(
    G_L,
    pos,
    node_size=node_sizes,
    node_color=node_colors,
    cmap=plt.cm.plasma,
    alpha=0.9,
)
plt.colorbar(sc, label="Betweenness Centrality", shrink=0.7)

top_bottlenecks = (
    df_micro.sort_values(by="Betweenness Centrality", ascending=False)
    .head(5)["Station"]
    .tolist()
)
label_pos = {name: (pos[name][0], pos[name][1] + 0.005) for name in top_bottlenecks}
nx.draw_networkx_labels(
    G_L,
    label_pos,
    labels={name: name for name in top_bottlenecks},
    font_color="white",
    font_size=10,
    font_weight="bold",
)
plt.title(
    "London Tube: Identifying Structural Bottlenecks (Betweenness Centrality)",
    color="white",
    fontsize=15,
    fontweight="bold",
)
plt.axis("off")
plt.tight_layout()
plt.savefig("latex/figures/london_tube_hotspots.png", dpi=300)
plt.close()
print("  Saved hotspots visualization to: latex/figures/london_tube_hotspots.png")

# Save table csv
df_micro.to_csv("data_output/london_centralities.csv", index=False)
print("  Saved table to: data_output/london_centralities.csv")


# -------------------------------------------------------------
# 3. MACROSCOPIC ANALYSIS & SMALL-WORLDNESS
# -------------------------------------------------------------
print("\n=== Phase 3: Macroscopic Analysis & Small-Worldness ===")
sw_results = compute_small_worldness(G_L, er_runs=50)

print(f"Empirical Average Path Length (L): {sw_results['L']:.4f}")
print(f"Empirical Clustering Coefficient (C): {sw_results['C']:.4f}")
print(f"Empirical Global Efficiency (E_glob): {sw_results['E_glob']:.4f}")
print(f"Empirical Local Efficiency (E_loc): {sw_results['E_loc']:.4f}")
print("Erdos-Renyi Random Graph Null Model (LCC):")
print(f"  L_rand: {sw_results['L_rand']:.4f}")
print(f"  C_rand: {sw_results['C_rand']:.4f}")
print(
    f"  Small-Worldness Sigma: {sw_results['sigma']:.4f} (Sigma > 1 implies Small-World)"
)
print("1D Regular Lattice Null Model:")
print(f"  L_lat: {sw_results['L_lat']:.4f}")
print(f"  C_lat: {sw_results['C_lat']:.4f}")
print(
    f"  Small-Worldness Omega: {sw_results['omega']:.4f} (Omega ~ 0 implies Small-World)"
)


# -------------------------------------------------------------
# 4. RESILIENCE STRESS-TEST
# -------------------------------------------------------------
print("\n=== Phase 4: Resilience Stress-Test ===")
(
    fractions,
    random_lcc,
    targeted_lcc,
    random_frag,
    targeted_frag,
    random_eff,
    targeted_eff,
) = run_resilience_simulation(G_L, random_runs=50)

print("\nTabular Resilience Data:")
print(
    f"{'Fraction %':<12}{'Rand LCC':<12}{'Target LCC':<12}{'Rand Frag':<12}{'Target Frag':<12}{'Rand Eff':<12}{'Target Eff':<12}"
)
for i, f in enumerate(fractions):
    print(
        f"{f * 100:<12.1f}{random_lcc[i]:<12.4f}{targeted_lcc[i]:<12.4f}{random_frag[i]:<12.2f}{targeted_frag[i]:<12.2f}{random_eff[i]:<12.4f}{targeted_eff[i]:<12.4f}"
    )

# LCC size plot
plt.figure(figsize=(7, 5))
plt.plot(
    fractions * 100,
    random_lcc,
    "o-",
    color="#3498db",
    label="Random Failure (Scenario A)",
    linewidth=2,
)
plt.plot(
    fractions * 100,
    targeted_lcc,
    "s-",
    color="#e74c3c",
    label="Targeted Attack (Scenario B)",
    linewidth=2,
)
plt.xlabel("Fraction of Nodes Removed (%)", fontsize=12)
plt.ylabel("Relative Size of LCC", fontsize=12)
plt.title(
    "London Tube: Connectedness under Node Removal",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(fontsize=10, loc="lower left")
plt.tight_layout()
plt.savefig("latex/figures/resilience_lcc.png", dpi=300)
plt.close()
print("  Saved decay curves plot to: latex/figures/resilience_lcc.png")

# Fragmentation plot
plt.figure(figsize=(7, 5))
plt.plot(
    fractions * 100,
    random_frag,
    "o-",
    color="#3498db",
    label="Random Failure (Scenario A)",
    linewidth=2,
)
plt.plot(
    fractions * 100,
    targeted_frag,
    "s-",
    color="#e74c3c",
    label="Targeted Attack (Scenario B)",
    linewidth=2,
)
plt.xlabel("Fraction of Nodes Removed (%)", fontsize=12)
plt.ylabel("Number of Connected Components", fontsize=12)
plt.title(
    "London Tube: Fragmentation under Node Removal",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(fontsize=10, loc="upper left")
plt.tight_layout()
plt.savefig("latex/figures/resilience_frag.png", dpi=300)
plt.close()
print("  Saved fragmentation plot to: latex/figures/resilience_frag.png")

# Global Efficiency Decay plot
plt.figure(figsize=(7, 5))
plt.plot(
    fractions * 100,
    random_eff,
    "o-",
    color="#3498db",
    label="Random Failure (Scenario A)",
    linewidth=2,
)
plt.plot(
    fractions * 100,
    targeted_eff,
    "s-",
    color="#e74c3c",
    label="Targeted Attack (Scenario B)",
    linewidth=2,
)
plt.xlabel("Fraction of Nodes Removed (%)", fontsize=12)
plt.ylabel("Relative Global Efficiency", fontsize=12)
plt.title(
    "London Tube: Global Efficiency under Node Removal",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
plt.grid(True, linestyle="--", alpha=0.5)
plt.legend(fontsize=10, loc="lower left")
plt.tight_layout()
plt.savefig("latex/figures/resilience_eff.png", dpi=300)
plt.close()
print("  Saved efficiency decay plot to: latex/figures/resilience_eff.png")


# -------------------------------------------------------------
# 5. VISUALIZING NETWORK COLLAPSE UNDER TARGETED ATTACK
# -------------------------------------------------------------
print("\n=== Phase 5: Generating Geographical Collapse Visualization ===")
G_temp = G_L.copy()

# Sort by original Betweenness Centrality
original_bet = nx.betweenness_centrality(G_L, weight="weight")
sorted_nodes = sorted(original_bet.items(), key=lambda x: x[1], reverse=True)
removed_nodes = [node for node, val in sorted_nodes[:10]]

# Remove the top 10 bottleneck stations
G_temp.remove_nodes_from(removed_nodes)

# Find remaining components
components = sorted(list(nx.connected_components(G_temp)), key=len, reverse=True)
lcc_nodes = components[0] if components else set()

plt.figure(figsize=(12, 10))
plt.gca().set_facecolor("#f7f9f9")

# 1. Draw intact edges in light gray
nx.draw_networkx_edges(G_temp, pos, edge_color="#cccccc", width=1.5, alpha=0.7)

# 2. Draw nodes in LCC (Giant Component) - Green
nx.draw_networkx_nodes(
    G_temp,
    nodelist=list(lcc_nodes),
    pos=pos,
    node_size=30,
    node_color="#2ecc71",
    label="Largest Connected Component",
)

# 3. Draw nodes in fragmented components - Orange
fragmented_nodes = []
for comp in components[1:]:
    fragmented_nodes.extend(list(comp))
if fragmented_nodes:
    nx.draw_networkx_nodes(
        G_temp,
        nodelist=fragmented_nodes,
        pos=pos,
        node_size=30,
        node_color="#e67e22",
        label="Isolated Components",
    )

# 4. Draw removed nodes (top bottlenecks) - Red crosses
nx.draw_networkx_nodes(
    G_L,
    nodelist=removed_nodes,
    pos=pos,
    node_size=80,
    node_color="#e74c3c",
    node_shape="x",
    label="Removed Bottlenecks",
)

# Label the removed nodes
removed_pos = {name: (pos[name][0], pos[name][1] + 0.004) for name in removed_nodes}
nx.draw_networkx_labels(
    G_L,
    removed_pos,
    labels={name: name for name in removed_nodes},
    font_color="#c0392b",
    font_size=8,
    font_weight="bold",
)

plt.title(
    "Visualizing Collapse: London Underground after Removing Top 10 Bottleneck Stations",
    fontsize=14,
    fontweight="bold",
)
plt.legend(loc="lower left", fontsize=11)
plt.axis("off")
plt.tight_layout()
plt.savefig("latex/figures/london_tube_collapse.png", dpi=300)
plt.close()

print("Collapse visualization generated.")
print(f"  Removed nodes: {removed_nodes}")
print(
    f"  LCC size: {len(lcc_nodes)} nodes ({len(lcc_nodes) / N * 100:.2f}% of original)"
)
print(f"  Number of remaining components: {len(components)}")
print("\n[SUCCESS] All analysis scripts executed and output figures updated!")
