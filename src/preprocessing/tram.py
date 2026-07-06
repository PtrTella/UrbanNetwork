import pandas as pd
import numpy as np
import json
import time
import re
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Configurazione Percorsi
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "dataset" / "bologna" / "raw"
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"

# Usiamo il JSON strutturato con le tratte divise in segmenti
INPUT_JSON = RAW_DIR / "tram_structured.json"
OSM_RAW_CSV = RAW_DIR / "osm_tram_stops.csv"

geolocator = Nominatim(user_agent="bologna_transit_lspace_builder")

# Svuotato come richiesto: ora i nomi matchano o si correggono nel CSV
MANUAL_OVERRIDES = {
    "Stazione Corticella": "CORTICELLA STAZIONE",
    "Giacomo Matteotti-Stazione AV": "MATTEOTTI ALTA VELOCITA",
    "Sant'Anna-Byron": "SANT`ANNA",
}

COORDINATE_OVERRIDES = {
    "Shakespeare": (44.550571, 11.358646),
    "Teatro Centofiori": (44.546272, 11.356402),
}


def normalize_name(name):
    """Pulisce la stringa da accenti e la standardizza in maiuscolo."""
    name = str(name).upper()
    replacements = {"À": "A", "È": "E", "É": "E", "Ì": "I", "Ò": "O", "Ù": "U"}
    for k, v in replacements.items():
        name = name.replace(k, v)
    name = re.sub(r"[^A-Z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def get_coordinates(address, retries=3):
    """Fallback estremo su Geopy/Nominatim"""
    for attempt in range(retries):
        try:
            location = geolocator.geocode(f"{address}, Bologna, Italy")
            if location:
                return location.latitude, location.longitude
        except GeocoderTimedOut:
            time.sleep(2)
    return None, None


def consolidate_bidirectional_stops(df_nodes, df_edges):
    """
    Fonde le fermate doppie/bidirezionali. Versione semplificata:
    raggruppa per nome e prende banalmente il primo record utile per ID e Coordinate.
    """
    print(
        f"\n Consolidamento. Nodi iniziali: {len(df_nodes)} | Archi: {len(df_edges)}"
    )

    # Prendi la prima occorrenza per ogni stazione (metodo ultra-semplificato)
    df_merged_nodes = df_nodes.groupby("stop_name", as_index=False).first()

    # Dizionario di mapping per aggiornare gli archi (es. se palo sud diventa palo nord)
    mapping_dict = {}
    for name, group in df_nodes.groupby("stop_name"):
        rep_id = group["stop_id"].iloc[0]
        for old_id in group["stop_id"]:
            mapping_dict[old_id] = rep_id

    # Aggiorna gli ID negli archi
    df_edges["stop_id"] = df_edges["stop_id"].map(mapping_dict)
    df_edges["next_stop_id"] = df_edges["next_stop_id"].map(mapping_dict)

    # Rimuovi i self-loops (es. palo A -> palo B fusi insieme)
    df_edges = df_edges[df_edges["stop_id"] != df_edges["next_stop_id"]]

    # Rimuovi i doppioni non orientati (A->B e B->A)
    arr = np.sort(df_edges[["stop_id", "next_stop_id"]].values, axis=1)
    df_edges["u"] = arr[:, 0]
    df_edges["v"] = arr[:, 1]
    df_edges = df_edges.drop_duplicates(subset=["u", "v", "route_id"]).drop(
        columns=["u", "v"]
    )

    print(
        f" Semplificazione fatta! Nodi unici: {len(df_merged_nodes)} | Archi finali: {len(df_edges)}"
    )
    return df_merged_nodes, df_edges


def process_tram_network():
    print("--- PREPROCESSING RETE TRAM (EXACT CSV -> BUS -> GPS) ---")

    if not INPUT_JSON.exists():
        print(f" Errore: {INPUT_JSON.name} non trovato.")
        return

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        tram_data = json.load(f)

    # 1. Carica CSV Tram da OSM
    osm_stops_dict = {}
    if OSM_RAW_CSV.exists():
        df_osm = pd.read_csv(OSM_RAW_CSV)
        for _, row in df_osm.iterrows():
            osm_stops_dict[normalize_name(row["stop_name"])] = (row["lat"], row["lon"])
        print(f" Caricate {len(osm_stops_dict)} fermate dal CSV OSM.")

    # 2. Carica CSV Bus per il primo Fallback
    bus_csv_path = PROCESSED_DIR / "bologna_stations.csv"
    bus_coords_dict = {}
    if bus_csv_path.exists():
        df_bus_nodes = pd.read_csv(bus_csv_path)
        for _, row in df_bus_nodes.iterrows():
            bus_coords_dict[normalize_name(row["stop_name"])] = (
                row["stop_lat"],
                row["stop_lon"],
            )
        print(f" Caricate {len(bus_coords_dict)} fermate dal CSV BUS (Fallback).")

    tram_nodes_csv = []

    print("\n Fusione Geografica in corso...")
    for stop in tram_data["stations"]:
        json_id = stop["id"]
        original_name = stop["name"]

        if original_name in MANUAL_OVERRIDES:
            original_name = MANUAL_OVERRIDES[original_name]

        name_upper = normalize_name(original_name)
        lat, lon = None, None

        # OVERRIDE COORDINATE MANUALE
        if original_name in COORDINATE_OVERRIDES:
            lat, lon = COORDINATE_OVERRIDES[original_name]
            print(f"   [MANUAL OVERRIDE] {name_upper}")

        # TENTATIVO 1: Exact Match su OSM CSV
        elif name_upper in osm_stops_dict:
            lat, lon = osm_stops_dict[name_upper]
            print(f"   [OSM CSV] {name_upper}")

        # TENTATIVO 2: Exact Match su BUS CSV
        elif name_upper in bus_coords_dict:
            lat, lon = bus_coords_dict[name_upper]
            print(f"   [Bus Match] {name_upper}")

        # TENTATIVO 3: Fallback Geopy API
        else:
            lat, lon = get_coordinates(original_name)
            if lat and lon:
                print(f"   [Geopy API] {name_upper}")
            else:
                lat, lon = 44.4949, 11.3426
                print(f"   [Fallito] '{name_upper}' -> Assegnato Centro di Bologna.")

        tram_nodes_csv.append(
            {
                "stop_id": json_id,
                "stop_name": name_upper,
                "stop_lat": lat,
                "stop_lon": lon,
                "node_type": stop.get("node_type", "fermata"),
            }
        )

    df_tram_nodes = pd.DataFrame(tram_nodes_csv)

    # Creazione Archi dal JSON Strutturato
    edges_data = []
    for route_id, segments in tram_data.get("routes", {}).items():
        for path in segments:
            for u, v in zip(path[:-1], path[1:]):
                edges_data.append(
                    {
                        "stop_id": u,
                        "next_stop_id": v,
                        "route_id": route_id,
                    }
                )
    df_tram_edges = pd.DataFrame(edges_data)

    # Consolidamento Nodi
    df_tram_nodes, df_tram_edges = consolidate_bidirectional_stops(
        df_tram_nodes, df_tram_edges
    )

    df_tram_nodes.to_csv(PROCESSED_DIR / "bologna_tram_stations.csv", index=False)
    df_tram_edges.to_csv(PROCESSED_DIR / "bologna_tram_connections.csv", index=False)

    print("\n Topologia L-Space Salvata!")


if __name__ == "__main__":
    process_tram_network()
