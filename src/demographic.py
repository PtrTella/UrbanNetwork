# src/demographic.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from src.config import TransitConfig
from src.graph import haversine, update_dynamic_dwell_times


def calculate_demographics_weight(G_full, raw_dir_path):
    """
    Fase 5: Carica i dati demografici ISTAT e li spalma sulle fermate in base all'Area Statistica.
    Usa un matching ibrido:
    1. Match esatto per nome fermata normalizzato.
    2. Fallback geografico tramite snapping (entro DEMOGRAPHIC_SNAPPING_RADIUS) se il nome non corrisponde.
    """
    demo_path = raw_dir_path / "bologna_demographics.csv"
    stops_path = raw_dir_path / "bologna_bus_stops.csv"

    if not demo_path.exists() or not stops_path.exists():
        print("Dataset mancanti per l'analisi demografica.")
        return

    # 1. Caricamento e Normalizzazione Demografia
    df_demo = pd.read_csv(demo_path, sep=";")
    anno_max = df_demo["anno"].max()  # Prende in automatico il 2024
    df_demo = df_demo[df_demo["anno"] == anno_max]

    # Normalizzazione Stringhe (Tutto maiuscolo, senza spazi laterali)
    df_demo["area_statistica"] = (
        df_demo["area_statistica"].astype(str).str.upper().str.strip()
    )
    pop_area = df_demo.groupby("area_statistica")["residenti"].sum().reset_index()

    # 2. Caricamento e Normalizzazione Fermate
    df_stops = pd.read_csv(stops_path, sep=";")
    df_stops = df_stops.dropna(subset=["geopoint", "area_statistica"])

    # Estraiamo le coordinate dal geopoint
    df_stops[["lat", "lon"]] = (
        df_stops["geopoint"].str.split(",", expand=True).astype(float)
    )
    df_stops["stop_name"] = (
        df_stops["denominazione"].astype(str).str.upper().str.strip()
    )
    df_stops["area_statistica"] = (
        df_stops["area_statistica"].astype(str).str.upper().str.strip()
    )

    # Rimuovere i duplicati calcolando le coordinate medie per ogni fermata unica per l'area statistica
    df_unique_stops = df_stops.groupby(
        ["stop_name", "area_statistica"], as_index=False
    ).agg(lat=("lat", "mean"), lon=("lon", "mean"))

    # Calcoliamo quante fermate "fisiche" vere ci sono per ogni Area
    stops_per_area = df_unique_stops["area_statistica"].value_counts().reset_index()
    stops_per_area.columns = ["area_statistica", "num_stops_unici"]

    # Unione Popolazione -> Divisa per Numero Fermate Reali
    pop_area = pop_area.merge(stops_per_area, on="area_statistica", how="inner")
    pop_area["pop_per_stop"] = pop_area["residenti"] / pop_area["num_stops_unici"]

    # Mappiamo il peso demografico su ogni singola fermata unica
    df_stops_pop = df_unique_stops.merge(
        pop_area[["area_statistica", "pop_per_stop"]], on="area_statistica", how="inner"
    )

    # Raggruppiamo per sicurezza nel caso una fermata stia sul confine di due aree
    pop_dict = df_stops_pop.groupby("stop_name")["pop_per_stop"].mean().to_dict()

    # Creiamo un subset per la ricerca spaziale rapida (escludiamo zone contrassegnate fuori confine)
    df_spatial_lookup = df_stops_pop[
        df_stops_pop["area_statistica"] != "FUORI BOLOGNA"
    ].copy()

    # 3. Pesatura del Grafo L-Space
    matched_by_name = 0
    matched_by_space = 0

    for n, data in G_full.nodes(data=True):
        node_name = data.get("name", "").strip().upper()

        # Metodo A: Match esatto sul nome della fermata
        peso_pop = pop_dict.get(node_name, 0.0)
        if peso_pop > 0:
            matched_by_name += 1

        # Metodo B: Fallback Spaziale (snapping di prossimità geografica)
        elif "lat" in data and "lon" in data and len(df_spatial_lookup) > 0:
            n_lat, n_lon = data["lat"], data["lon"]
            dists = haversine(
                n_lat,
                n_lon,
                df_spatial_lookup["lat"].values,
                df_spatial_lookup["lon"].values,
            )
            if len(dists) > 0:
                min_idx = np.argmin(dists)
                if dists[min_idx] <= TransitConfig.DEMOGRAPHIC_SNAPPING_RADIUS:
                    peso_pop = df_spatial_lookup["pop_per_stop"].iloc[min_idx]
                    matched_by_space += 1



        G_full.nodes[n]["population_served"] = peso_pop

    # Estrazione Nodi (Raggruppati per nome per evitare cloni visivi delle paline)
    unique_hubs = {}
    for n, data in G_full.nodes(data=True):
        name = data.get("name", "SCONOSCIUTO").strip()
        pop = data.get("population_served", 0)
        unique_hubs[name] = max(unique_hubs.get(name, 0), pop)

    nodes_pop = sorted(unique_hubs.items(), key=lambda x: x[1], reverse=True)

    print(" Associazione Demografica Completata:")
    print(f"   - Match esatti per Nome: {matched_by_name}")
    print(f"   - Match per Snapping Spaziale: {matched_by_space}")
    print(
        f"   - Fermate senza dati (extraurbane/non trovate): {len(G_full) - (matched_by_name + matched_by_space)}"
    )

    print("\nTop 5 Hub per Pressione Demografica (Residenti):")
    for name, pop in nodes_pop[:5]:
        print(f"  - {name:<35} {int(pop)} abitanti")

    # Applica i dwell times dinamici agli archi del grafo
    update_dynamic_dwell_times(G_full)


