import pandas as pd
import networkx as nx
import os

PROCESSED_DIR = "dataset/bologna/processed"


def load_bologna_graph(scenario="bus_only"):
    """
    Costruisce il grafo L-Space caricando i CSV pre-processati.
    Scenari: 'bus_only', 'real_tram', 'alt_campus', 'alt_circular'
    """
    print(f"Caricamento Grafo - Scenario: {scenario.upper()}")

    # File Base (Sempre presenti)
    bus_nodes_file = os.path.join(PROCESSED_DIR, "bologna_stations.csv")
    bus_edges_file = os.path.join(PROCESSED_DIR, "bologna_connections.csv")

    # File Tram (Caricati solo se richiesti)
    tram_nodes_file = os.path.join(PROCESSED_DIR, "bologna_tram_stations.csv")
    tram_edges_file = os.path.join(PROCESSED_DIR, "bologna_tram_connections.csv")

    if not os.path.exists(bus_nodes_file) or not os.path.exists(bus_edges_file):
        raise FileNotFoundError(
            "CSV dei Bus mancanti. Esegui parse_and_build_dataset.py"
        )

    G = nx.DiGraph()

    # --- 1. CARICAMENTO RETE BUS BASE ---
    df_bus_nodes = pd.read_csv(bus_nodes_file)
    for _, row in df_bus_nodes.iterrows():
        G.add_node(
            str(row["stop_id"]),
            name=row["stop_name"],
            lat=row["stop_lat"],
            lon=row["stop_lon"],
            traffic_flow=row.get("nearest_traffic_flow", 0),
            accidents=row.get("accidents_300m", 0),
            type="bus",
        )

    df_bus_edges = pd.read_csv(bus_edges_file)
    for _, row in df_bus_edges.iterrows():
        u, v = str(row["stop_id"]), str(row["next_stop_id"])
        if u in G and v in G:
            # Calcolo del peso dell'arco basato sul traffico
            avg_traffic = (
                G.nodes[u].get("traffic_flow", 0) + G.nodes[v].get("traffic_flow", 0)
            ) / 2.0
            weight = 1.0 + (avg_traffic / 15000.0)

            G.add_edge(
                u,
                v,
                route=row["route_id"],
                type="bus",
                weight=weight,
                frequency=row["frequency"],
            )

    # --- 2. CARICAMENTO RETE TRAM (SE RICHIESTO) ---
    if scenario != "bus_only":
        if not os.path.exists(tram_nodes_file) or not os.path.exists(tram_edges_file):
            raise FileNotFoundError(
                "CSV del Tram mancanti. Esegui parse_and_build_tram.py"
            )

        df_tram_nodes = pd.read_csv(tram_nodes_file)
        df_tram_edges = pd.read_csv(tram_edges_file)

        # Aggiungiamo tutti i nodi fisici del tram
        for _, row in df_tram_nodes.iterrows():
            G.add_node(
                str(row["stop_id"]),
                name=row["stop_name"],
                lat=row["stop_lat"],
                lon=row["stop_lon"],
                traffic_flow=0,
                accidents=0,
                type="tram",
            )

        # Filtriamo le linee tram da attivare in base allo scenario
        allowed_routes = []
        if scenario == "real_tram":
            allowed_routes = ["101_LINEA_ROSSA", "102_LINEA_VERDE"]
        elif scenario == "alt_campus":
            allowed_routes = ["103_TRAM_CAMPUS"]
        elif scenario == "alt_circular":
            allowed_routes = ["104_TRAM_VIALI"]

        df_active_tram = df_tram_edges[df_tram_edges["route_id"].isin(allowed_routes)]

        # Aggiungiamo gli archi tram (peso basso, zero traffico)
        for _, row in df_active_tram.iterrows():
            u, v = str(row["stop_id"]), str(row["next_stop_id"])
            if u in G and v in G:
                G.add_edge(
                    u,
                    v,
                    route=row["route_id"],
                    type="tram",
                    weight=0.5,
                    frequency=row["frequency"],
                )

    print(
        f"✅ Grafo generato. Nodi: {G.number_of_nodes()}, Archi: {G.number_of_edges()}"
    )
    return G
