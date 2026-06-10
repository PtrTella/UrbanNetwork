# src/graph.py
import pandas as pd
import networkx as nx
import numpy as np
from pathlib import Path
from src.config import TransitConfig  # <-- Importiamo la configurazione

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2.0) ** 2
    return R * 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))


def load_bologna_graph(scenario="bus_only", integration_mode="fused"):
    print(
        f"Caricamento Grafo - Scenario: {scenario.upper()} | Modalità: {integration_mode.upper()}"
    )

    df_bus_nodes = pd.read_csv(PROCESSED_DIR / "bologna_stations.csv")
    df_bus_edges = pd.read_csv(PROCESSED_DIR / "bologna_connections.csv")

    G = nx.Graph()

    # 1. Carica Nodi Bus
    for _, row in df_bus_nodes.iterrows():
        G.add_node(
            str(row["stop_id"]),
            name=row["stop_name"],
            lat=row["stop_lat"],
            lon=row["stop_lon"],
            traffic=row.get("nearest_traffic_flow", 0),  # Ora contiene il picco orario!
            accidents=row.get(
                "accidents_300m", 0
            ),  # Diventa un attributo stocastico di rischio
            type="bus",
        )

    # 1. Carica Bus (Leggiamo anche la capacità specifica!)
    for _, row in df_bus_nodes.iterrows():
        G.add_node(
            str(row["stop_id"]),
            name=row["stop_name"],
            lat=row["stop_lat"],
            lon=row["stop_lon"],
            traffic=row.get("nearest_traffic_flow", 0),
            capacity=row.get("road_capacity", 1000),  # <-- CAPACITÀ DINAMICA DELLA VIA
            accidents=row.get("accidents_300m", 0),
            type="bus",
        )

    # 2. Archi Bus (Formula BPR con Capacità Dinamica Locale)
    for _, row in df_bus_edges.iterrows():
        u, v = str(row["stop_id"]), str(row["next_stop_id"])
        if u in G and v in G:
            dist_m = haversine(
                G.nodes[u]["lat"],
                G.nodes[u]["lon"],
                G.nodes[v]["lat"],
                G.nodes[v]["lon"],
            )

            # Calcoliamo i valori medi del segmento tra le due fermate
            avg_traffic_peak = (G.nodes[u]["traffic"] + G.nodes[v]["traffic"]) / 2.0
            avg_capacity = (G.nodes[u]["capacity"] + G.nodes[v]["capacity"]) / 2.0

            # FUNZIONE BPR DINAMICA: Ogni via ha la sua C (avg_capacity)
            # Legge solo ALPHA e BETA da config.py per il comportamento della curva
            bpr_penalty = 1.0 + TransitConfig.BPR_ALPHA * (
                (avg_traffic_peak / avg_capacity) ** TransitConfig.BPR_BETA
            )

            effective_speed = TransitConfig.BUS_BASE_SPEED / bpr_penalty
            if effective_speed < TransitConfig.MIN_BUS_SPEED:
                effective_speed = TransitConfig.MIN_BUS_SPEED

            travel_time_sec = dist_m / effective_speed
            G.add_edge(u, v, weight=travel_time_sec, dist_meters=dist_m, type="bus")

    # 3. Carica Tram
    if scenario != "bus_only":
        df_tram_nodes = pd.read_csv(PROCESSED_DIR / "bologna_tram_stations.csv")
        df_tram_edges = pd.read_csv(PROCESSED_DIR / "bologna_tram_connections.csv")
        tram_to_bus_map = {}

        for _, row in df_tram_nodes.iterrows():
            tram_id = str(row["stop_id"])
            t_lat, t_lon = row["stop_lat"], row["stop_lon"]

            min_dist = float("inf")
            closest_bus_id = None
            for n, data in G.nodes(data=True):
                if data.get("type") == "bus":
                    dist = haversine(t_lat, t_lon, data["lat"], data["lon"])
                    if dist < min_dist:
                        min_dist, closest_bus_id = dist, n

            if min_dist <= TransitConfig.SNAPPING_RADIUS:
                if integration_mode == "fused":
                    tram_to_bus_map[tram_id] = closest_bus_id
                    G.nodes[closest_bus_id]["type"] = "intersezione_bus_tram"
                elif integration_mode == "multiplex":
                    G.add_node(
                        tram_id,
                        name=row["stop_name"],
                        lat=t_lat,
                        lon=t_lon,
                        type="tram",
                        traffic=0,
                        accidents=0,
                    )
                    tram_to_bus_map[tram_id] = tram_id

                    # Trasbordo Pedonale Multiplex (Tempo a piedi in secondi)
                    G.add_edge(
                        tram_id,
                        closest_bus_id,
                        weight=min_dist / TransitConfig.WALKING_SPEED,
                        type="trasbordo_pedonale",
                    )
            else:
                G.add_node(
                    tram_id,
                    name=row["stop_name"],
                    lat=t_lat,
                    lon=t_lon,
                    type="tram",
                    traffic=0,
                    accidents=0,
                )
                tram_to_bus_map[tram_id] = tram_id

        # Archi Tram
        for _, row in df_tram_edges.iterrows():
            u = tram_to_bus_map.get(str(row["stop_id"]), str(row["stop_id"]))
            v = tram_to_bus_map.get(str(row["next_stop_id"]), str(row["next_stop_id"]))

            if u != v and u in G and v in G:
                dist_m = haversine(
                    G.nodes[u]["lat"],
                    G.nodes[u]["lon"],
                    G.nodes[v]["lat"],
                    G.nodes[v]["lon"],
                )

                # IL TRAM NON SUBISCE TRAFFICO: Tempo costante basato sulla sede protetta
                tram_time_sec = dist_m / TransitConfig.TRAM_SPEED
                G.add_edge(u, v, weight=tram_time_sec, dist_meters=dist_m, type="tram")

    print(
        f"✅ Grafo Integrato ({integration_mode}): {G.number_of_nodes()} Nodi, {G.number_of_edges()} Archi. (Pesi Temporali Rigorosi BPR)"
    )
    return G
