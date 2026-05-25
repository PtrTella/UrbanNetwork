### La Topologia della Città: Analisi Small-World e Resilienza Strutturale nella Rete di Trasporto Pubblico

_"The Topology of Urban Resilience: Small-World Analysis, Bottlenecks, and Structural Vulnerability in the Metro Network of [City of Your Choice]"_

---

### 1. Academic Reference Literature (The Background)

First of all, your project must rest on solid scientific foundations. You will begin the report by citing and contextualizing these key papers in order to justify your “Research Design”:

- **The theoretical foundation:** _Is the Boston subway a small-world network?_ (Latora & Marchiori, 2002). This is the paper recommended by the course. It demonstrates how transportation networks, despite being “spatial networks” (and therefore constrained by real-world geography), still exhibit small-world characteristics. It introduces the crucial concept of “transport efficiency” to overcome the limitations of classical models.
    
- **Complexity and Resilience:** _The complexity and robustness of metro networks_ (Derrible & Kennedy, 2010). This study on 33 metro systems worldwide is essential. It demonstrates that urban networks are often _Scale-Free_ systems dominated by “transfer hubs” (interchange stations). This will provide the theoretical basis to explain why the network is resistant to random failures but extremely vulnerable when a hub is targeted.
    
- **L-Space vs P-Space Topology:** In contemporary research, transportation networks are modeled according to two logical spaces. You will need to cite the so-called _Space L_ (where nodes are stations and edges represent a direct physical connection between adjacent stations) and _Space P_ (where an edge exists between two nodes if they belong to the same line, indicating the possibility of traveling without transfers). Your study will focus on _Space L_in order to map the real infrastructure.
    

---

### 2. Data and Technical Tools (The Tech Stack)

You will not waste time manually mapping stations. Instead, you will adopt an automated approach:

- **Data Acquisition:** You will use the remarkable Python library `OSMnx`. With a single line of code, this library can extract and model the infrastructural network of any city directly from the open OpenStreetMap database, returning a ready-to-use theoretical graph. Alternatively, you may import open transportation data in _GTFS_ format.
    
- **Mathematical Engine:** `NetworkX` (in Python) for adjacency matrix ingestion and the immediate computation of all the metrics studied during the course (Centrality, Shortest Paths, Triad Census).
    

---

### 3. Operational Work Plan: What to Apply and Demonstrate

You will divide the work into 4 precise experimental phases, which will comprehensively cover more than 60% of the evaluation rubric (methodological rigor).

---

#### Phase A: Network Construction

You will extract the metro or tram network (e.g., Milan, Paris, or Tokyo). You will model the network as an undirected graph in _Space L_ format (stations as nodes, tracks as edges). The physical distances in meters between stations will constitute the edge “weights” for distance evaluations.

---

#### Phase B: Microscopic Autopsy (Searching for the Gatekeepers)

You will apply the microscopic algorithms studied in Lecture 5:

- _Degree Centrality:_ You will identify the obvious interchange hubs.
    
- _Betweenness Centrality:_ This is the “Holy Grail” of your project. You will identify the stations that, despite not having many intersecting lines, act as vital bottlenecks for shortest paths between opposite sides of the city.
    
- _Closeness Centrality:_ To compute the average travel efficiency and determine the most “central” station in the system.
    

---

#### Phase C: Macroscopic Autopsy (Testing Small-Worldness)

You will need to numerically demonstrate whether the analyzed city qualifies as a “Small-World” network (Lecture 6).

- You will compute the Average Path Length ($L$) and the Global Clustering Coefficient ($C$).
    
- You will generate two comparison networks: a regular lattice and an Erdős-Rényi stochastic graph ($G(n,p)$) with the same number of nodes and the same density as your city network.
    
- By computing the structural coefficients $\sigma$ and $\omega$, you will demonstrate whether the city architecture balances high local clustering with surprisingly short global distances.
    

---

#### Phase D: Resilience Stress Test (The “Wow Effect” for the Top Grade)

This is the dynamic simulation that will conclude the research (Lecture 6):

1. _Random Failure:_ You will write a Python loop that virtually “shuts down” 5%, 10%, and 20% of the stations in a purely random way (e.g., scattered electrical blackouts). You will measure how much the system’s _Connectedness_metric decreases.
    
2. _Targeted Attack:_ Starting again from the intact network, you will shut down only 5% of the stations, but beginning with those having the highest _Betweenness Centrality_ identified in Phase B (e.g., a targeted strike or flooding of a critical interchange).
    
3. _Conclusion:_ You will graphically demonstrate how, consistently with Derrible & Kennedy’s theory on urban networks, public transportation tolerates random events quite well, but immediately fragments and loses cohesion under surgical attacks.
    

---

### 4. What You Must Study Thoroughly (Preparation Focus)

To write a rigorous essay and correctly interpret the data (the remaining 20% of the grade), you must master the following theoretical concepts from the course:

1. **The Mathematics of Small-World Networks:** Do not simply output the value of $\sigma$. You must be able to explain _why_ you compute the coefficient relative to the Erdős-Rényi random graph $G(n,p)$ and what the Average Path Length represents in terms of passenger transit times.
    
2. **Betweenness vs Degree:** The professor will try to assess whether you truly understand the semantic distinction between these measures. You must explain that Degree Centrality identifies the major stations (such as Roma Termini in Rome or Milano Centrale in Milan), whereas Betweenness Centrality identifies vulnerable structural “bridges” (perhaps a small peripheral station that nevertheless represents the only access route to an entire district).
    
3. **The Spatial Paradox:** Unlike the Internet (which can behave as an almost pure scale-free network), metro systems are physically anchored to the terrain. There is a physical limit to how many tracks can intersect within a station (network planarity). This means that node degrees can never reach the extreme levels observed in networks such as Spotify, thereby modifying the tail of the distribution. Correctly interpreting this factor will guarantee excellence.