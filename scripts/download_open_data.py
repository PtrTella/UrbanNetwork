import os
import requests
import json
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "dataset", "bologna")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def download_spire_traffic():
    print("Fetching 2026 vehicle spire traffic data...")
    url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/rilevazione-flusso-veicoli-tramite-spire-anno-2026/records"
    
    # 24 hourly fields summed
    hourly_fields = [f"{i:02d}_00_{i+1:02d}_00" for i in range(24)]
    escaped_fields = " + ".join([f"`{f}`" for f in hourly_fields])
    select_clause = f"avg({escaped_fields}) as avg_daily_flow, count(*)"
    
    params = {
        "where": "id_uni is not null",
        "group_by": "id_uni, nome_via, latitudine, longitudine",
        "select": select_clause,
        "limit": 1000
    }
    
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Error fetching spire data: {r.status_code} - {r.text}")
        return
        
    records = r.json().get("results", [])
    df = pd.DataFrame(records)
    output_path = os.path.join(OUTPUT_DIR, "bologna_spire_traffic.csv")
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} spire sensors to {output_path}")

def download_accidents():
    print("Fetching accident data by neighborhood...")
    url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/incidenti_new/records"
    
    params = {
        "group_by": "nomequart",
        "select": "sum(n_incident) as total_accidents, sum(totale_fer) as total_injured, sum(totale_mor) as total_deaths",
        "limit": 20
    }
    
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Error fetching accident data: {r.status_code} - {r.text}")
        return
        
    records = r.json().get("results", [])
    df = pd.DataFrame(records)
    # Map neighborhoods to match our station naming standard
    # e.g., "San Donato - San Vitale" -> "San Donato", "Borgo Panigale - Reno" -> "Borgo Panigale"
    def normalize_neighborhood(name):
        if not name:
            return "Unknown"
        name_clean = name.strip()
        if "San Donato" in name_clean:
            return "San Donato"
        if "Borgo Panigale" in name_clean:
            return "Borgo Panigale"
        if "Porto" in name_clean or "Saragozza" in name_clean:
            return "Porto-Saragozza"
        return name_clean
        
    df["normalized_neighborhood"] = df["nomequart"].apply(normalize_neighborhood)
    output_path = os.path.join(OUTPUT_DIR, "bologna_accidents.csv")
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} neighborhood accident summaries to {output_path}")

def download_bike_counters():
    print("Fetching bike counters flow data and coordinates...")
    url = "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/colonnine-conta-bici/records"
    
    # 1. Fetch aggregates
    params = {
        "group_by": "colonnina",
        "select": "avg(totale) as avg_hourly_flow, count(*)",
        "limit": 100
    }
    
    r = requests.get(url, params=params)
    if r.status_code != 200:
        print(f"Error fetching bike counter aggregates: {r.status_code} - {r.text}")
        return
        
    aggregates = r.json().get("results", [])
    
    # 2. Fetch coordinates for each unique counter
    bike_records = []
    for agg in aggregates:
        c_name = agg["colonnina"]
        # Fetch one record to get the geopoint
        detail_params = {
            "where": f"colonnina=\"{c_name}\"",
            "limit": 1
        }
        detail_r = requests.get(url, params=detail_params)
        lat, lon = None, None
        if detail_r.status_code == 200:
            detail_res = detail_r.json().get("results", [])
            if detail_res:
                gp = detail_res[0].get("geo_point_2d", {})
                lat = gp.get("lat")
                lon = gp.get("lon")
        
        bike_records.append({
            "colonnina": c_name,
            "avg_hourly_flow": agg["avg_hourly_flow"],
            "reading_count": agg["count(*)"],
            "latitude": lat,
            "longitude": lon
        })
        
    df = pd.DataFrame(bike_records)
    output_path = os.path.join(OUTPUT_DIR, "bologna_bike_counters.csv")
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} bike counters to {output_path}")

def main():
    print("=== Start downloading Bologna Open Data ===")
    download_spire_traffic()
    download_accidents()
    download_bike_counters()
    print("=== Open Data download complete! ===")

if __name__ == "__main__":
    main()
