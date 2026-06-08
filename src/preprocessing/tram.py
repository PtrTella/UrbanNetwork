import pandas as pd
import json
import os

RAW_DIR = "dataset/bologna/raw"
PROCESSED_DIR = "dataset/bologna/processed"


def build_tram_datasets():
    print("Inizio elaborazione Rete Tranviaria (Dati Ufficiali)...")

    tram_json_path = os.path.join(RAW_DIR, "tram_official.json")
    bus_nodes_path = os.path.join(PROCESSED_DIR, "bologna_stations.csv")

    if not os.path.exists(tram_json_path) or not os.path.exists(bus_nodes_path):
        raise FileNotFoundError(
            "Mancano i file raw del tram o le stazioni bus processate."
        )

    # 1. Caricamento Dati
    with open(tram_json_path, "r", encoding="utf-8") as f:
        official_tram_stops = json.load(f)

    bus_df = pd.read_csv(bus_nodes_path)

    # Mappa dei nomi dei bus per ricerca coordinate (Tutto maiuscolo per facilitare il match)
    bus_map = {
        str(row["stop_name"]).upper(): (row["stop_lat"], row["stop_lon"])
        for _, row in bus_df.iterrows()
    }

    # 2. Risoluzione Spaziale dei Nodi (Geocoding basato su TPER)
    tram_nodes = []

    for stop in official_tram_stops:
        name_upper = stop["name"].upper()
        lat, lon = None, None

        # Match Esatto
        if name_upper in bus_map:
            lat, lon = bus_map[name_upper]
        else:
            # Match Parziale (es. "SAFFI" dentro "PORTA SAFFI")
            for bus_name, coords in bus_map.items():
                if name_upper in bus_name or bus_name in name_upper:
                    lat, lon = coords
                    break

        # Fallback se non esiste fermata bus vicina (Centro di Bologna)
        if lat is None:
            lat, lon = 44.4949, 11.3426

        tram_nodes.append(
            {
                "stop_id": stop["id"],
                "stop_name": stop["name"],
                "stop_lat": lat,
                "stop_lon": lon,
                "line_group": stop["line"],
                "nearest_traffic_flow": 0,  # Sede protetta
                "accidents_300m": 0,  # Sede protetta
            }
        )

    df_tram_nodes = pd.DataFrame(tram_nodes)

    # 3. Creazione degli Archi (Sequenze Linee)
    tram_edges = []

    def add_sequence(stops_list, route_id):
        for i in range(len(stops_list) - 1):
            tram_edges.append(
                {
                    "stop_id": stops_list[i]["stop_id"],
                    "next_stop_id": stops_list[i + 1]["stop_id"],
                    "route_id": route_id,
                    "type": "tram",
                    "frequency": 120,  # Alta frequenza
                }
            )

    # Dividiamo i nodi per linea per creare le sequenze logiche
    rossa = df_tram_nodes[df_tram_nodes["line_group"] == "Rossa"].to_dict("records")
    verde = df_tram_nodes[df_tram_nodes["line_group"] == "Verde"].to_dict("records")

    # Costruiamo gli scenari
    add_sequence(rossa, "101_LINEA_ROSSA")
    add_sequence(verde, "102_LINEA_VERDE")

    # Costruiamo lo scenario What-If Campus (Lazzaretto, Spadolini, San Donato)
    campus_names = ["Lazzaretto / Campus Navile", "Piazza Spadolini", "San Donato"]
    campus = df_tram_nodes[df_tram_nodes["stop_name"].isin(campus_names)].to_dict(
        "records"
    )
    if len(campus) > 1:
        add_sequence(campus, "103_TRAM_CAMPUS")

    # Costruiamo lo scenario What-If Viali (San Felice, San Donato, Saffi, Stazione)
    viali_names = ["Porta San Felice", "San Donato", "Saffi", "Stazione Centrale"]
    viali = df_tram_nodes[df_tram_nodes["stop_name"].isin(viali_names)].to_dict(
        "records"
    )
    if len(viali) > 1:
        add_sequence(viali, "104_TRAM_VIALI")

    df_tram_edges = pd.DataFrame(tram_edges)

    # 4. Salvataggio in processed
    nodes_out = os.path.join(PROCESSED_DIR, "bologna_tram_stations.csv")
    edges_out = os.path.join(PROCESSED_DIR, "bologna_tram_connections.csv")

    df_tram_nodes.to_csv(nodes_out, index=False)
    df_tram_edges.to_csv(edges_out, index=False)

    print(
        f"✅ Tram processato! Nodi: {len(df_tram_nodes)}, Archi: {len(df_tram_edges)}"
    )


if __name__ == "__main__":
    build_tram_datasets()
