# src/graph.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import networkx as nx
import numpy as np

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

    # 1. Carica Nodi Bus (Leggiamo traffico, capacità stradale, e incidenti in un singolo passo)
    for _, row in df_bus_nodes.iterrows():
        G.add_node(
            str(row["stop_id"]),
            name=row["stop_name"],
            lat=row["stop_lat"],
            lon=row["stop_lon"],
            traffic=row.get("nearest_traffic_flow", 0),  # Flusso di picco orario
            capacity=row.get("road_capacity", 1000),  # Capacità dinamica della via
            accidents=row.get("accidents_300m", 0),  # Rischio stocastico di incidenti
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
            # Clamp di sicurezza per impedire divisioni per zero se la capacità stradale è nulla
            avg_capacity = max(1.0, (G.nodes[u]["capacity"] + G.nodes[v]["capacity"]) / 2.0)

            # FUNZIONE BPR DINAMICA: Ogni via ha la sua C (avg_capacity)
            # Legge solo ALPHA e BETA da config.py per il comportamento della curva
            bpr_penalty = 1.0 + TransitConfig.BPR_ALPHA * (
                (avg_traffic_peak / avg_capacity) ** TransitConfig.BPR_BETA
            )

            effective_speed = TransitConfig.BUS_BASE_SPEED / bpr_penalty
            if effective_speed < TransitConfig.MIN_BUS_SPEED:
                effective_speed = TransitConfig.MIN_BUS_SPEED

            travel_time_sec = dist_m / effective_speed + TransitConfig.BUS_DWELL_TIME
            G.add_edge(
                u,
                v,
                weight=travel_time_sec,
                dist_meters=dist_m,
                type="bus",
                route_id=row.get("route_id"),
            )

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

                    # Trasbordo Pedonale Multiplex con Frizione (Cammino + Attesa + Penalità Cognitiva)
                    transfer_time = (
                        (min_dist / TransitConfig.WALKING_SPEED)
                        + TransitConfig.TRANSFER_WAITING_TIME
                        + TransitConfig.TRANSFER_COGNITIVE_PENALTY
                    )
                    G.add_edge(
                        tram_id,
                        closest_bus_id,
                        weight=transfer_time,
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

                tram_time_sec = dist_m / TransitConfig.TRAM_SPEED + TransitConfig.TRAM_DWELL_TIME
                G.add_edge(
                    u,
                    v,
                    weight=tram_time_sec,
                    dist_meters=dist_m,
                    type="tram",
                    route_id=row.get("route_id"),
                )

    print(
        f"✅ Grafo Integrato ({integration_mode}): {G.number_of_nodes()} Nodi, {G.number_of_edges()} Archi. (Pesi Temporali Rigorosi BPR)"
    )
    return G


def load_cached_graph(name, scenario=None, integration_mode="fused"):
    """
    Tenta di caricare un grafo salvato in formato pickle da data_output/bologna/graphs/.
    Se non esiste, lo calcola al volo e lo salva.
    """
    import pickle

    cache_path = BASE_DIR / "data_output" / "bologna" / "graphs" / f"{name}.pkl"
    if cache_path.exists():
        try:
            with open(cache_path, "rb") as f:
                G = pickle.load(f)
            print(f"✅ Caricato grafo cached da: {cache_path}")
            return G
        except Exception as e:
            print(f"⚠️ Errore nel caricamento cache: {e}. Ricostruzione...")

    # Ricostruzione in caso di mancanza cache
    if name == "G_bus":
        G = load_bologna_graph(scenario="bus_only")
    elif name == "G_fused":
        G = load_bologna_graph(scenario="tram", integration_mode="fused")
    elif name == "G_multiplex":
        G = load_bologna_graph(scenario="tram", integration_mode="multiplex")
    elif name == "G_futuro":
        from src.scenarios import inject_hypothetical_tram

        G_f = load_cached_graph("G_fused")
        G = inject_hypothetical_tram(G_f, route_to_upgrade="32")
    else:
        G = load_bologna_graph(scenario=scenario, integration_mode=integration_mode)

    # Salva in cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "wb") as f:
        pickle.dump(G, f)
    print(f"✅ Grafo salvato in cache: {cache_path}")
    return G


if __name__ == "__main__":
    import pickle
    from src.scenarios import inject_hypothetical_tram

    OUTPUT_DIR = BASE_DIR / "data_output" / "bologna" / "graphs"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("🚀 Loading and saving all graphs to graphs/ directory...")
    G_bus = load_bologna_graph(scenario="bus_only")
    G_fused = load_bologna_graph(scenario="tram", integration_mode="fused")
    G_multi = load_bologna_graph(scenario="tram", integration_mode="multiplex")
    G_futuro = inject_hypothetical_tram(G_fused, route_to_upgrade="32")

    for name, G in [
        ("G_bus", G_bus),
        ("G_fused", G_fused),
        ("G_multiplex", G_multi),
        ("G_futuro", G_futuro),
    ]:
        path = OUTPUT_DIR / f"{name}.pkl"
        with open(path, "wb") as f:
            pickle.dump(G, f)
        print(f"  ✅ Saved {name} to {path}")
