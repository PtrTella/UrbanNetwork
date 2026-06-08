import os
import requests
import json
import sys

# Output directory relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "dataset", "bologna")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "raw_bologna_osm.json")

overpass_url = "https://overpass-api.de/api/interpreter"

# Bounding box for Bologna: (min_lat, min_lon, max_lat, max_lon)
# We query for both bus and trolleybus (since 32/33 are trolleybuses)
# and we match ref patterns like 11A, 11B, 11TA, and exact matches for others.
overpass_query = """
[out:json][timeout:120];
(
  relation["route"~"bus|trolleybus"]["ref"~"^(11[A-Z]?|11[A-Z]{2}|13|14|19|20|27|32|33|35|37)$"](44.43,11.23,44.56,11.46);
);
out body;
>;
out;
"""

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'application/json'
}

def main():
    print("Sending bulk GET request to Overpass API...")
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers, timeout=95)
    except Exception as e:
        print(f"Request failed: {e}")
        sys.exit(1)

    print(f"Status code: {response.status_code}")
    if response.status_code != 200:
        print("Error raw response:")
        print(response.text[:1000])
        sys.exit(1)

    try:
        data = response.json()
    except Exception as e:
        print("Failed to decode JSON. Raw response:")
        print(response.text[:1000])
        sys.exit(1)

    elements = data.get('elements', [])
    print(f"Total elements returned: {len(elements)}")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=1)
    print(f"Saved raw OSM data successfully to {OUTPUT_PATH}")

if __name__ == '__main__':
    main()
