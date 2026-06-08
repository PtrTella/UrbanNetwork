import requests
import os

# 1. Setup delle directory (separazione raw/processed)
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

    # Parametri per ottenere un CSV pulito, senza label umane ma coi nomi colonna raw
    params = {
        "lang": "it",
        "timezone": "Europe/Rome",
        "use_labels": "false",
        "delimiter": ";",
    }

    try:
        response = requests.get(url, params=params, stream=True)
        response.raise_for_status()  # Lancia eccezione se l'API va in errore (es. 404 o 500)

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"✅ Salvato: {output_path}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Errore durante il download di {dataset_id}: {e}")


if __name__ == "__main__":
    print("Inizio acquisizione dati grezzi per la topologia L-Space...")

    for filename, dataset_id in DATASETS.items():
        file_path = os.path.join(RAW_DIR, filename)

        # Evita di riscaricare roba pesante se c'è già, utile in fase di dev
        if not os.path.exists(file_path):
            download_ods_csv(dataset_id, file_path)
        else:
            print(f"⏭️ {filename} già presente in locale, salto il download.")

    print("\n--- Fase 1 (Data Fetching) Completata! ---")
