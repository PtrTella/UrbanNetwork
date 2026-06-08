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
        print(f"Error: Raw OSM data not found at {RAW_JSON_PATH}. Run scripts/download_raw_osm.py or copy it.")
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
    
    # Clustering of stops (stops within 120m are grouped into a single station)
    clusters = []
    for stop in all_stops:
        found_cluster = False
        for c in clusters:
            dist = haversine(stop['lat'], stop['lon'], c['lat'], c['lon'])
            if dist < 120:
                c['stops'].append(stop)
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
    
    # Official coordinates for the 50 announced tram stops
    official_tram_stops = {
        # Linea Rossa Trunk (Borgo Panigale to Porta San Felice)
        "Emilio Lepido": (44.5173, 11.2750),
        "Villaggio Ina": (44.5158, 11.2820),
        "Ducati": (44.5147, 11.2885),
        "Manuzio": (44.5134, 11.2940),
        "Stazione Borgo Panigale-Teatri di Vita": (44.5118, 11.2995),
        "Triumvirato-Fabbri 1905": (44.5103, 11.3050),
        "Pontelungo-MAST": (44.5090, 11.3110),
        "Santa Viola-Opificio Golinelli": (44.5076, 11.3160),
        "Prati di Caprara": (44.5065, 11.3200),
        "Ospedale Maggiore": (44.5045, 11.3250),
        "Saffi": (44.5020, 11.3295),
        "Porta San Felice": (44.4988, 11.3325),
        # Paladozza Twin stops
        "Paladozza-San Felice": (44.4975, 11.3360),
        "Paladozza-Riva Reno": (44.4990, 11.3340),
        # Center
        "Canale di Reno-Lame": (44.4978, 11.3410),
        "Ugo Bassi": (44.4955, 11.3430),
        "Piazza Maggiore-San Pietro": (44.4950, 11.3470),
        "Indipendenza-8 Agosto": (44.5010, 11.3490),
        # Shared Rossa/Verde
        "Stazione Centrale": (44.5058, 11.3431),
        "Giacomo Matteotti-Stazione AV": (44.5072, 11.3461),
        "Piazza dell'Unità": (44.5135, 11.3461),
        # Fiera Branch
        "Zucca-Museo Ustica (Centro)": (44.5115, 11.3500),
        "Zucca-Museo Ustica (Fiera)": (44.5115, 11.3515),
        "Stalingrado": (44.5100, 11.3552),
        "Aldo Moro-Regione-Fiera": (44.5097, 11.3620),
        "Viale della Fiera-Liceo Copernico": (44.5130, 11.3650),
        "Michelino-Fiera nord": (44.5185, 11.3695),
        # Pilastro/CAAB Branch
        "Repubblica": (44.5105, 11.3710),
        "Piazza Spadolini": (44.5098, 11.3695),
        "San Donato": (44.5030, 11.3633),
        "San Donnino-Casalone": (44.5086, 11.3783),
        "Villaggio S. Giorgio": (44.5095, 11.3835),
        "Pirandello": (44.5116, 11.3899),
        "Pilastro - Futura": (44.5105, 11.3960),
        "Sighinolfi": (44.5111, 11.4010),
        "Facoltà di Agraria": (44.5130, 11.4079),
        # Linea Verde (from Mille to Corticella)
        "Mille": (44.5018, 11.3417),
        "Ca' dei Fiori": (44.5200, 11.3485),
        "Ippodromo": (44.5185, 11.3479),
        "Aldini Valeriani": (44.5215, 11.3481),
        "Caserme Rosse": (44.5258, 11.3497),
        "Croce Coperta": (44.5303, 11.3523),
        "Pinardi": (44.5330, 11.3535),
        "Don Fiammelli": (44.5360, 11.3545),
        "Lipparini-Ca' Bura": (44.5393, 11.3592),
        "Bentini-Villa Torchi": (44.5420, 11.3555),
        "Gorki - Teatro Centofiori": (44.5440, 11.3565),
        "Sant'Anna-Byron": (44.5464, 11.3605),
        "Shakespeare": (44.5490, 11.3585),
        "Stazione Corticella": (44.5519, 11.3545)
    }
    
    # Other key network landmarks/gates to preserve
    other_key_points = {
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
        "Meloncello": (44.4899, 11.3121),
        "Porta Galliera": (44.5043, 11.3435),
        "XX Settembre": (44.5033, 11.3418),
        "Piazza dei Martiri": (44.5020, 11.3391)
    }

    # Combined dictionary of all points to map
    all_points = {}
    for name, coords in campuses.items():
        all_points[name] = (coords, 'Campus')
    for name, coords in official_tram_stops.items():
        all_points[name] = (coords, 'Station')
    for name, coords in other_key_points.items():
        if name not in all_points:
            all_points[name] = (coords, 'Station')

    cluster_types = {c['id']: 'Station' for c in clusters}
    cluster_unibo_attr = {c['id']: 0.0 for c in clusters}
    key_station_mapping = {}
    
    # Calculate all pairwise distances
    pair_distances = []
    for name, (coords, ptype) in all_points.items():
        for c in clusters:
            dist = haversine(coords[0], coords[1], c['lat'], c['lon'])
            pair_distances.append((dist, name, c['id'], coords, ptype))
            
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
            if ptype == 'Campus':
                cluster_unibo_attr[new_id] = 1.0 if name != "Agraria Cadriano" else 0.8
            key_station_mapping[name] = new_id
            matched_names.add(name)

    # Generate sequential connections from bus routes
    connections = []
    active_lines = set()
    
    for rel in relations:
        line_ref = rel.get('tags', {}).get('ref', '')
        digits = ''.join(c for c in line_ref if c.isdigit())
        if not digits:
            continue
        line_id = int(digits)
        active_lines.add(line_id)
        members = rel.get('members', [])
        
        stop_seq = []
        for m in members:
            if m['type'] == 'node' and m['role'] in ['stop', 'platform', 'stop_entry_only', 'stop_exit_only']:
                node_id = m['ref']
                if node_id in osm_to_cluster:
                    stop_seq.append(osm_to_cluster[node_id])
                    
        clean_seq = []
        for sid in stop_seq:
            if not clean_seq or clean_seq[-1] != sid:
                clean_seq.append(sid)
                
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
                
    unique_conns = []
    seen_conns = set()
    for conn in connections:
        key = (conn['station1'], conn['station2'], conn['line'])
        if key not in seen_conns:
            seen_conns.add(key)
            unique_conns.append(conn)
            
    print(f"Generated {len(unique_conns)} unique bus connections.")
    
    # 4. Integrate planned/what-if Tram Lines
    def add_tram_connections(route, line_id):
        for idx in range(len(route) - 1):
            n1 = route[idx]
            n2 = route[idx + 1]
            s1 = key_station_mapping[n1]
            s2 = key_station_mapping[s2_name := n2] # handle local scope variable assignment safely
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

    # Linea Rossa (101):
    # Main Borgo Panigale trunk
    rossa_trunk = [
        "Emilio Lepido", "Villaggio Ina", "Ducati", "Manuzio", "Stazione Borgo Panigale-Teatri di Vita", 
        "Triumvirato-Fabbri 1905", "Pontelungo-MAST", "Santa Viola-Opificio Golinelli", "Prati di Caprara", 
        "Ospedale Maggiore", "Saffi", "Porta San Felice"
    ]
    add_tram_connections(rossa_trunk, 101)
    
    # Paladozza Twin Paths
    # Path A (San Felice)
    s_felice_path = ["Porta San Felice", "Paladozza-San Felice", "Canale di Reno-Lame", "Ugo Bassi"]
    add_tram_connections(s_felice_path, 101)
    # Path B (Riva Reno)
    r_reno_path = ["Porta San Felice", "Paladozza-Riva Reno", "Canale di Reno-Lame", "Ugo Bassi"]
    add_tram_connections(r_reno_path, 101)
    
    # Center section
    rossa_center = ["Ugo Bassi", "Piazza Maggiore-San Pietro", "Indipendenza-8 Agosto", "Stazione Centrale", "Giacomo Matteotti-Stazione AV", "Piazza dell'Unità"]
    add_tram_connections(rossa_center, 101)
    
    # Fiera Branch (including Zucca twin paths)
    fiera_path_a = ["Piazza dell'Unità", "Zucca-Museo Ustica (Centro)", "Stalingrado"]
    fiera_path_b = ["Piazza dell'Unità", "Zucca-Museo Ustica (Fiera)", "Stalingrado"]
    add_tram_connections(fiera_path_a, 101)
    add_tram_connections(fiera_path_b, 101)
    
    fiera_end = ["Stalingrado", "Aldo Moro-Regione-Fiera", "Viale della Fiera-Liceo Copernico", "Michelino-Fiera nord"]
    add_tram_connections(fiera_end, 101)
    
    # Pilastro/CAAB Branch
    pilastro_branch = [
        "Piazza dell'Unità", "Repubblica", "Piazza Spadolini", "San Donato", "San Donnino-Casalone", 
        "Villaggio S. Giorgio", "Pirandello", "Pilastro - Futura", "Sighinolfi", "Facoltà di Agraria"
    ]
    add_tram_connections(pilastro_branch, 101)
    
    # Linea Verde (102):
    verde_route = [
        "Mille", "Stazione Centrale", "Giacomo Matteotti-Stazione AV", "Piazza dell'Unità", 
        "Ippodromo", "Ca' dei Fiori", "Aldini Valeriani", "Caserme Rosse", "Croce Coperta", 
        "Pinardi", "Don Fiammelli", "Lipparini-Ca' Bura", "Bentini-Villa Torchi", 
        "Gorki - Teatro Centofiori", "Sant'Anna-Byron", "Shakespeare", "Stazione Corticella"
    ]
    add_tram_connections(verde_route, 102)
    
    # Alternative Campus Tram (103):
    campus_route = ["Lazzaretto", "Navile", "Piazza Spadolini", "Porta San Donato"]
    add_tram_connections(campus_route, 103)
    
    # Alternative Circular Tram (Viali) (104):
    circular_route = [
        "Porta Galliera", "XX Settembre", "Piazza dei Martiri", "Porta San Felice", 
        "Porta Saragozza", "Porta Santo Stefano", "Porta Mazzini", "Porta San Donato", "Porta Galliera"
    ]
    add_tram_connections(circular_route, 104)

    print("Integrated Tram Linea Rossa (101), Linea Verde (102), Alternative Campus (103), and Alternative Circular (104).")

    # Connect Agraria to FICO and Pilastro via Line 35 walking/bus transfers
    agraria_id = key_station_mapping["Facoltà di Agraria"]
    pilastro_id = key_station_mapping["Pilastro - Futura"]
    
    unique_conns.append({
        'station1': min(agraria_id, pilastro_id),
        'station2': max(agraria_id, pilastro_id),
        'line': 35,
        'time': 3
    })
    print("Facoltà di Agraria connected to Pilastro - Futura via Line 35.")

    # 5. Load and Merge Open Data
    
    # Load Spire Traffic
    spire_path = f"{OUTPUT_DIR}/bologna_spire_traffic.csv"
    if os.path.exists(spire_path):
        df_spire = pd.read_csv(spire_path)
        print(f"Loaded {len(df_spire)} spire traffic sensors.")
    else:
        print("Warning: bologna_spire_traffic.csv not found.")
        df_spire = pd.DataFrame()
        
    # Load Accidents
    accidents_path = f"{OUTPUT_DIR}/bologna_accidents.csv"
    if os.path.exists(accidents_path):
        df_acc = pd.read_csv(accidents_path)
        acc_dict = df_acc.set_index("normalized_neighborhood").to_dict(orient="index")
        print(f"Loaded {len(df_acc)} accident neighborhood records.")
    else:
        print("Warning: bologna_accidents.csv not found.")
        acc_dict = {}
        
    # Load Bike Counters
    bike_path = f"{OUTPUT_DIR}/bologna_bike_counters.csv"
    if os.path.exists(bike_path):
        df_bike = pd.read_csv(bike_path)
        print(f"Loaded {len(df_bike)} bike counters.")
    else:
        print("Warning: bologna_bike_counters.csv not found.")
        df_bike = pd.DataFrame()

    # Pre-calculate zone average daily flows for spire fallback
    # Match spire coordinates to neighborhoods
    spire_flows_by_zone = {}
    if not df_spire.empty:
        for idx, row in df_spire.iterrows():
            lat, lon = row["latitudine"], row["longitudine"]
            zone = "Centro"
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
            spire_flows_by_zone.setdefault(zone, []).append(row["avg_daily_flow"])
            
    zone_avg_flow = {z: np.mean(flows) for z, flows in spire_flows_by_zone.items()}
    overall_avg_flow = df_spire["avg_daily_flow"].mean() if not df_spire.empty else 5000.0

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
                
        # Find nearest bike counter within 300 meters
        bike_flow = 0.0
        if not df_bike.empty:
            for idx, row in df_bike.iterrows():
                b_lat, b_lon = row["latitude"], row["longitude"]
                if pd.notna(b_lat) and pd.notna(b_lon):
                    dist = haversine(lat, lon, b_lat, b_lon)
                    if dist < 300:
                        bike_flow = max(bike_flow, row["avg_hourly_flow"])
                        
        stations_data.append({
            'id': c['id'],
            'name': c['name'],
            'latitude': round(lat, 5),
            'longitude': round(lon, 5),
            'zone': zone,
            'type': cluster_types.get(c['id'], 'Station'),
            'bike_flow_hourly': round(bike_flow, 2)
        })
        
    df_stations_out = pd.DataFrame(stations_data)
    df_stations_out.to_csv(f"{OUTPUT_DIR}/bologna_stations.csv", index=False)
    print(f"Saved {len(df_stations_out)} stations to bologna_stations.csv")
    
    # 6b. Connections CSV
    df_conns_out = pd.DataFrame(unique_conns)
    df_conns_out.to_csv(f"{OUTPUT_DIR}/bologna_connections.csv", index=False)
    print(f"Saved {len(df_conns_out)} connections to bologna_connections.csv")
    
    # 6c. Demographics & Open Data CSV
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
            
        # Match nearest vehicle spire flow (within 500m)
        traffic_flow = None
        min_dist = float('inf')
        if not df_spire.empty:
            for idx, s_row in df_spire.iterrows():
                s_lat, s_lon = s_row["latitudine"], s_row["longitudine"]
                dist = haversine(c["lat"], c["lon"], s_lat, s_lon)
                if dist < min_dist:
                    min_dist = dist
                    traffic_flow = s_row["avg_daily_flow"]
                    
        # Apply neighborhood fallback if no spire is within 500m
        if min_dist > 500 or traffic_flow is None:
            traffic_flow = zone_avg_flow.get(zone, overall_avg_flow)
            
        # Match neighborhood accident statistics
        acc_info = acc_dict.get(zone, {"total_accidents": 0, "total_injured": 0, "total_deaths": 0})
        
        demo_data.append({
            'station_id': cid,
            'station_name': name,
            'neighborhood': zone,
            'population_density': density,
            'unibo_attraction': cluster_unibo_attr.get(cid, 0.0),
            'traffic_flow_daily': round(traffic_flow, 2),
            'zone_total_accidents': acc_info.get("total_accidents", 0),
            'zone_total_injured': acc_info.get("total_injured", 0),
            'zone_total_deaths': acc_info.get("total_deaths", 0)
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
        103: ("Tram Alternativo Campus", "F57C00"),
        104: ("Tram Alternativo Circolare Viali", "0288D1"),
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
