import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import zipfile
import os

# --- PATH CONFIGURATION ---
RAW_DIR = "dataset/bologna/raw"
PROCESSED_DIR = "dataset/bologna/processed"
GTFS_ZIP = os.path.join(RAW_DIR, "gommagtfsbo.zip")

# Sistemi di coordinate: 4326 (Lat/Lon standard) -> 32632 (Metrico per l'Italia, zona 32N)
CRS_WGS84 = "EPSG:4326"
CRS_METRIC = "EPSG:32632"


def load_gtfs_network():
    print("1. Estrazione Rete Bus dai file GTFS estratti...")

    # Puntiamo direttamente alla cartella estratta
    GTFS_DIR = os.path.join(RAW_DIR, "gommagtfsbo")
    stops_path = os.path.join(GTFS_DIR, "stops.txt")
    stop_times_path = os.path.join(GTFS_DIR, "stop_times.txt")
    trips_path = os.path.join(GTFS_DIR, "trips.txt")

    if not os.path.exists(stops_path):
        raise FileNotFoundError(
            f"Non trovo i file GTFS in {GTFS_DIR}. Sicuro di averli estratti lì?"
        )

    # Carica i nodi (fermate)
    stops = pd.read_csv(stops_path)
    stops = stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].drop_duplicates(
        subset=["stop_id"]
    )

    # Carica gli archi (stop_times) e i viaggi
    stop_times = pd.read_csv(
        stop_times_path, usecols=["trip_id", "stop_id", "stop_sequence"]
    )
    trips = pd.read_csv(trips_path, usecols=["route_id", "trip_id"])

    # Creazione degli archi logici (Edges)
    seq = pd.merge(stop_times, trips, on="trip_id")
    seq = seq.sort_values(by=["trip_id", "stop_sequence"])

    # Colonna "next_stop_id" shiftando le righe per lo stesso viaggio
    seq["next_stop_id"] = seq.groupby("trip_id")["stop_id"].shift(-1)
    edges = seq.dropna(subset=["next_stop_id"]).copy()

    # Raggruppiamo e pesiamo per frequenza
    edges_agg = (
        edges.groupby(["stop_id", "next_stop_id", "route_id"])
        .size()
        .reset_index(name="frequency")
    )

    return stops, edges_agg


