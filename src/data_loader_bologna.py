import os
import pandas as pd
import networkx as nx
import numpy as np

# Path to the local dataset folder relative to this file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIONS_PATH = os.path.join(BASE_DIR, "dataset", "bologna", "bologna_stations.csv")
CONNECTIONS_PATH = os.path.join(BASE_DIR, "dataset", "bologna", "bologna_connections.csv")
LINES_PATH = os.path.join(BASE_DIR, "dataset", "bologna", "bologna_lines.csv")
DEMOGRAPHICS_PATH = os.path.join(BASE_DIR, "dataset", "bologna", "bologna_demographics.csv")

def haversine(lat1, lon1, lat2, lon2):
    """
    Computes geographical distance between two lat/lon points in meters.
    """
    R = 6371000.0  # Earth radius in meters
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return R * c

def load_bologna_network(include_tram=False):
    """
    Loads Bologna stations, connections, and lines from local CSV files.
    Builds an L-Space undirected Graph.
    If include_tram is True, incorporates tram lines (101, 102).
    """
    df_stations = pd.read_csv(STATIONS_PATH)
    df_connections = pd.read_csv(CONNECTIONS_PATH)
    df_lines = pd.read_csv(LINES_PATH)
    df_demo = pd.read_csv(DEMOGRAPHICS_PATH)

    # Mappings
    id_to_name = dict(zip(df_stations['id'], df_stations['name']))
    id_to_lat = dict(zip(df_stations['id'], df_stations['latitude']))
    id_to_lon = dict(zip(df_stations['id'], df_stations['longitude']))

    # Build Graph
    G = nx.Graph()

    # Add nodes
    for idx, row in df_stations.iterrows():
        name = row['name']
        G.add_node(name, 
                   id=int(row['id']),
                   lat=row['latitude'], 
                   lon=row['longitude'], 
                   zone=row['zone'],
                   type=row['type'],
                   pos=(row['longitude'], row['latitude']))

    # Add edges
    for idx, row in df_connections.iterrows():
        line_id = int(row['line'])
        if not include_tram and line_id >= 100:
            continue  # Skip tram lines if not requested
            
        s1_id = int(row['station1'])
        s2_id = int(row['station2'])
        s1_name = id_to_name[s1_id]
        s2_name = id_to_name[s2_id]
        
        lat1, lon1 = id_to_lat[s1_id], id_to_lon[s1_id]
        lat2, lon2 = id_to_lat[s2_id], id_to_lon[s2_id]
        dist = haversine(lat1, lon1, lat2, lon2)
        
        if G.has_edge(s1_name, s2_name):
            if line_id not in G[s1_name][s2_name]['lines']:
                G[s1_name][s2_name]['lines'].append(line_id)
        else:
            G.add_edge(s1_name, s2_name, weight=dist, time=row['time'], lines=[line_id])

    return G, df_stations, df_connections, df_lines, df_demo
