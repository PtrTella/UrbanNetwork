import networkx as nx
import pandas as pd


def attack_top_hubs(G_bus, G_full, top_bottlenecks):
    """
    Esegue uno stress-test infrastrutturale rimuovendo a cascata i Top Hub.
    Dimostra la differenza di resilienza tra una rete solo-bus e una bus+tram.
    """
    print("\n=== Phase 4: Resilience Stress-Test ===")
    print(
        "Simulazione attacco a cascata ai Top 5 Hub (Infrastructural Node Failure)..."
    )

    # Efficienza Iniziale (Baseline)
    eff_bus_base = nx.global_efficiency(G_bus)
    eff_full_base = nx.global_efficiency(G_full)

    print(
        f"\n{'Hub Compromesso':<32} | {'Crollo Rete Solo-Bus':<22} | {'Crollo Rete Bus+Tram':<22}"
    )
    print("-" * 82)

    G_bus_attack = G_bus.copy()
    G_full_attack = G_full.copy()

    for node_id, node_name in top_bottlenecks:
        # Attacco l'Infrastruttura (Il nodo scompare dalla città in entrambi gli scenari)
        if G_bus_attack.has_node(node_id):
            G_bus_attack.remove_node(node_id)
        if G_full_attack.has_node(node_id):
            G_full_attack.remove_node(node_id)

        # Ricalcolo
        eff_bus_new = nx.global_efficiency(G_bus_attack)
        eff_full_new = nx.global_efficiency(G_full_attack)

        # Calcolo del Delta percentuale
        drop_bus = ((eff_bus_base - eff_bus_new) / eff_bus_base) * 100
        drop_full = ((eff_full_base - eff_full_new) / eff_full_base) * 100

        print(f"{node_name:<32} | -{drop_bus:.2f}%{'':<15} | -{drop_full:.2f}%")


def calculate_demographics_weight(G_full, raw_dir_path):
    """
    Fase 5: Carica i dati demografici ISTAT e li spalma sulle fermate in base all'Area Statistica.
    Bug Fix: Normalizzazione testi e rimozione fermate duplicate (Stop-Line).
    """
    demo_path = raw_dir_path / "bologna_demographics.csv"
    stops_path = raw_dir_path / "bologna_bus_stops.csv"

    if not demo_path.exists() or not stops_path.exists():
        print("Dataset mancanti per l'analisi demografica.")
        return

    # 1. Caricamento e Normalizzazione Demografia
    df_demo = pd.read_csv(demo_path, sep=";")
    anno_max = df_demo["anno"].max()  # Prende in automatico il 2024
    df_demo = df_demo[df_demo["anno"] == anno_max]

    # Normalizzazione Stringhe (Tutto maiuscolo, senza spazi laterali)
    df_demo["area_statistica"] = (
        df_demo["area_statistica"].astype(str).str.upper().str.strip()
    )
    pop_area = df_demo.groupby("area_statistica")["residenti"].sum().reset_index()

    # 2. Caricamento e Normalizzazione Fermate
    df_stops = pd.read_csv(stops_path, sep=";")
    df_stops["stop_name"] = (
        df_stops["denominazione"].astype(str).str.upper().str.strip()
    )
    df_stops["area_statistica"] = (
        df_stops["area_statistica"].astype(str).str.upper().str.strip()
    )

    # FIX FONDAMENTALE: Rimuovere i duplicati!
    # Teniamo solo le combinazioni uniche (Nome Fermata - Area)
    df_unique_stops = df_stops[["stop_name", "area_statistica"]].drop_duplicates()

    # Calcoliamo quante fermate "fisiche" vere ci sono per ogni Area
    stops_per_area = df_unique_stops["area_statistica"].value_counts().reset_index()
    stops_per_area.columns = ["area_statistica", "num_stops_unici"]

    # Unione Popolazione -> Divisa per Numero Fermate Reali
    pop_area = pop_area.merge(stops_per_area, on="area_statistica", how="inner")
    pop_area["pop_per_stop"] = pop_area["residenti"] / pop_area["num_stops_unici"]

    # Mappiamo il peso demografico su ogni singola fermata unica
    df_stops_pop = df_unique_stops.merge(
        pop_area[["area_statistica", "pop_per_stop"]], on="area_statistica", how="inner"
    )

    # Raggruppiamo per sicurezza nel caso una fermata stia sul confine di due aree
    pop_dict = df_stops_pop.groupby("stop_name")["pop_per_stop"].mean().to_dict()

    # 3. Pesatura del Grafo L-Space
    for n, data in G_full.nodes(data=True):
        node_name = data.get("name", "").strip().upper()
        # Se la fermata è fuori Bologna o non ha dati, prende 0
        peso_pop = pop_dict.get(node_name, 0)

        # --- INIEZIONE PENDOLARI (Dati Ufficiali RFI / PUMS) ---
        if node_name == "STAZIONE CENTRALE" or node_name == "MEDAGLIE D'ORO":
            peso_pop += 159000  # RFI: 58 mln/anno
        if node_name == "AUTOSTAZIONE":
            peso_pop += 14000  # PUMS: ~5 mln/anno
        # -------------------------------------------------------

        G_full.nodes[n]["population_served"] = peso_pop

    # Estrazione Nodi (Raggruppati per nome per evitare cloni visivi delle paline)
    unique_hubs = {}
    for n, data in G_full.nodes(data=True):
        name = data.get("name", "SCONOSCIUTO").strip()
        pop = data.get("population_served", 0)
        unique_hubs[name] = max(unique_hubs.get(name, 0), pop)

    nodes_pop = sorted(unique_hubs.items(), key=lambda x: x[1], reverse=True)

    print("\nTop 5 Hub per Pressione Demografica (Residenti + Pendolari):")
    for name, pop in nodes_pop[:5]:
        print(f"  - {name:<35} {int(pop)} abitanti")
