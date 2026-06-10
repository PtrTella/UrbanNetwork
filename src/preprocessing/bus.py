import pandas as pd
import geopandas as gpd
from pathlib import Path

# Configurazione Percorsi
BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "dataset" / "bologna" / "raw"
GTFS_DIR = RAW_DIR / "gommagtfsbo"
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# LA WHITE-LIST: Solo le vere linee urbane di Bologna
# =========================================================
BOLOGNA_URBAN_LINES = {
    # Linee Storiche Radiali e Tangenziali
    "11",
    "13",
    "14",
    "15",
    "16",
    "18",
    "19",
    "20",
    "21",
    "25",
    "27",
    "28",
    "29",
    "30",
    "32",
    "33",
    "35",
    "36",
    "37",
    "38",
    "39",
    # Linee periferiche urbane/suburbane primarie
    "51",
    "52",
    "54",
    "55",
    "56",
    "58",
    "59",
    "60",
    # Navette Centro Storico e Speciali
    "A",
    "C",
    "D",
    "T1",
}


def clean_id(val):
    if pd.isna(val):
        return None
    try:
        return str(int(float(val)))
    except ValueError:
        return str(val).strip()


def process_bus_network():
    print("Inizio Preprocessing Rete Bus (Hard Filter Linee Bologna)...")

    if (
        not (GTFS_DIR / "stops.txt").exists()
        or not (GTFS_DIR / "stop_times.txt").exists()
    ):
        raise FileNotFoundError(
            f"Estrai gommagtfsbo.zip nella cartella {GTFS_DIR} prima di procedere!"
        )

    # =========================================================
    # 1. FILTRO HARD SULLE LINEE (routes.txt)
    # =========================================================
    print(" -> Analisi Linee (Filtraggio tramite White-List)...")
    df_routes = pd.read_csv(GTFS_DIR / "routes.txt")

    # Assicuriamoci che i nomi siano stringhe pulite e maiuscole per il match
    df_routes["clean_short_name"] = (
        df_routes["route_short_name"].astype(str).str.strip().str.upper()
    )

    # Teniamo solo le rotte che matchano la nostra lista
    df_routes_bologna = df_routes[
        df_routes["clean_short_name"].isin(BOLOGNA_URBAN_LINES)
    ]
    urban_route_ids = df_routes_bologna["route_id"].unique()

    # =========================================================
    # 2. ESTRAZIONE ARCHI (Solo tracciati della White-List)
    # =========================================================
    print(" -> Estrazione Archi (Costruzione topologia pura)...")
    stop_times = pd.read_csv(GTFS_DIR / "stop_times.txt")
    trips = pd.read_csv(GTFS_DIR / "trips.txt")

    trips_urban = trips[trips["route_id"].isin(urban_route_ids)]

    st_trips = stop_times.merge(trips_urban[["trip_id", "route_id"]], on="trip_id")
    st_trips = st_trips.sort_values(["trip_id", "stop_sequence"])

    st_trips["next_stop_id"] = st_trips.groupby("trip_id")["stop_id"].shift(-1)
    edges_raw = st_trips.dropna(subset=["next_stop_id"])

    df_edges = pd.DataFrame()
    df_edges["stop_id"] = edges_raw["stop_id"].apply(clean_id)
    df_edges["next_stop_id"] = edges_raw["next_stop_id"].apply(clean_id)
    df_edges["route_id"] = edges_raw["route_id"].astype(str)

    df_edges = df_edges.drop_duplicates(subset=["stop_id", "next_stop_id", "route_id"])

    valid_stops = set(df_edges["stop_id"]).union(set(df_edges["next_stop_id"]))

    # =========================================================
    # 3. LETTURA NODI (Solo fermate toccate dalle linee filtrate)
    # =========================================================
    print(" -> Elaborazione Nodi (Rimozione orfani extraurbani)...")
    df_stops_raw = pd.read_csv(GTFS_DIR / "stops.txt")
    df_stops_raw["stop_id_clean"] = df_stops_raw["stop_id"].apply(clean_id)

    df_stops = df_stops_raw[df_stops_raw["stop_id_clean"].isin(valid_stops)].copy()

    df_stops["stop_id"] = df_stops["stop_id_clean"]
    df_stops["stop_name"] = df_stops["stop_name"].str.upper()
    df_stops["stop_lat"] = df_stops["stop_lat"].astype(float)
    df_stops["stop_lon"] = df_stops["stop_lon"].astype(float)
    df_stops = df_stops.drop_duplicates(subset=["stop_id"])

    # =========================================================
    # 4. INTEGRAZIONE TRAFFICO E INCIDENTI
    # =========================================================
    print(" -> Mappatura Spire di Traffico e Incidenti...")

    # [Traffico]
    try:
        df_spire = pd.read_csv(RAW_DIR / "bologna_spire_traffic.csv", sep=";")
        df_spire = df_spire.dropna(subset=["longitudine", "latitudine"])
        df_spire["longitudine"] = (
            df_spire["longitudine"].astype(str).str.replace(",", ".").astype(float)
        )
        df_spire["latitudine"] = (
            df_spire["latitudine"].astype(str).str.replace(",", ".").astype(float)
        )

        colonne_orarie = df_spire.filter(regex=r"\d{2}_00_\d{2}_00").columns
        df_spire["flusso_totale_giorno"] = (
            df_spire[colonne_orarie]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0)
            .sum(axis=1)
        )
        df_spire_agg = (
            df_spire.groupby(["longitudine", "latitudine"])["flusso_totale_giorno"]
            .mean()
            .reset_index()
        )

        gdf_stops = gpd.GeoDataFrame(
            df_stops,
            geometry=gpd.points_from_xy(df_stops.stop_lon, df_stops.stop_lat),
            crs="EPSG:4326",
        )
        gdf_spire = gpd.GeoDataFrame(
            df_spire_agg,
            geometry=gpd.points_from_xy(
                df_spire_agg.longitudine, df_spire_agg.latitudine
            ),
            crs="EPSG:4326",
        )

        joined_spire = gpd.sjoin_nearest(
            gdf_stops.to_crs("EPSG:32632"),
            gdf_spire.to_crs("EPSG:32632")[["geometry", "flusso_totale_giorno"]],
            how="left",
        )
        joined_spire = joined_spire.drop_duplicates(subset=["stop_id"])

        df_stops = df_stops.merge(
            joined_spire[["stop_id", "flusso_totale_giorno"]], on="stop_id", how="left"
        )
        df_stops.rename(
            columns={"flusso_totale_giorno": "nearest_traffic_flow"}, inplace=True
        )
        df_stops["nearest_traffic_flow"] = (
            df_stops["nearest_traffic_flow"].fillna(0).round(2)
        )
    except Exception as e:
        df_stops["nearest_traffic_flow"] = 0

    # [Incidenti]
    try:
        df_acc = pd.read_csv(RAW_DIR / "bologna_accidents.csv", sep=";")
        df_acc = df_acc.dropna(subset=["geo_point_2d"])
        acc_coords = df_acc["geo_point_2d"].str.split(",", expand=True)
        df_acc["lat"], df_acc["lon"] = (
            acc_coords[0].astype(float),
            acc_coords[1].astype(float),
        )

        gdf_acc = gpd.GeoDataFrame(
            df_acc, geometry=gpd.points_from_xy(df_acc.lon, df_acc.lat), crs="EPSG:4326"
        ).to_crs("EPSG:32632")
        gdf_stops_metric = gdf_stops.to_crs("EPSG:32632")
        gdf_stops_metric["geometry"] = gdf_stops_metric.geometry.buffer(300)

        joined_acc = gpd.sjoin(
            gdf_acc, gdf_stops_metric, how="inner", predicate="intersects"
        )
        acc_counts = (
            joined_acc.groupby("stop_id").size().reset_index(name="accidents_300m")
        )

        df_stops = df_stops.merge(acc_counts, on="stop_id", how="left")
        df_stops["accidents_300m"] = df_stops["accidents_300m"].fillna(0).astype(int)
    except Exception as e:
        df_stops["accidents_300m"] = 0

    # =========================================================
    # 5. ESPORTAZIONE
    # =========================================================
    col_finali = [
        "stop_id",
        "stop_name",
        "stop_lat",
        "stop_lon",
        "nearest_traffic_flow",
        "accidents_300m",
    ]
    df_stops[col_finali].to_csv(PROCESSED_DIR / "bologna_stations.csv", index=False)
    df_edges.to_csv(PROCESSED_DIR / "bologna_connections.csv", index=False)

    print(f"✅ Pipeline Completata con Successo (White-List)!")
    print(f"   - Nodi (Fermate Bologna Urbana): {len(df_stops)}")
    print(f"   - Archi (Connessioni Topologiche): {len(df_edges)}")


if __name__ == "__main__":
    process_bus_network()
