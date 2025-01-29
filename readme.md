# RPKI-BGP Simulation Framework

This project implements a simulation framework for BGP announcements and RPKI adoption in a network topology. The main script, `kat_rpki.py`, orchestrates the configuration, analysis, and simulation of attacks on the network. It includes tools to analyze AS relationships, generate configurations, simulate attacks on the BGP infrastructure, and calculate statistics for the customer cone of an AS.

---

## Project Structure

### Main Script

- `kat_rpki.py`: The main script that manages the workflow, including topology creation, RPKI configurations, attack simulations, and statistics generation.

### Configuration and Input Files

- `config.json`: Contains the main configuration parameters, such as the RPKI adoption percentage, path to the AS relationships file, flag for generating statistics, flag for start a random configuration with adoption percentage of RPKI and Collector.
- `20241101_as-rel2.txt`: File defining relationships between Autonomous Systems (AS), such as provider-to-customer (p2c), customer-to-provider (c2p) and peer-to-peer (p2p).

### Core Modules

1. **Topology and Graph Parsing**

   - `parse_as_graph.py`: Parses AS relationship files and generates a graph structure.
   - `customer_cone.py`: Creates a "customer cone" graph starting from a specified AS.
   - `statistics_customer_cone.py`: Generates and saves statistics for the customer cone, such as size, sub-cones, and maximum depth.
   - `neighbor_dictionary.py`: Builds a dictionary of neighbors and their LAN assignments based on the topology.

2. **Configuration Generators**

   - `configuration_files.py`: Generates configurations for RPKI servers (Routinator, Krill) and routers.
   - `daemons.py`: Creates `daemons` files for router startup configurations.
   - `frr.py`: Generates configuration files for FRRouting (FRR).
   - `startup.py`: Automates the creation of startup scripts for routers.

3. **Simulation and Visualization**

   - `app.py`: Provides a Dash-based GUI for visualizing and interacting with the network topology.
   - `app_result.py`: Visualizes attack results and their impact on the network.

4. **Attacks and Analysis**

   - `attack.py`: Simulates a malicious actor announcing routes from another AS.
   - `bgp_convergence.py`: Ensures BGP route convergence before simulations or attacks.
   - `bgp_aspath_check.py`: Analyzes BGP paths to validate attack outcomes.

5. **Lab Setup**

   - `lab_collision_domain.py`: Configures routers and links in a simulated lab environment.

### Outputs

- **Generated Files**: Includes configurations, logs, and attack simulation results.
- **JSON Outputs**:
  - `as_graph.json`: Parsed AS graph.
  - `customer_cone.json`: Customer cone for the selected AS.
  - `statistics_customer_cone.json`: Statistical data about the customer cone.
  - `neighbor_dict.json`: Dictionary of AS neighbors.
  - `Collision_domains.json`: Collision domain mappings.

---

## Workflow

### 1. Configure Settings

Update the `config.json` file with the desired parameters, such as the RPKI adoption percentage, the path to the AS relationships file, and whether to enable statistics generation:

```json
{
  "relations_file": "20241101_as-rel2.txt",
  "specified_as": "51028",
  "random_configuration": true,
  "adoption_rpki": 90,
  "adoption_collector_peer": 10,
  "prefer_customer": true,
  "invalid_prefixes_in_bgp_table": true,
  "show_statistics_ccone": true
}
```

### 2. Run the Main Script

Run the command:

```bash
python kat_rpki.py
```

This script:

- Reads the AS relationships file (`20241101_as-rel2.txt`).
- Creates the AS graph and generates a topology based on a specified AS.
- Builds the customer cone and saves it to `customer_cone.json`.
- Optionally generates statistics for the customer cone and saves them to `statistics_customer_cone.json`.
- Runs a Dash app to select RPKI nodes, collectors, hackers, and victims.
- Configures the topology in a simulated lab.
- Simulates BGP attacks and analyzes the results.

### 3. Interact with the Network

Use the Dash app to select RPKI nodes, collectors, and identify hacker/victim ASes.

### 4. Simulate and Analyze Attacks

- Generate attack scripts with `attack.py`.
- Ensure BGP convergence with `bgp_convergence.py`.
- Analyze AS path deviations with `bgp_aspath_check.py`.

### 5. Visualize Results

The Dash GUI shows the impact of RPKI adoption, attack simulations, and customer cone statistics on the network.

---

## Complete File List

| File Name                     | Description                                         |
| ----------------------------- | --------------------------------------------------- |
| `kat_rpki.py`                 | Main script managing the workflow.                  |
| `config.json`                 | Configuration file with simulation parameters.      |
| `20241101_as-rel2.txt`        | AS relationships file.                              |
| `parse_as_graph.py`           | AS relationship parser and graph generator.         |
| `customer_cone.py`            | Generates customer cones for ASes.                  |
| `statistics_customer_cone.py` | Calculates and saves statistics for customer cones. |
| `neighbor_dictionary.py`      | Creates neighbor dictionaries for ASes.             |
| `configuration_files.py`      | Generates configurations for Routinator and Krill.  |
| `daemons.py`                  | Creates `daemons` files for routers.                |
| `frr.py`                      | Generates FRRouting configurations.                 |
| `startup.py`                  | Creates startup scripts for routers.                |
| `lab_collision_domain.py`     | Configures routers and links in the simulated lab.  |
| `attack.py`                   | Creates attack simulation scripts.                  |
| `bgp_convergence.py`          | Ensures BGP route convergence.                      |
| `bgp_aspath_check.py`         | Analyzes AS paths after attacks.                    |
| `app.py`                      | Dash app for topology visualization.                |
| `app_result.py`               | Dash app for visualizing attack results.            |

---

## Future Work

- **Support for Additional Attack Scenarios**: Include new simulation strategies to expand testing.
- **Enhanced Visualization**: Add advanced features for analyzing large-scale topologies.
- **Integration with Real-World Datasets**: Use real AS data to validate tests.

---

## Requirements

- **Kathara**: For lab simulation.
- **Docker**: To run containerized routers and RPKI servers.
- **Python Packages**: Listed in the `requirements.txt` file.

---

## How to Run

1. Set up the environment:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the main script:
   ```bash
   python kat_rpki.py
   ```