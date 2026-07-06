import pandas as pd
import folium
from pathlib import Path

# Configurazione Percorsi
BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"
OUTPUT_MAP = BASE_DIR / "data_output" / "bologna" / "bologna_interactive_map.html"


def get_color_for_route(route_id):
    """Genera un colore visivamente distinto basato sull'ID della linea."""
    colors = [
        "#3498db",
        "#9b59b6",
        "#34495e",
        "#16a085",
        "#f39c12",
        "#d35400",
        "#c0392b",
        "#0097e6",
        "#8c7ae6",
        "#e1b12c",
    ]
    return colors[hash(str(route_id)) % len(colors)]


def generate_interactive_map():
    print("Generazione Mappa Interattiva (con selettore di Linee) in corso...")

    m = folium.Map(location=[44.4949, 11.3426], zoom_start=13, tiles="CartoDB positron")

    try:
        df_bus_nodes = pd.read_csv(PROCESSED_DIR / "bologna_stations.csv")
        df_bus_edges = pd.read_csv(PROCESSED_DIR / "bologna_connections.csv")
        df_tram_nodes = pd.read_csv(PROCESSED_DIR / "bologna_tram_stations.csv")
        df_tram_edges = pd.read_csv(PROCESSED_DIR / "bologna_tram_connections.csv")
    except FileNotFoundError:
        print(
            "Errore: Impossibile trovare i file. Assicurati di aver lanciato il preprocessing."
        )
        return

    # Lookup veloce coordinate
    bus_coords = {
        str(row["stop_id"]): (row["stop_lat"], row["stop_lon"])
        for _, row in df_bus_nodes.iterrows()
    }
    tram_coords = {
        str(row["stop_id"]): (row["stop_lat"], row["stop_lon"])
        for _, row in df_tram_nodes.iterrows()
    }
    all_coords = {**bus_coords, **tram_coords}

    # FEATURE GROUPS
    fg_tram_rossa = folium.FeatureGroup(name="TRAM - Linea Rossa", show=True)
    fg_tram_verde = folium.FeatureGroup(name="TRAM - Linea Verde", show=True)
    fg_tram_nodi = folium.FeatureGroup(name="Nodi Tram", show=True)
    fg_bus_nodi = folium.FeatureGroup(name="Tutti i Nodi Bus", show=False)

    bus_layers = {}
    unique_bus_routes = df_bus_edges["route_id"].unique()
    for route in unique_bus_routes:
        bus_layers[str(route)] = folium.FeatureGroup(
            name=f"BUS - Linea {route}", show=False
        )

    # DISEGNO ARCHI BUS
    print(" -> Disegno Archi Bus nei rispettivi Layer...")
    for _, row in df_bus_edges.iterrows():
        u, v = str(row["stop_id"]), str(row["next_stop_id"])
        route = str(row["route_id"])
        if u in all_coords and v in all_coords:
            folium.PolyLine(
                locations=[all_coords[u], all_coords[v]],
                color=get_color_for_route(route),
                weight=3,
                opacity=0.7,
                popup=f"Bus Linea: {route}",
            ).add_to(bus_layers[route])

    # DISEGNO ARCHI TRAM (Supporta Nativamente Bivi e Deviazioni)
    print(" -> Disegno Archi Tram...")
    for _, row in df_tram_edges.iterrows():
        u, v = str(row["stop_id"]), str(row["next_stop_id"])
        route = str(row["route_id"]).upper()

        if u in all_coords and v in all_coords:
            # FIX: Supporta sia l'ID testuale (RED)
            if "RED" in route or "ROSSA" in route:
                folium.PolyLine(
                    locations=[all_coords[u], all_coords[v]],
                    color="#e74c3c",
                    weight=5,
                    opacity=0.9,
                ).add_to(fg_tram_rossa)
            else:
                folium.PolyLine(
                    locations=[all_coords[u], all_coords[v]],
                    color="#27ae60",
                    weight=5,
                    opacity=0.9,
                ).add_to(fg_tram_verde)

    # DISEGNO NODI BUS
    print(" -> Disegno Nodi Bus...")
    for _, row in df_bus_nodes.iterrows():
        folium.CircleMarker(
            location=(row["stop_lat"], row["stop_lon"]),
            radius=3,
            color="#2c3e50",
            fill=True,
            fill_opacity=0.8,
            popup=f"BUS: {row['stop_name']}",
        ).add_to(fg_bus_nodi)

    # DISEGNO NODI TRAM
    print(" -> Disegno Nodi Tram...")
    for _, row in df_tram_nodes.iterrows():
        ntype = str(row.get("node_type", "fermata")).lower()
        if ntype in ["bivio", "intersezione"]:
            color, radius = "#f39c12", 8
        elif ntype == "capolinea":
            color, radius = "#8e44ad", 8
        else:
            color, radius = "#2980b9", 6

        folium.CircleMarker(
            location=(row["stop_lat"], row["stop_lon"]),
            radius=radius,
            color=color,
            fill=True,
            fill_opacity=1.0,
            popup=f"TRAM [{ntype.upper()}]: {row['stop_name']}",
        ).add_to(fg_tram_nodi)

    # AGGIUNTA LAYER
    m.add_child(fg_tram_rossa)
    m.add_child(fg_tram_verde)
    m.add_child(fg_tram_nodi)
    for layer in bus_layers.values():
        m.add_child(layer)
    m.add_child(fg_bus_nodi)

    folium.LayerControl(collapsed=True).add_to(m)

    OUTPUT_MAP.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(OUTPUT_MAP))
    print(f" Mappa salvata con successo in: {OUTPUT_MAP}")


if __name__ == "__main__":
    generate_interactive_map()
