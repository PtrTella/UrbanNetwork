import pandas as pd
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

INPUT_JSON = RAW_DIR / "tram_official.json"
OUTPUT_JSON = RAW_DIR / "tram_annotated.json"

geolocator = Nominatim(user_agent="bologna_transit_lspace_builder")

# =========================================================
# IL CECCHINO: Mappature manuali per le fermate impossibili
# =========================================================
MANUAL_OVERRIDES = {
    "PALADOZZA": "PALASPORT",
    "INDIPENDENZA - PIAZZA VIII AGOSTO": "VIII AGOSTO",
    "ZUCCA MUSEO USTICA": "ZUCCA",
    "SANTA VIOLA OPIFICIO GOLINELLI": "BERRETTA ROSSA - OPIFICIO GOLINELLI",
    "STAZIONE BORGO PANIGALE": "BORGO PANIGALE STAZIONE",
    "GORKI TEATRO CENTOFIORI": "CENTOFIORI",
    "BENTINI VILLA TORCHI": "BENTINI",
    "TRIUMVIRATO FABBRI 1905": "TRIUMVIRATO",
}


def normalize_name(name):
    """Pulisce la stringa da accenti, backtick e punteggiatura inutile."""
    name = str(name).upper().strip()
    name = name.replace("`", "'").replace("’", "'")
    name = (
        name.replace("À", "A'")
        .replace("È", "E'")
        .replace("Ì", "I'")
        .replace("Ò", "O'")
        .replace("Ù", "U'")
    )
    # Rimuove caratteri speciali mantenendo lettere, numeri, spazi e apostrofi
    name = re.sub(r"[^A-Z0-9\s']", " ", name)
    return " ".join(name.split())


def get_coordinates_from_map(stop_name):
    """Ricerca su OSM con strategie progressive."""
    # Split per trattino o spazio: cerca solo la prima parte per nomi troppo complessi
    first_part = stop_name.split("-")[0].split()[0]

    queries = [
        f"Fermata {stop_name}, Bologna, Italia",
        f"Via {stop_name}, Bologna, Italia",
        f"{stop_name}, Bologna, Italia",
        f"Via {first_part}, Bologna, Italia",  # Strategia disperata
    ]

    for query in queries:
        try:
            time.sleep(1)
            location = geolocator.geocode(query, timeout=10)
            if location:
                return location.latitude, location.longitude
        except GeocoderTimedOut:
            continue
    return None


def process_and_annotate_tram():
    print("Inizio Geolocalizzazione Automatica v2.0 (Smart Matching)...")

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        tram_data = json.load(f)

    # 1. Caricamento e Normalizzazione Bus
    df_bus = pd.read_csv(PROCESSED_DIR / "bologna_stations.csv")
    bus_map = {}
    for _, row in df_bus.iterrows():
        raw_name = str(row["stop_name"])
        norm_name = normalize_name(raw_name)
        # Teniamo sempre l'ultimo ID se ci sono omonimi
        bus_map[norm_name] = {
            "id": str(row["stop_id"]),
            "lat": row["stop_lat"],
            "lon": row["stop_lon"],
            "raw": raw_name,
        }

    tram_nodes_csv = []
    json_id_to_final_id = {}

    print(" -> Ricerca Coordinate in corso...")

    for stop in tram_data:
        original_name = stop["name"].strip()
        name_upper = original_name.upper()
        norm_name = normalize_name(original_name)

        # Applica l'Override se esiste
        if name_upper in MANUAL_OVERRIDES:
            print("manual override")
            norm_name = normalize_name(MANUAL_OVERRIDES[name_upper])

        json_id = stop["id"]
        lat, lon = None, None

        # --- STRATEGIA 1: Match Esatto (su stringa normalizzata) ---
        if norm_name in bus_map:
            lat, lon = bus_map[norm_name]["lat"], bus_map[norm_name]["lon"]
            print(f"Match diretto {original_name}")

        else:
            print(f"    🌍 Cerco su Mappa OSM: '{original_name}'...")
            coords = get_coordinates_from_map(original_name)
            if coords:
                lat, lon = coords
                print(f"      ✅ Trovato: {lat:.5f}, {lon:.5f}")
            else:
                # Fallback (Da correggere a mano)
                lat, lon = 44.4949, 11.3426
                print(f"    ❌ Fallito: '{original_name}'. Assegnato Piazza Maggiore.")

        json_id_to_final_id[json_id] = json_id

        tram_nodes_csv.append(
            {
                "stop_id": json_id,
                "stop_name": name_upper,
                "stop_lat": lat,
                "stop_lon": lon,
                "node_type": stop.get("node_type", "fermata"),
            }
        )

    df_tram_nodes = pd.DataFrame(tram_nodes_csv).drop_duplicates(subset=["stop_id"])
    edges_data = []
    rossa_stops = [s for s in tram_data if "Rossa" in s["line"]]
    verde_stops = [s for s in tram_data if "Verde" in s["line"]]

    def build_edges(stops_list, route_id):
        for i in range(len(stops_list) - 1):
            edges_data.append(
                {
                    "stop_id": json_id_to_final_id[stops_list[i]["id"]],
                    "next_stop_id": json_id_to_final_id[stops_list[i + 1]["id"]],
                    "route_id": route_id,
                }
            )

    build_edges(rossa_stops, "101")
    build_edges(verde_stops, "102")
    df_tram_edges = pd.DataFrame(edges_data).drop_duplicates()

    df_tram_nodes.to_csv(PROCESSED_DIR / "bologna_tram_stations.csv", index=False)
    df_tram_edges.to_csv(PROCESSED_DIR / "bologna_tram_connections.csv", index=False)

    print(f"\n✅ Completato! Controlla {OUTPUT_JSON} e lancia src/visualize_map.py")


if __name__ == "__main__":
    process_and_annotate_tram()
