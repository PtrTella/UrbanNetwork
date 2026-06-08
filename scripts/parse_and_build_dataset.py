import os
import json
import math
import pandas as pd
import numpy as np

# Resolve directories relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_JSON_PATH = os.path.join(SCRIPT_DIR, "..", "dataset", "bologna", "raw_bologna_osm.json")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "..", "dataset", "bologna")

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def clean_stop_name(name):
    if not name:
        return "Unknown Stop"
    return name.strip()

def main():
    print("Loading raw OSM data...")
    if not os.path.exists(RAW_JSON_PATH):
        print(f"Error: Raw OSM data not found at {RAW_JSON_PATH}. Run scripts/download_raw_osm.py first.")
        return
        
    with open(RAW_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    elements = data.get('elements', [])
    print(f"Total elements: {len(elements)}")
    
    # Extract nodes
    nodes = {}
    for el in elements:
        if el['type'] == 'node':
            nodes[el['id']] = {
                'id': el['id'],
                'lat': el.get('lat'),
                'lon': el.get('lon'),
                'name': el.get('tags', {}).get('name', '')
            }
            
    # Extract relations (bus routes)
    relations = []
    for el in elements:
        if el['type'] == 'relation':
            relations.append(el)
            
    print(f"Found {len(nodes)} nodes and {len(relations)} relations.")
    
    # Collect all stops referenced in relations with their lat/lon
    all_stops = []
    for rel in relations:
        line_ref = rel.get('tags', {}).get('ref')
        members = rel.get('members', [])
        for idx, m in enumerate(members):
            if m['type'] == 'node' and m['role'] in ['stop', 'platform', 'stop_entry_only', 'stop_exit_only']:
                node_id = m['ref']
                if node_id in nodes:
                    node = nodes[node_id]
                    if node['lat'] and node['lon']:
                        all_stops.append({
                            'osm_id': node_id,
                            'lat': node['lat'],
                            'lon': node['lon'],
                            'name': node['name'] if node['name'] else f"Stop_{node_id}",
                            'line': line_ref
                        })
                        
    print(f"Total stop occurrences across all lines: {len(all_stops)}")
    
    # 2. Clustering of stops (stops within 120m are grouped into a single station)
    clusters = []
    for stop in all_stops:
        found_cluster = False
        for c in clusters:
            dist = haversine(stop['lat'], stop['lon'], c['lat'], c['lon'])
            if dist < 120:
                c['stops'].append(stop)
                # Update centroid coordinates
                c['lat'] = sum(s['lat'] for s in c['stops']) / len(c['stops'])
                c['lon'] = sum(s['lon'] for s in c['stops']) / len(c['stops'])
                found_cluster = True
                break
        if not found_cluster:
            clusters.append({
                'id': len(clusters) + 1,
                'name': clean_stop_name(stop['name']),
                'lat': stop['lat'],
                'lon': stop['lon'],
                'stops': [stop]
            })
            
    print(f"Clustered {len(all_stops)} stops into {len(clusters)} unique stations.")
    
    # Create mapping from OSM node ID to Cluster ID
    osm_to_cluster = {}
    for c in clusters:
        for s in c['stops']:
            osm_to_cluster[s['osm_id']] = c['id']
            
    # Key coordinates for university campuses
    campuses = {
        "Lazzaretto": (44.5248, 11.3115),
        "Navile": (44.5255, 11.3425),
        "Villa Spada": (44.4895, 11.3051),
        "Plesso Belmeloro": (44.4935, 11.3551),
        "LAUS Ingegneria": (44.5290, 11.3415),
        "Sant'Orsola Medicina": (44.4925, 11.3651),
        "Agraria Cadriano": (44.5385, 11.3985),
    }
    
    # Key coordinates for tram hubs and key network points
    key_points = {
        "Bologna Centrale": (44.5058, 11.3431),
        "Borgo Panigale": (44.5165, 11.2825),
        "Santa Viola": (44.5085, 11.3094),
        "Ospedale Maggiore": (44.5065, 11.3175),
        "Porta San Felice": (44.5015, 11.3255),
        "Via Marconi": (44.4995, 11.3377),
        "Via Ugo Bassi": (44.4947, 11.3411),
        "Rizzoli": (44.4945, 11.3433),
        "Due Torri": (44.4943, 11.3468),
        "Porta San Donato": (44.4975, 11.3571),
        "Sant'Egidio": (44.4990, 11.3621),
        "Piazza Spadolini": (44.5098, 11.3695),
        "FICO Eataly World": (44.5173, 11.4056),
        "Corticella Stazione": (44.5422, 11.3533),
        "Ippodromo": (44.5218, 11.3491),
        "Piazza dell'Unita": (44.5135, 11.3461),
        "Casalecchio Garibaldi": (44.4782, 11.2785),
        "San Lazzaro di Savena": (44.4705, 11.4085),
        "Porta Saragozza": (44.4912, 11.3275),
        "Stadio Dall'Ara": (44.4925, 11.3095),
        "Mazzini Stazione": (44.4851, 11.3781),
        "Porta Mazzini": (44.4885, 11.3615),
        "San Ruffillo Stazione": (44.4632, 11.3795),
        "Porta Santo Stefano": (44.4842, 11.3565),
        "Giardini Margherita": (44.4812, 11.3532),
        "Barca": (44.4985, 11.2915),
        "Massarenti": (44.4945, 11.3785),
        "Casteldebole": (44.5082, 11.2685),
        "Irnerio": (44.4965, 11.3535),
        "Pilastro": (44.5145, 11.3912),
        "Meloncello": (44.4899, 11.3121),
        "Porta Galliera": (44.5043, 11.3435),
        "XX Settembre": (44.5033, 11.3418),
        "Piazza dei Martiri": (44.5020, 11.3391)
    }

    cluster_types = {}
    cluster_unibo_attr = {}
    
    for c in clusters:
        cluster_types[c['id']] = 'Station'
        cluster_unibo_attr[c['id']] = 0.0
        
    key_station_mapping = {}
    
    # We map campuses and key points greedily to DISTINCT closest clusters
    all_points = {}
    for name, coords in campuses.items():
        all_points[name] = (coords, 'Campus')
    for name, coords in key_points.items():
        if name not in all_points:
            all_points[name] = (coords, 'Station')
            
    # Calculate all pairwise distances
    pair_distances = []
    for name, (coords, ptype) in all_points.items():
        for c in clusters:
            dist = haversine(coords[0], coords[1], c['lat'], c['lon'])
            pair_distances.append((dist, name, c['id'], coords, ptype))
            
    # Sort by distance ascending
    pair_distances.sort()
    
    assigned_clusters = set()
    matched_names = set()
    
    for dist, name, cid, coords, ptype in pair_distances:
        if name in matched_names or cid in assigned_clusters:
            continue
            
        # We allow matching up to 3 km to ensure all nodes find their nearest bus stop
        if dist < 3000:
            c = [x for x in clusters if x['id'] == cid][0]
            print(f"Greedy map: '{name}' -> closest stop '{c['name']}' (dist: {dist:.1f}m)")
            c['name'] = name
            cluster_types[cid] = ptype
            if ptype == 'Campus':
                cluster_unibo_attr[cid] = 1.0 if name != "Agraria Cadriano" else 0.8
            key_station_mapping[name] = cid
            assigned_clusters.add(cid)
            matched_names.add(name)
            
    # For any unmatched point, we create a new node
    for name, (coords, ptype) in all_points.items():
        if name not in matched_names:
            new_id = len(clusters) + 1
            print(f"No close station for '{name}' within 3km, creating a new node at {coords}")
            clusters.append({
                'id': new_id,
                'name': name,
                'lat': coords[0],
                'lon': coords[1],
                'stops': []
            })
            cluster_types[new_id] = ptype
            cluster_unibo_attr[new_id] = 1.0 if name != "Agraria Cadriano" else 0.8
            key_station_mapping[name] = new_id
            matched_names.add(name)

    # 3. Generate sequential connections from routes
    connections = []
    active_lines = set()
    
    for rel in relations:
        line_ref = rel.get('tags', {}).get('ref', '')
        # Extract only digits to find the parent line number (e.g. "11A" -> 11)
        digits = ''.join(c for c in line_ref if c.isdigit())
        if not digits:
            continue
        line_id = int(digits)
            
        active_lines.add(line_id)
        members = rel.get('members', [])
        
        # Extract stop sequence for this relation
        stop_seq = []
        for m in members:
            if m['type'] == 'node' and m['role'] in ['stop', 'platform', 'stop_entry_only', 'stop_exit_only']:
                node_id = m['ref']
                if node_id in osm_to_cluster:
                    stop_seq.append(osm_to_cluster[node_id])
                    
        # Remove consecutive duplicates
        clean_seq = []
        for sid in stop_seq:
            if not clean_seq or clean_seq[-1] != sid:
                clean_seq.append(sid)
                
        # Generate stop-to-stop connections
        for idx in range(len(clean_seq) - 1):
            s1 = clean_seq[idx]
            s2 = clean_seq[idx + 1]
            if s1 != s2:
                st1, st2 = min(s1, s2), max(s1, s2)
                c1 = [c for c in clusters if c['id'] == st1][0]
                c2 = [c for c in clusters if c['id'] == st2][0]
                dist = haversine(c1['lat'], c1['lon'], c2['lat'], c2['lon'])
                time_min = max(1, int(round(dist / 250.0)))  # ~1 min per 250m
                connections.append({
                    'station1': st1,
                    'station2': st2,
                    'line': line_id,
                    'time': time_min
                })
                
    # Remove connection duplicates (same stations, same line)
    unique_conns = []
    seen_conns = set()
    for conn in connections:
        key = (conn['station1'], conn['station2'], conn['line'])
        if key not in seen_conns:
            seen_conns.add(key)
            unique_conns.append(conn)
            
    print(f"Generated {len(unique_conns)} unique bus connections.")
    
    # 4. Integrate planned Tram Lines
    tram_rossa_route = [
        "Borgo Panigale", "Santa Viola", "Ospedale Maggiore", "Porta San Felice", 
        "Via Marconi", "Via Ugo Bassi", "Rizzoli", "Due Torri", "Porta San Donato", 
        "Sant'Egidio", "Piazza Spadolini", "FICO Eataly World"
    ]
    tram_verde_route = [
        "Corticella Stazione", "Ippodromo", "Piazza dell'Unita", "Bologna Centrale", 
        "Via Marconi", "Via Ugo Bassi"
    ]
    tram_blu_route = [
        "Casalecchio Garibaldi", "Porta Saragozza", "Via Marconi", "Via Ugo Bassi",
        "Rizzoli", "Due Torri", "Porta Mazzini", "Mazzini Stazione", "San Lazzaro di Savena"
    ]
    
    def add_tram_connections(route, line_id):
        for idx in range(len(route) - 1):
            n1 = route[idx]
            n2 = route[idx + 1]
            s1 = key_station_mapping[n1]
            s2 = key_station_mapping[n2]
            st1, st2 = min(s1, s2), max(s1, s2)
            c1 = [c for c in clusters if c['id'] == st1][0]
            c2 = [c for c in clusters if c['id'] == st2][0]
            dist = haversine(c1['lat'], c1['lon'], c2['lat'], c2['lon'])
            # Tram is faster than bus (~22 km/h)
            time_min = max(1, int(round(dist / 360.0)))
            unique_conns.append({
                'station1': st1,
                'station2': st2,
                'line': line_id,
                'time': time_min
            })
            
    add_tram_connections(tram_rossa_route, 101)
    add_tram_connections(tram_verde_route, 102)
    add_tram_connections(tram_blu_route, 103)
    print("Planned tram lines integrated successfully.")

    # 5. Connect isolated nodes like Agraria Cadriano!
    # Connect Agraria to FICO and Pilastro via Line 35 walking/bus transfers
    agraria_id = key_station_mapping["Agraria Cadriano"]
    fico_id = key_station_mapping["FICO Eataly World"]
    pilastro_id = key_station_mapping["Pilastro"]
    
    unique_conns.append({
        'station1': min(agraria_id, fico_id),
        'station2': max(agraria_id, fico_id),
        'line': 35,
        'time': 4
    })
    unique_conns.append({
        'station1': min(agraria_id, pilastro_id),
        'station2': max(agraria_id, pilastro_id),
        'line': 35,
        'time': 3
    })
    print("Agraria Cadriano connected to FICO and Pilastro via Line 35.")

    # 6. Save data
    
    # 6a. Stations CSV
    stations_data = []
    for c in clusters:
        zone = "Centro"
        lat, lon = c['lat'], c['lon']
        if lat > 44.515:
            zone = "Navile" if lon < 11.37 else "San Donato"
        elif lat < 44.485:
            zone = "Santo Stefano" if lon > 11.34 else "Porto-Saragozza"
            if lon > 11.37:
                zone = "Savena"
        else:
            if lon < 11.31:
                zone = "Borgo Panigale"
            elif lon > 11.36:
                zone = "San Donato"
            elif lon < 11.335:
                zone = "Porto-Saragozza"
                
        stations_data.append({
            'id': c['id'],
            'name': c['name'],
            'latitude': round(lat, 5),
            'longitude': round(lon, 5),
            'zone': zone,
            'type': cluster_types.get(c['id'], 'Station')
        })
        
    df_stations_out = pd.DataFrame(stations_data)
    df_stations_out.to_csv(f"{OUTPUT_DIR}/bologna_stations.csv", index=False)
    print(f"Saved {len(df_stations_out)} stations to bologna_stations.csv")
    
    # 6b. Connections CSV
    df_conns_out = pd.DataFrame(unique_conns)
    df_conns_out.to_csv(f"{OUTPUT_DIR}/bologna_connections.csv", index=False)
    print(f"Saved {len(df_conns_out)} connections to bologna_connections.csv")
    
    # 6c. Demographics CSV
    zone_densities = {
        "Centro": 8500,
        "San Donato": 5500,
        "Borgo Panigale": 4500,
        "Porto-Saragozza": 6000,
        "Navile": 5000,
        "Savena": 6500,
        "Santo Stefano": 6000
    }
    
    demo_data = []
    for c in clusters:
        cid = c['id']
        name = c['name']
        row = df_stations_out[df_stations_out['id'] == cid].iloc[0]
        zone = row['zone']
        density = zone_densities.get(zone, 5000)
        
        if "Centrale" in name or "Marconi" in name:
            density += 1000
        if "Pilastro" in name or "Massarenti" in name:
            density += 1500
        if "Agraria" in name:
            density = 1500
            
        demo_data.append({
            'station_id': cid,
            'station_name': name,
            'neighborhood': zone,
            'population_density': density,
            'unibo_attraction': cluster_unibo_attr.get(cid, 0.0)
        })
        
    df_demo_out = pd.DataFrame(demo_data)
    df_demo_out.to_csv(f"{OUTPUT_DIR}/bologna_demographics.csv", index=False)
    print(f"Saved {len(df_demo_out)} rows to bologna_demographics.csv")
    
    # 6d. Lines CSV
    lines_color_map = {
        11: ("Linea 11 (Bus)", "00897B"),
        13: ("Linea 13 (Bus)", "D32F2F"),
        14: ("Linea 14 (Bus)", "7CB342"),
        19: ("Linea 19 (Bus)", "FB8C00"),
        20: ("Linea 20 (Bus)", "F4511E"),
        27: ("Linea 27 (Bus)", "1976D2"),
        32: ("Circolare 32 (Bus)", "388E3C"),
        33: ("Circolare 33 (Bus)", "FBC02D"),
        35: ("Linea Navetta 35 (Bus)", "8E24AA"),
        37: ("Linea 37 (Bus)", "546E7A"),
        101: ("Tram Linea Rossa", "E53935"),
        102: ("Tram Linea Verde", "43A047"),
        103: ("Tram Linea Blu", "1E88E5"),
    }
    
    lines_data = []
    for lid, (lname, color) in lines_color_map.items():
        lines_data.append({
            'line': lid,
            'name': lname,
            'colour': color
        })
    df_lines_out = pd.DataFrame(lines_data)
    df_lines_out.to_csv(f"{OUTPUT_DIR}/bologna_lines.csv", index=False)
    print(f"Saved {len(df_lines_out)} lines to bologna_lines.csv")
    
    print("\nDataset generation completed successfully!")

if __name__ == '__main__':
    main()
