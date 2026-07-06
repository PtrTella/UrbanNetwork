# The Topology of Urban Resilience: Network Analysis, Vulnerability, and Greenfield Optimization of Bologna’s Transit System

This repository contains the complete codebase, data processing pipelines, and analytical models used to study the structural resilience and optimization of the public transit network of **Bologna, Italy**. 

Using a complex networks framework (Network Science / Social Network Analysis), the project evaluates Bologna's current bus-dominated transit network and models the impact of integrating planned high-capacity tramways. Furthermore, it implements an algorithmic solution to the **Transit Network Design Problem (TNDP)** to design a demographically optimized greenfield tram network under budget constraints.

---

## 🚀 Project Overview & Core Architecture

The study models the transit network through two topological representations:
1. **L-Space (Physical Graph):** Stops represent nodes, and edges represent physical, adjacent connections between consecutive stops. Edge weights are defined by passenger travel times (in seconds) adjusted for passenger dwell times and localized congestion.
2. **P-Space (Cognitive Graph):** Nodes represent stops, and a cognitive edge connects any two stops if they share at least one transit line, representing a zero-transfer journey.

### Exogenous Stress & Demographic Pressure
Rather than analyzing a purely topological network, our pipeline snaps **municipal resident population statistics (2024, by statistical area)** within a 400m catchment buffer of each stop. Station dwell times are scaled dynamically based on demographic pressure:
$$t_{dwell} = t_{base\_dwell} + \frac{P_{stop} \cdot \theta}{F_{capacity}}$$
where $t_{base\_dwell}$ is 5.0s for buses and 8.0s for trams, $\theta = 0.015\text{ s/capita}$ is the boarding time coefficient, and $F_{capacity}$ represents boarding door efficiency (1.0 for buses, 3.0 for low-floor trams).

---

## 📈 Key Analytical Findings

### 1. Macroscopic Topology & Small-Worldness
Under demographically loaded travel times (dynamic dwell times applied), the L-Space network displays distinct small-world properties, balancing local clustering with short path lengths.

| Metric | Bus Only (Baseline) | Planned Tram (TPER) |
| :--- | :---: | :---: |
| **Nodes ($N_{lcc}$)** | 1212 | 1283 |
| **Edges ($M_{lcc}$)** | 1482 | 1570 |
| **Avg Travel Time $L$** | 2162.69 sec | 2183.89 sec |
| **Clustering Coefficient ($C$)** | 0.0113 | 0.0124 |
| **Global Efficiency ($E_{glob}$)** | $0.000658\text{ s}^{-1}$ | $0.000690\text{ s}^{-1}$ |
| **Small-World Sigma ($\sigma$)** | 2.35 | 4.29 |
| **Small-World Omega ($\omega$)** | 0.00 | 0.00 |

*Note: The collapse of Telesford's Omega ($\omega = 0.00$) is a structural property of Space L transit networks, where the low average degree ($\langle k \rangle \approx 2.4$) yields undefined ratio comparisons with regular lattices.*

### 2. Physical Bottlenecks (L-Space Betweenness Centrality)
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
* **Sequential Targeted Attacks:** Extremely damaging. Removing the top 5% highest-betweenness nodes causes global efficiency to crash by **27.43%**, forcing passengers onto long, circuitous detours even before the network physically fragments.

### 4. Greenfield Tramway Optimization (TNDP)
We implemented a greenfield greedy optimization algorithm to layout a new 25 km tramway starting at the seed hubs *Farini* and *Piazza Cavour* (the two highest-scoring nodes by combined betweenness and demographic weight), maximizing a multi-criteria edge utility:
$$U(e) = \alpha \cdot EB(e) + \beta \cdot \Delta t(e) \cdot EB(e) + \gamma \cdot \text{avg\_pop}(e)$$

