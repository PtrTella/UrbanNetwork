import requests
import os
import pandas as pd

# 1. Setup delle directory
RAW_DIR = "dataset/bologna/raw"
PROCESSED_DIR = "dataset/bologna/processed"
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# 2. Mappatura File Locali -> Dataset ID (Open Data Bologna)
DATASETS = {
    "bologna_spire_traffic.csv": "rilevazione-flusso-veicoli-tramite-spire-anno-2026",
    "bologna_accidents.csv": "incidenti_new",
    "bologna_bike_counters.csv": "colonnine-conta-bici",
    "bologna_demographics.csv": "popolazione-residente-per-eta-sesso-cittadinanza-quartiere-zona-area-statistica-",
    "bologna_bus_stops.csv": "tper-fermate-autobus",
}


def download_ods_csv(dataset_id, output_path):
    print(f"Scaricando {dataset_id}...")
    url = f"https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/{dataset_id}/exports/csv"
    params = {
        "lang": "it",
        "timezone": "Europe/Rome",
        "use_labels": "false",
        "delimiter": ";",
    }

    try:
        response = requests.get(url, params=params, stream=True)
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Salvato: {output_path}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Errore durante il download di {dataset_id}: {e}")


def download_osm_tram_stops(output_path):
    """Estrae le fermate del tram da OSM e le salva in un CSV raw per eventuale pulizia manuale."""
    print("🌍 Scaricando fermate Tram da OpenStreetMap (Overpass API)...")
    overpass_url = "https://overpass-api.de/api/interpreter"
    headers = {"User-Agent": "UrbanNetworkAnalysis_Bologna_Thesis/1.0"}

    overpass_query = """
    [out:json][timeout:30];
    area["name"="Bologna"]["admin_level"="8"]->.searchArea;
    (
      node["railway"="tram_stop"](area.searchArea);
      node["railway"="construction"]["construction"="tram_stop"](area.searchArea);
      node["railway"="proposed"]["proposed"="tram_stop"](area.searchArea);
      node["public_transport"="stop_position"]["tram"="yes"](area.searchArea);
      node["public_transport"="platform"]["tram"="yes"](area.searchArea);
    );
    out body;
    """

    try:
        response = requests.post(
            overpass_url, data=overpass_query.encode("utf-8"), headers=headers
        )
        response.raise_for_status()
        data = response.json()

        rows = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name", "")
            if name:  # Salviamo solo i nodi che hanno un nome
                rows.append(
                    {
                        "osm_id": el["id"],
                        "stop_name": name,
                        "lat": el["lat"],
                        "lon": el["lon"],
                    }
                )

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)
        print(f"✅ Salvato: {output_path} ({len(df)} fermate OSM)")
        print(
            "   -> Puoi modificare a mano i 'stop_name' in questo CSV per allinearli al tuo JSON."
        )
    except Exception as e:
        print(f"❌ Errore API Overpass: {e}")


if __name__ == "__main__":
    print("Inizio acquisizione dati grezzi per la topologia L-Space...")

    # 1. Download Open Data Comune
    for filename, dataset_id in DATASETS.items():
        file_path = os.path.join(RAW_DIR, filename)
        if not os.path.exists(file_path):
            download_ods_csv(dataset_id, file_path)
        else:
            print(f"⏭️ {filename} già presente in locale, salto il download.")

    # 2. Download OpenStreetMap Tram
    osm_file_path = os.path.join(RAW_DIR, "osm_tram_stops.csv")
    if not os.path.exists(osm_file_path):
        download_osm_tram_stops(osm_file_path)
    else:
        print("⏭️ osm_tram_stops.csv già presente in locale, salto il download.")

    print("\n--- Fase 1 (Data Fetching) Completata! ---")
