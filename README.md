# Network Analysis of the Bologna Transit System: Bottlenecks and Resilience

This repository contains the complete codebase, data processing pipelines, and analytical models used to study the structural resilience and optimization of the public transit network of **Bologna, Italy**.

Using a complex networks framework (Network Science / Social Network Analysis), the project evaluates Bologna's current bus-dominated transit network and models the impact of integrating planned high-capacity tramways. Furthermore, it implements an algorithmic solution to the **Transit Network Design Problem (TNDP)** to design a demographically optimized greenfield tram network under budget constraints.

---

## Project Overview & Core Architecture

The study models the transit network through two topological representations:
1. **L-space (Physical Graph):** Stops are nodes, and edges represent physical, adjacent connections between consecutive stops. Edge weights are passenger travel times (in seconds) adjusted for dwell times and localized congestion.
2. **P-space (Cognitive Graph):** Nodes are stops, and a cognitive edge connects any two stops if they share at least one transit line, representing a zero-transfer journey.

### Exogenous Stress & Demographic Pressure
Rather than analyzing a purely topological network, our pipeline snaps **municipal resident population statistics (2024, by statistical area)** within a 400 m catchment buffer of each stop. Station dwell times are scaled dynamically based on demographic pressure:
$$t_{dwell} = t_{base\_dwell} + \frac{P_{stop} \cdot \theta}{F_{capacity}}$$
where $t_{base\_dwell}$ is 5.0 s for buses and 8.0 s for trams, $\theta = 0.015\text{ s/capita}$ is the boarding time coefficient, and $F_{capacity}$ represents boarding door efficiency (1.0 for buses, 3.0 for low-floor trams).

---

## Key Analytical Findings

### 1. Macroscopic Topology & Small-Worldness
Under demographically loaded travel times (dynamic dwell times applied), the L-space network displays distinct small-world properties, balancing local clustering with short path lengths.

| Metric | Bus Only (Baseline) | Planned Tram (TPER) |
| :--- | :---: | :---: |
| **Nodes ($N_{lcc}$)** | 1212 | 1283 |
| **Edges ($M_{lcc}$)** | 1482 | 1570 |
| **Avg Travel Time $L$** | 2162.69 sec | 2183.89 sec |
| **Clustering Coefficient ($C$)** | 0.0113 | 0.0124 |
| **Global Efficiency ($E_{glob}$)** | $0.000658\text{ s}^{-1}$ | $0.000690\text{ s}^{-1}$ |
| **Small-World Sigma ($\sigma$)** | 2.35 | 4.29 |
| **Small-World Omega ($\omega$)** | 0.00 | 0.00 |

*Note: The collapse of Telesford's Omega ($\omega = 0.00$) is a structural property of L-space transit networks, where the low average degree ($\langle k \rangle \approx 2.4$) yields undefined ratio comparisons with regular lattices.*

### 1b. Cognitive Topology (P-space)
Analyzing the transfer-based P-space (nodes = stops, edge = shared line) reveals how passengers experience the network:
* **Communities:** Louvain detection finds **10 transit basins** (e.g. Borgo Panigale W, San Donato E, Corticella N) — within a basin, most trips need no transfer.
* **Assortativity:** near-neutral degree correlation ($r = 0.0120$ bus → $0.0179$ with tram).
* **Core–Periphery:** the P-space is dense (≈0.10 vs ≈0.002 in L-space) and spans **34 k-core shells**, with a 137-stop innermost core at $k = 136$ — the imprint of the longest trunk lines (max degree 663 at Amendola).

### 2. Physical Bottlenecks (L-space Betweenness Centrality)
We computed weighted Betweenness Centrality based on shortest travel times to locate municipal chokepoints.

1. **Farini** (Bus: 0.13499 | Tram: 0.13066)
2. **Piazza Cavour** (Bus: 0.11527) / **Piazza dell'Unità** (Tram: 0.12946)
3. **Garganelli** (Bus: 0.10911) / **Matteotti Alta Velocità** (Tram: 0.12344)
4. **Porta Santo Stefano** (Bus: 0.10464) / **Ugo Bassi** (Tram: 0.11490)
5. **Marconi** (Bus: 0.10237) / **San Felice** (Tram: 0.11095)

*These locations represent the narrow historical corridors and city gates of Bologna, which control the global flow of passengers across the network.*

### 3. Resilience Stress-Tests (Percolation Analysis)
We simulated systemic attacks by removing nodes and measuring the decay of global efficiency:
* **Random Failures & Accidents:** Highly tolerated due to topological redundancy. At 5% removal, global efficiency drops by only ~14%.
* **Static Targeted Attacks:** Extremely damaging. Removing the top 5% highest-betweenness nodes causes global efficiency to crash by **27.43%** (while the network is still 88.83% physically connected), forcing passengers onto long, circuitous detours before the network fragments.
* **Dynamic Targeted Attacks:** A sequential variant recomputes betweenness after each removal, always striking the current worst bottleneck — Farini falls first in every scenario.

