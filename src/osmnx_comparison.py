import osmnx as ox
import networkx as nx
try:
    from src.data_loader import load_london_network
except ModuleNotFoundError:
    from data_loader import load_london_network

def main():
    # TRUCCO 1: Configura OSMnx per scaricare i tag utili per le stazioni
    ox.settings.useful_tags_way += ['railway', 'tunnel', 'layer']
    ox.settings.useful_tags_node += ['railway', 'station', 'name']

    # 1. Definiamo l'area e il filtro per prendere SOLO la metropolitana (Subway)
    place_name = "Greater London, United Kingdom"
    subway_filter = '["railway"~"subway"]'

    print("Scaricando la rete metropolitana da OpenStreetMap...")
    # 2. Scarichiamo il grafo usando il filtro personalizzato
    G_raw = ox.graph_from_place(
        place_name, 
        custom_filter=subway_filter, 
        retain_all=True, 
        simplify=True
    )
    print(f"Grafo raw scaricato: {len(G_raw.nodes)} nodi e {len(G_raw.edges)} archi.")

    # TRUCCO 1: Conversione in grafo semplice non orientato
    G_simple = nx.Graph(G_raw)
    
    # TRUCCO 2: Consolidamento intersezioni/nodi vicini
    G_projected = ox.project_graph(G_raw)
    G_clean_raw = ox.consolidate_intersections(G_projected, rebuild_graph=True, tolerance=150, dead_ends=False)
    G_clean = nx.Graph(G_clean_raw)

    # 3. Carichiamo il dataset curato
    print("\nCaricando il dataset curato (Hennig & O'Brien)...")
    G_curated, _, _, _ = load_london_network()

    # 4. Calcoliamo e compariamo le statistiche
    print("\n" + "="*55)
    print("CONFRONTO TOPOLOGICO RETI ESTRATTE")
    print("="*55)
    
    def get_stats(G_net, name):
        num_nodes = len(G_net.nodes)
        num_edges = len(G_net.edges)
        density = nx.density(G_net)
        is_connected = nx.is_connected(G_net)
        
        # Giant component stats
        if not is_connected:
            comp = max(nx.connected_components(G_net), key=len)
            G_g = G_net.subgraph(comp).copy()
        else:
            G_g = G_net
            
        avg_path = nx.average_shortest_path_length(G_g)
        diameter = nx.diameter(G_g)
        transitivity = nx.transitivity(G_net)
        
        print(f"Statistiche per: {name}")
        print(f"  Nodi totali (N): {num_nodes}")
        print(f"  Archi totali (M): {num_edges}")
        print(f"  Rete Connessa: {is_connected}")
        print(f"  Nodi nella Componente Gigante: {len(G_g.nodes)}")
        print(f"  Average Path Length (Giant Component): {avg_path:.4f}")
        print(f"  Diametro (Giant Component): {diameter}")
        print(f"  Transittivita' globale: {transitivity:.4f}")
        print("-"*55)

    get_stats(G_simple, "OSMnx Raw (Multi-Grafo convertito a Semplice)")
    get_stats(G_clean, "OSMnx Clean (Consolidato 150m + Semplice)")
    get_stats(G_curated, "Dataset Curato (Hennig & O'Brien)")

if __name__ == "__main__":
    main()
