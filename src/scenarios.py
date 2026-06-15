# src/scenarios.py
import pandas as pd
from pathlib import Path
from src.graph import haversine
from src.config import TransitConfig

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "bologna" / "processed"


def inject_hypothetical_tram(G_base, route_to_upgrade="32"):
    G_hypo = G_base.copy()
    df_bus_edges = pd.read_csv(PROCESSED_DIR / "bologna_connections.csv")
    
    # Se l'upgrade riguarda la linea 32 o 33, aggiorniamo entrambe le circolari (oraria/antioraria)
    if str(route_to_upgrade) in ["32", "33"]:
        routes_to_upgrade = ["32", "33"]
    else:
        routes_to_upgrade = [str(route_to_upgrade)]

    edges_target = df_bus_edges[
        df_bus_edges["route_id"].astype(str).isin(routes_to_upgrade)
    ]

    archi_upgradati = 0
    for _, row in edges_target.iterrows():
        u, v = str(row["stop_id"]), str(row["next_stop_id"])
        if u in G_hypo and v in G_hypo:
            dist_m = haversine(
                G_hypo.nodes[u]["lat"],
                G_hypo.nodes[u]["lon"],
                G_hypo.nodes[v]["lat"],
                G_hypo.nodes[v]["lon"],
            )

            # TRASFORMAZIONE IN TRAM: Viaggia alla velocità del tram costante senza subire il traffico dei viali!
            tram_time_sec = dist_m / TransitConfig.TRAM_SPEED + TransitConfig.TRAM_BASE_DWELL
            G_hypo.add_edge(
                u, v, weight=tram_time_sec, type="tram", route="TRAM_CIRCOLARE_FUTURA"
            )

            G_hypo.nodes[u]["type"] = "intersezione_bus_tram"
            G_hypo.nodes[v]["type"] = "intersezione_bus_tram"
            archi_upgradati += 1

    print(
        f"🔮 Scenario Predittivo: Convertiti {archi_upgradati} archi bus in linee Tram ad alta velocità (Linee {', '.join(routes_to_upgrade)})."
    )
    return G_hypo
