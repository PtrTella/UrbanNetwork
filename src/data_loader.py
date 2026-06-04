import pandas as pd
import networkx as nx
import numpy as np

# London Tube URLs
STATIONS_URL = "https://raw.githubusercontent.com/nicola/tubemaps/master/datasets/london.stations.csv"
CONNECTIONS_URL = "https://raw.githubusercontent.com/nicola/tubemaps/master/datasets/london.connections.csv"
LINES_URL = "https://raw.githubusercontent.com/nicola/tubemaps/master/datasets/london.lines.csv"

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

def load_london_network():
    """
    Downloads stations, lines and connections and builds an L-Space undirected Graph.
    """
    df_stations = pd.read_csv(STATIONS_URL)
    df_connections = pd.read_csv(CONNECTIONS_URL)
    df_lines = pd.read_csv(LINES_URL)

    # Mappings
    id_to_name = dict(zip(df_stations['id'], df_stations['name']))
    id_to_lat = dict(zip(df_stations['id'], df_stations['latitude']))
    id_to_lon = dict(zip(df_stations['id'], df_stations['longitude']))

    # Build Graph
    G_L = nx.Graph()

    # Add nodes
    for idx, row in df_stations.iterrows():
        name = row['name']
        G_L.add_node(name, 
                     id=int(row['id']),
                     lat=row['latitude'], 
                     lon=row['longitude'], 
                     zone=row['zone'],
                     pos=(row['longitude'], row['latitude']))

    # Add edges
    for idx, row in df_connections.iterrows():
        s1_id = int(row['station1'])
        s2_id = int(row['station2'])
        s1_name = id_to_name[s1_id]
        s2_name = id_to_name[s2_id]
        
        lat1, lon1 = id_to_lat[s1_id], id_to_lon[s1_id]
        lat2, lon2 = id_to_lat[s2_id], id_to_lon[s2_id]
        dist = haversine(lat1, lon1, lat2, lon2)
        
        if G_L.has_edge(s1_name, s2_name):
            G_L[s1_name][s2_name]['lines'].append(int(row['line']))
        else:
            G_L.add_edge(s1_name, s2_name, weight=dist, time=row['time'], lines=[int(row['line'])])

    return G_L, df_stations, df_connections, df_lines