def enrich_nodes_with_opendata(stops_df):
    print("2. Arricchimento Spaziale dei Nodi (Geopandas)...")

    # Convertiamo le fermate in Geometries
    gdf_stops = gpd.GeoDataFrame(
        stops_df,
        geometry=gpd.points_from_xy(stops_df.stop_lon, stops_df.stop_lat),
        crs=CRS_WGS84,
    ).to_crs(CRS_METRIC)  # Proiettiamo in metri

    # --- INCIDENTI (Raggio 300m) ---
    print("   -> Calcolo Risk Score (Incidenti entro 300m)...")
    df_acc = pd.read_csv(os.path.join(RAW_DIR, "bologna_accidents.csv"), sep=";")

    # NOVITÀ: Dividiamo "geo_point_2d" (che è "lat, lon") in due colonne separate
    # Eliminiamo le righe dove geo_point_2d è nullo per evitare errori
    df_acc = df_acc.dropna(subset=["geo_point_2d"])
    df_acc[["lat", "lon"]] = (
        df_acc["geo_point_2d"].str.split(",", expand=True).astype(float)
    )

    gdf_acc = gpd.GeoDataFrame(
        df_acc, geometry=gpd.points_from_xy(df_acc["lon"], df_acc["lat"]), crs=CRS_WGS84
    ).to_crs(CRS_METRIC)

    # Creiamo un buffer di 300 metri attorno ad ogni fermata
    gdf_stops_buffer = gdf_stops.copy()
    gdf_stops_buffer.geometry = gdf_stops_buffer.geometry.buffer(300)

    # Spatial Join: contiamo quanti incidenti cadono nel buffer
    joined_acc = gpd.sjoin(gdf_acc, gdf_stops_buffer, how="inner", predicate="within")
    acc_counts = (
        joined_acc.groupby("index_right").size().reset_index(name="accidents_300m")
    )

    # Eseguiamo il merge dei risultati sui nodi
    gdf_stops = gdf_stops.merge(
        acc_counts, left_index=True, right_on="index_right", how="left"
    ).drop(columns=["index_right"])
    gdf_stops["accidents_300m"] = gdf_stops["accidents_300m"].fillna(0)

    # --- SPIRE TRAFFICO (Sensore più vicino) ---
    print("   -> Aggancio Traffico Spire (Sensore più vicino)...")
    df_spire = pd.read_csv(os.path.join(RAW_DIR, "bologna_spire_traffic.csv"), sep=";")

    col_lon, col_lat = "longitudine", "latitudine"

    if col_lon in df_spire.columns:
        # 1. Puliamo i dati rimuovendo i sensori senza coordinate
        df_spire = df_spire.dropna(subset=[col_lon, col_lat])

        # Le coordinate a volte hanno la virgola invece del punto nei dataset italiani
        df_spire[col_lon] = (
            df_spire[col_lon].astype(str).str.replace(",", ".").astype(float)
        )
        df_spire[col_lat] = (
            df_spire[col_lat].astype(str).str.replace(",", ".").astype(float)
        )

        # 2. Calcoliamo il 'flusso_totale' sommando tutte le 24 colonne orarie
        # Generiamo i nomi delle colonne orarie in modo programmatico per non scriverle tutte a mano
        colonne_orarie = [
            f"{str(i).zfill(2)}_00_{str(i + 1).zfill(2)}_00" for i in range(24)
        ]

        # Convertiamo i valori orari in numeri (se ci sono errori/vuoti mettiamo 0)
        df_spire[colonne_orarie] = (
            df_spire[colonne_orarie].apply(pd.to_numeric, errors="coerce").fillna(0)
        )
        df_spire["flusso_totale"] = df_spire[colonne_orarie].sum(axis=1)

        # 3. Mappatura su Geopandas e calcolo spaziale
        gdf_spire = gpd.GeoDataFrame(
            df_spire,
            geometry=gpd.points_from_xy(df_spire[col_lon], df_spire[col_lat]),
            crs=CRS_WGS84,
        ).to_crs(CRS_METRIC)

        # Spatial Join Nearest: trova la spira più vicina alla fermata
        gdf_stops = gpd.sjoin_nearest(
            gdf_stops, gdf_spire[["geometry", "flusso_totale"]], how="left"
        )

        # Rinominiamo e puliamo
        gdf_stops.rename(
            columns={"flusso_totale": "nearest_traffic_flow"}, inplace=True
        )
        gdf_stops = gdf_stops.drop_duplicates(subset=["stop_id"]).drop(
            columns=["index_right"], errors="ignore"
        )

    return gdf_stops.to_crs(
        CRS_WGS84
    )  # Riportiamo in Lat/Lon per comodità di esportazione


def inject_tram_scenarios(nodes, edges):
    print("3. Iniezione Scenari Tram What-if...")
    # TODO: QUI INSERIRAI LE TUE 50 FERMATE HARDCODATE.
    # Esempio di struttura:
    tram_stops = pd.DataFrame(
        [
            {
                "stop_id": "TRAM_R_01",
                "stop_name": "Terminale Fiera",
                "stop_lat": 44.512,
                "stop_lon": 11.365,
            },
            {
                "stop_id": "TRAM_R_02",
                "stop_name": "Aldo Moro",
                "stop_lat": 44.509,
                "stop_lon": 11.361,
            },
            # ... aggiungi le altre 48 ...
        ]
    )

    # Esempio archi tram (sequenza lineare)
    tram_edges = pd.DataFrame(
        [
            {
                "stop_id": "TRAM_R_01",
                "next_stop_id": "TRAM_R_02",
                "route_id": "Linea_Rossa_101",
                "frequency": 100,
            }
        ]
    )

    # Unione dei dataframe
    # return pd.concat([nodes, tram_stops]), pd.concat([edges, tram_edges])

    # Per ora restituiamo l'originale in attesa dei tuoi dati
    return nodes, edges


if __name__ == "__main__":
    print("Avvio Pipeline di Parsing Dati Bologna...")

    # 1. Estrai base da GTFS
    raw_stops, raw_edges = load_gtfs_network()

    # 2. Arricchisci con Open Data e Geopandas
    enriched_stops = enrich_nodes_with_opendata(raw_stops)

    # 3. Aggiungi i Tram
    final_nodes, final_edges = inject_tram_scenarios(enriched_stops, raw_edges)

    # 4. Salvataggio
    print("4. Salvataggio dei dataset processati...")
    # Rimuoviamo la colonna geometry prima di salvare in CSV
    final_nodes.drop(columns=["geometry"], errors="ignore").to_csv(
        os.path.join(PROCESSED_DIR, "bologna_stations.csv"), index=False
    )
    final_edges.to_csv(
        os.path.join(PROCESSED_DIR, "bologna_connections.csv"), index=False
    )

    print("✅ Build del Dataset Completato! I file sono in dataset/bologna/processed/")