| Scenario | Avg Travel Time $L$ (sec) | Global Efficiency $E_{glob}$ ($\text{s}^{-1}$) | Tram Population Served |
| :--- | :---: | :---: | :---: |
| **Bus Only** | 2162.69 | 0.000658 | N/D |
| **Planned Tram (TPER)** | 2183.89 | 0.000690 | 33,106 |
| **Circular Tram (Ring)** | 2155.92 | 0.000702 | 45,227 |
| **Optimal Tram (TNDP)** | 2060.40 | 0.000688 | **42,230** |

*Our algorithmically designed **Optimal Tram** achieves the lowest average travel time and a **27.6% increase in demographic coverage** over the Planned TPER layout by routing along high-density and high-betweenness corridors.*

### 5. Commuter Shock: Forced Hub Passenger Injection
We simulated a massive commuter shock (up to 100,000 incoming passengers) at *Stazione Centrale* and *Autostazione* to test network absorption capacity:
* **Planned & Optimal Tramways** route passengers directly through the historic core, causing average travel times to roughly double (from ~23-24 to **~48-49 minutes**).
* **Circular Tramway (Lines 32/33)** acts as a fast bypass, allowing commuters to disperse along the ring road, saving **7.05 minutes** (-14.5%) compared to the planned radial lines.

---

## 📁 Repository Structure

```
├── run_analysis_bologna.py      # Main pipeline script (Act 1 to Act 4)
├── src/
│   ├── graph.py                 # Graph building, Space L & Space P parsers
│   ├── analyzer.py              # Centralities, small-worldness & assortativity
│   ├── simulator.py             # Percolation and targeted attack simulations
│   ├── demographic.py           # Census tract spatial snapping & BPR formulas
│   ├── tram_optimizer.py        # Greenfield TNDP greedy optimization
│   ├── plottings.py             # Visualizations, maps, and comparative plots
│   └── config.py                # Hyperparameters, capacities, and file paths
├── dataset/
│   └── bologna/
│       ├── raw/                 # Raw GTFS, census demographics, and OSM stops
│       └── processed/           # Processed CSV nodes, edges, and graphs
├── data_output/                 # Exported metrics (CSV) and runtime logs
└── latex/
    ├── NetworkAnalysisReport.tex # Main academic LaTeX paper
    ├── references.bib           # BibTeX academic references
    └── figures/                 # Generated plots injected into the report
```

---

## ⚙️ How to Run

### 1. Requirements
Ensure you have Python 3.9+ installed. We recommend using a virtual environment:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```
*(Dependencies include: `networkx`, `pandas`, `numpy`, `matplotlib`, `seaborn`, `scipy`)*

### 2. Execution
Run the complete analysis pipeline (centrality calculations, null model comparisons, resilience percolations, future scenario tests, and plot exports):

```bash
python run_analysis_bologna.py
```

All plots will be generated and saved directly to the `data_output/` and `latex/figures/bologna/` directories.

> **Note on execution order (full rebuild from raw data):** the master pipeline consumes cached graphs and intermediate CSVs. To rebuild everything from scratch, run in order: `src/preprocessing/download.py` → `src/preprocessing/bus.py` → `src/preprocessing/tram.py` → `src/graph.py` (builds and caches the base graphs) → `src/analyzer.py` (exports P-Space communities) → `src/demographic.py` (exports demographic pressure CSVs) → `run_analysis_bologna.py`. The graph cache in `data_output/bologna/graphs/` always stores **base BPR travel times**; demographic dwell times are applied at runtime by the pipeline.

---

## 📚 Academic References

The mathematical formulations and research design are grounded in the following literature:
* **Small-World in Transit:** Latora, V. & Marchiori, M. (2002). *Is the Boston subway a small-world network?* Physica A.
* **Urban Complexity & Resilience:** Derrible, S. & Kennedy, C. (2010). *The complexity and robustness of metro networks.* Physica A.
* **Global Efficiency:** Latora, V. & Marchiori, M. (2001). *Efficient behavior of small-world networks.* Physical Review Letters.
* **Demand-Centrality Correlation:** Šfiligoj, T. et al. (2025). *Node importance corresponds to passenger demand in public transport networks.* Physica A.