### 4. Greenfield Tramway Optimization (TNDP)
We implemented a greenfield greedy optimization algorithm to lay out a new 25 km tramway starting at the seed hubs *Farini* and *Piazza Cavour* (the two highest-scoring nodes by combined betweenness and demographic weight), maximizing a multi-criteria edge utility:
$$U(e) = \alpha \cdot EB(e) + \beta \cdot \Delta t(e) \cdot EB(e) + \gamma \cdot \text{avg\_pop}(e)$$

| Scenario | Avg Travel Time $L$ (sec) | Global Efficiency $E_{glob}$ ($\text{s}^{-1}$) | Tram Population Served |
| :--- | :---: | :---: | :---: |
| **Bus Only** | 2162.69 | 0.000658 | N/A |
| **Planned Tram (TPER)** | 2183.89 | 0.000690 | 33,106 |
| **Circular Tram (Ring)** | 2155.92 | 0.000702 | 45,227 |
| **Optimal Tram (TNDP)** | 2060.40 | 0.000688 | **42,230** |

*Our algorithmically designed **Optimal Tram** achieves the lowest average travel time and a **27.6% increase in demographic coverage** over the Planned TPER layout by routing along high-density and high-betweenness corridors.*

### 5. Commuter Shock: Forced Hub Passenger Injection
We simulated a massive commuter shock (up to 100,000 incoming passengers) at *Stazione Centrale* and *Autostazione* to test network absorption capacity:
* **Planned & Optimal Tramways** route passengers directly through the historic core, causing average travel times to roughly double (from ~23-24 to **~48-49 minutes**).
* **Circular Tramway (Lines 32/33)** acts as a fast bypass, allowing commuters to disperse along the ring road, saving **7.05 minutes** (-14.5%) compared to the planned radial lines.

---

## Repository Structure

```
├── run_analysis_bologna.py       # Main pipeline script (Act 1 to Act 4)
├── requirements.txt              # Python dependencies
├── src/
│   ├── preprocessing/
│   │   ├── download.py           # Fetch GTFS, OSM tram stops, and municipal open data
│   │   ├── bus.py                # Build bus nodes/edges; join traffic sensors & accidents
│   │   └── tram.py               # Geocode and consolidate tram stops from structured JSON
│   ├── graph.py                  # Graph building, L-space & P-space parsers, pickle cache
│   ├── scenarios.py              # Circular-tram (Lines 32/33) hypothetical injection
│   ├── analyzer.py               # Centralities, small-worldness, assortativity, communities
│   ├── simulator.py              # Percolation, targeted attacks, hub-injection shocks
│   ├── demographic.py            # Population snapping & dynamic dwell-time weighting
│   ├── tram_optimizer.py         # Greenfield TNDP greedy optimization
│   ├── plottings.py              # Report figures (static maps & comparative plots)
│   ├── visualize.py              # Interactive Folium HTML map
│   ├── generate_comparisons.py   # Legacy/standalone plot helpers
│   └── config.py                 # Hyperparameters, capacities, and physical constants
├── dataset/
│   └── bologna/
│       ├── raw/                  # Raw GTFS, municipal demographics, traffic, accidents, OSM
│       └── processed/            # Processed CSV nodes and edges
├── data_output/
│   └── bologna/
│       ├── graphs/               # Cached graph pickles (base BPR weights only)
│       └── *.csv                 # Exported metrics (centrality, macro, scenarios, …)
└── latex/
    ├── NetworkAnalysisReport.tex # Main academic LaTeX paper
    ├── references.bib            # BibTeX academic references
    └── figures/                  # Generated plots injected into the report
```

---

## How to Run

### 1. Requirements
Ensure you have Python 3.9+ installed. We recommend using a virtual environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
All dependencies are pinned in `requirements.txt` (core: `networkx`, `pandas`, `numpy`; geospatial: `geopandas`, `geopy`; clustering: `scikit-learn`; visualization: `matplotlib`, `seaborn`, `contextily`, `folium`).

### 2. Execution
Run the complete analysis pipeline (centrality calculations, null model comparisons, resilience percolations, future scenario tests, and plot exports):

```bash
python run_analysis_bologna.py
```

All plots are generated and saved directly to the `data_output/` and `latex/figures/bologna/` directories.

> **Note on execution order (full rebuild from raw data):** the master pipeline consumes cached graphs and intermediate CSVs. To rebuild everything from scratch, run in order: `src/preprocessing/download.py` → `src/preprocessing/bus.py` → `src/preprocessing/tram.py` → `src/graph.py` (builds and caches the base graphs) → `src/analyzer.py` (exports P-space communities) → `src/demographic.py` (exports demographic pressure CSVs) → `run_analysis_bologna.py`. The graph cache in `data_output/bologna/graphs/` always stores **base BPR travel times**; demographic dwell times are applied at runtime by the pipeline.

### 3. Interactive Map (optional)
For a browsable, layer-toggle map of all bus and tram lines:

```bash
python -m src.visualize
```
Output: `data_output/bologna/bologna_interactive_map.html` (open in any browser).

---