if __name__ == "__main__":
    from src.graph import load_cached_graph
    from pathlib import Path

    BASE_DIR = Path(__file__).resolve().parent.parent
    RAW_DIR = BASE_DIR / "dataset" / "bologna" / "raw"
    OUTPUT_DIR = BASE_DIR / "data_output" / "bologna"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(" Running autonomous Demographic Pressure Analysis...")
    G_bus = load_cached_graph("G_bus")
    G_fused = load_cached_graph("G_fused")
    G_multi = load_cached_graph("G_multiplex")

    def process_and_save(G, filename, graph_name):
        # Ripuliamo/Calcoliamo per il grafo specifico
        # NOTA: il grafo caricato NON va risalvato nella cache pickle. La cache deve
        # contenere solo i pesi base BPR: la pipeline applica i dwell demografici a
        # runtime, e un grafo già "caricato" in cache subirebbe un doppio conteggio.
        calculate_demographics_weight(G, RAW_DIR)

        # Raccogliamo i risultati in un DataFrame da salvare
        data = []
        for n, attr in G.nodes(data=True):
            node_type = attr.get("type", "bus")
            pop = attr.get("population_served", 0.0)
            
            # Calcolo Vulnerabilità / Dwell Penalty
            cap_factor = TransitConfig.BUS_CAPACITY_FACTOR
            if node_type == "tram":
                cap_factor = TransitConfig.TRAM_CAPACITY_FACTOR
                
            dwell_penalty = (pop * TransitConfig.DWELL_TIME_PER_CAPITA) / cap_factor
            
            data.append({
                "Station_Name": attr.get("name", ""),
                "Latitude": attr.get("lat", 0.0),
                "Longitude": attr.get("lon", 0.0),
                "Type": node_type,
                "Population_Served": pop,
                "Dwell_Penalty": dwell_penalty
            })
        df_raw = pd.DataFrame(data)
        
        # Clustering Spaziale con DBSCAN per estrarre Macro-Zone urbane (eps=0.0035 gradi ~ 400m)
        from sklearn.cluster import DBSCAN
        coords = df_raw[["Latitude", "Longitude"]].values
        db = DBSCAN(eps=0.0035, min_samples=1).fit(coords)
        df_raw["Macro_Zone_ID"] = db.labels_
        
        # Raggruppiamo le paline fisiche in Macro-Zone, tenendo il nome della stazione con la pop massima come label
        def get_zone_name(group):
            return group.loc[group["Population_Served"].idxmax(), "Station_Name"]
            
        df_demo_res = df_raw.groupby("Macro_Zone_ID", as_index=False).agg({
            "Latitude": "mean",
            "Longitude": "mean",
            "Population_Served": "max",  # La pressione demografica del bacino (sovrapposta, prendiamo il max o la media)
            "Dwell_Penalty": "mean",     # La vulnerabilità media di questa zona
            "Type": "first"
        })
        
        # Aggiungiamo i nomi delle stazioni rappresentative per la zona
        zone_names = df_raw.groupby("Macro_Zone_ID").apply(get_zone_name).reset_index(name="Zone_Name")
        df_demo_res = df_demo_res.merge(zone_names, on="Macro_Zone_ID")
        
        df_demo_res = df_demo_res.sort_values(by="Population_Served", ascending=False)

        out_csv = OUTPUT_DIR / filename
        df_demo_res.to_csv(out_csv, index=False)
        print(f"  ✅ Demographic pressure results saved to: {out_csv}")

    print("\n--- Analisi Rete Solo Bus ---")
    process_and_save(G_bus, "demographic_bus_results.csv", "G_bus")
    print("\n--- Analisi Rete Tram (Fused) ---")
    process_and_save(G_fused, "demographic_tram_results.csv", "G_fused")
    print("\n--- Analisi Rete Multiplex ---")
    process_and_save(G_multi, "demographic_multi_results.csv", "G_multiplex")
