# src/config.py


class TransitConfig:
    """Parametri ingegneristici e fisici per il modello di mobilità di Bologna."""

    # --- VELOCITÀ COMMERCIALI REALI (Metri al Secondo) ---
    WALKING_SPEED = 1.1  # ~4 km/h (Trasbordo pedonale medio)
    TRAM_SPEED = 5.5  # ~20 km/h (Tram costante in sede protetta)
    BUS_BASE_SPEED = 4.16  # ~15 km/h (Velocità del bus urbano senza traffico)
    MIN_BUS_SPEED = 1.0  # ~3.6 km/h (Velocità di strisciamento in congestione totale)

    # --- TOPOLOGIA ---
    SNAPPING_RADIUS = 30.0  # Distanza massima per la fusione dei nodi

    # --- FUNZIONE BPR (CONGESTIONE ORARIA) ---
    # Capacità oraria nominale di una corsia stradale urbana (Standard PUMS Bologna / HCM)
    BPR_ALPHA = 0.15  # Coefficiente standard di inizio rallentamento
    BPR_BETA = 4.0  # Esponente di penalizzazione stocastica esponenziale
