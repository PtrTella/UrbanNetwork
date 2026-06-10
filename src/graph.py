import pandas as pd
import networkx as nx
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    return R * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


def load_bologna_graph(scenario="bus_only"):
    print(f"Caricamento Grafo Integrato - Scenario: {scenario.upper()}")

    # 1. Carica Bus
    df_bus_nodes = pd.read_csv(PROCESSED_DIR / "bologna_stations.csv")
    df_bus_edges = pd.read_csv(PROCESSED_DIR / "bologna_connections.csv")

    G = nx.Graph()

    # Popola Nodi da Bus
    for _, row in df_bus_nodes.iterrows():
        G.add_node(
            str(row["stop_id"]),
            name=row["stop_name"],
            lat=row["stop_lat"],
            lon=row["stop_lon"],
            type="bus",
        )

    # Aggiungi Archi Bus
    for _, row in df_bus_edges.iterrows():
        u, v = str(row["stop_id"]), str(row["next_stop_id"])
        if u in G and v in G:
            G.add_edge(
                u,
                v,
                weight=haversine(
                    G.nodes[u]["lat"],
                    G.nodes[u]["lon"],
                    G.nodes[v]["lat"],
                    G.nodes[v]["lon"],
                ),
                type="bus",
            )

    # 2. Carica Tram (SE RICHIESTO)
    if scenario != "bus_only":
        df_tram_nodes = pd.read_csv(PROCESSED_DIR / "bologna_tram_stations.csv")
        df_tram_edges = pd.read_csv(PROCESSED_DIR / "bologna_tram_connections.csv")

        # Popola Nodi Tram (se non esistono già)
        for _, row in df_tram_nodes.iterrows():
            nid = str(row["stop_id"])
            if nid not in G:
                G.add_node(
                    nid,
                    name=row["stop_name"],
                    lat=row["stop_lat"],
                    lon=row["stop_lon"],
                    type="tram",
                )

        # Aggiungi Archi Tram
        for _, row in df_tram_edges.iterrows():
            u, v = str(row["stop_id"]), str(row["next_stop_id"])
            if u in G and v in G:
                # Il tram ha peso ridotto (sede protetta)
                dist = haversine(
                    G.nodes[u]["lat"],
                    G.nodes[u]["lon"],
                    G.nodes[v]["lat"],
                    G.nodes[v]["lon"],
                )
                G.add_edge(u, v, weight=dist * 0.5, type="tram")

    print(
        f"✅ Grafo Integrato: {G.number_of_nodes()} Nodi, {G.number_of_edges()} Archi."
    )
    return G
