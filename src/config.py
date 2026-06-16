# src/config.py


class TransitConfig:
    """Parametri ingegneristici e fisici per il modello di mobilità di Bologna."""

    # --- VELOCITÀ COMMERCIALI REALI (Metri al Secondo) ---
    TRAM_SPEED = 5.5  # ~20 km/h (Tram costante in sede protetta)
    BUS_BASE_SPEED = 4.16  # ~15 km/h (Velocità del bus urbano senza traffico)
    MIN_BUS_SPEED = 1.0  # ~3.6 km/h (Velocità di strisciamento in congestione totale)

    # --- TOPOLOGIA ---
    SNAPPING_RADIUS = 30.0  # Distanza massima per la fusione dei nodi

    # --- FUNZIONE BPR (CONGESTIONE ORARIA) ---
    # Capacità oraria nominale di una corsia stradale urbana (Standard PUMS Bologna / HCM)
    BPR_ALPHA = 0.15  # Coefficiente standard di inizio rallentamento per auto
    BPR_BETA = 4.0  # Esponente di penalizzazione stocastica esponenziale
    # Calibrazione PCU (Passenger Car Equivalent) per i Mezzi Pubblici
    BUS_PCU = 2.5  # Un autobus urbano occupa lo spazio e la dinamica di 2.5 auto
    BPR_ALPHA_BUS = 0.20  # L'autobus risente maggiormente della congestione iniziale

    # --- DEMOGRAFIA ---
    # Raggio massimo in metri per associare spazialmente una fermata del grafo alle aree ISTAT
    DEMOGRAPHIC_SNAPPING_RADIUS = 400.0  # Ricalibrato: raggio di catchment realistico (~5 minuti a piedi)

    # --- CAPACITÀ STRADALE E CONFIGURAZIONI TRAM ---
    DEFAULT_ROAD_CAPACITY = 800.0  # Ricalibrato per Bologna: capacità stradale standard per corsia urbana ridotta
    OPTIMAL_TRAM_BUDGET_METERS = 25000  # Budget totale per la rete tram ottimale (25 km)
    OPTIMAL_TRAM_NUM_SEEDS = 2  # Ricalibrato: 2 hub seed centrali per riflettere le 2 linee tranviarie principali (Rossa e Verde)

    # --- FRIZIONE DI TRASBORDO (MULTIPLEX TRANSFER FRICTION) ---
    # Tempo di attesa medio (secondi) stimato per accedere alla coincidenza (1/2 headway medio)
    TRANSFER_WAITING_TIME = 150.0  # 2.5 minuti
    # Penalità cognitiva in secondi per tenere conto dello stress/scomodità del cambio linea
    TRANSFER_COGNITIVE_PENALTY = 180.0  # 3 minuti

    # --- TEMPI DI FERMATA DINAMICI (DWELL TIMES in secondi) ---
    # La fermata base a cui sommiamo il tempo di salita/discesa parametrato sulla demografia
    BUS_BASE_DWELL = 5.0
    TRAM_BASE_DWELL = 8.0
    # Tempo marginale di incarrozzamento per singolo passeggero potenziale
    DWELL_TIME_PER_CAPITA = 0.015  # secondi
    # Capacità nominale massima dei veicoli (passeggeri totali)
    BUS_MAX_CAPACITY = 90  # Capienza standard di un bus da 12m (seduti + in piedi)
    TRAM_MAX_CAPACITY = 250  # Capienza nominale di un tram da 32m (es. Stadler Tramlink)

    # Capacità di assorbimento del mezzo (modera il tempo di dwell in base al design delle porte)
    BUS_CAPACITY_FACTOR = 1.0  # Baseline
    TRAM_CAPACITY_FACTOR = 3.0  # Il tram imbarca molto più in fretta grazie a porte multiple ampie e piano ribassato totale
