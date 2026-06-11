import pandas as pd
import numpy as np
from src.config import TransitConfig
from src.graph import haversine


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

        # --- INIEZIONE PENDOLARI (Dati Ufficiali RFI / PUMS) ---
        if node_name == "STAZIONE CENTRALE" or node_name == "MEDAGLIE D'ORO":
            peso_pop += TransitConfig.STAZIONE_CENTRALE_PENDOLARI
        if node_name == "AUTOSTAZIONE":
            peso_pop += TransitConfig.AUTOSTAZIONE_PENDOLARI
        # -------------------------------------------------------

        G_full.nodes[n]["population_served"] = peso_pop

    # Estrazione Nodi (Raggruppati per nome per evitare cloni visivi delle paline)
    unique_hubs = {}
    for n, data in G_full.nodes(data=True):
        name = data.get("name", "SCONOSCIUTO").strip()
        pop = data.get("population_served", 0)
        unique_hubs[name] = max(unique_hubs.get(name, 0), pop)

    nodes_pop = sorted(unique_hubs.items(), key=lambda x: x[1], reverse=True)

    print("📊 Associazione Demografica Completata:")
    print(f"   - Match esatti per Nome: {matched_by_name}")
    print(f"   - Match per Snapping Spaziale: {matched_by_space}")
    print(
        f"   - Fermate senza dati (extraurbane/non trovate): {len(G_full) - (matched_by_name + matched_by_space)}"
    )

    print("\nTop 5 Hub per Pressione Demografica (Residenti + Pendolari):")
    for name, pop in nodes_pop[:5]:
        print(f"  - {name:<35} {int(pop)} abitanti")
