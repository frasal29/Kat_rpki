import json
import app_result
from Kathara.manager.Kathara import Kathara

def execute_command_in_container(machine_name, lab, command):
    """
    Executes a command inside a container.

    :param machine_name: Machine object kathara
    :param command: Command to execute inside the container.
    :return: Output of the command as a string.
    """
    # Execute the command in the container
    result, stderr, return_code = Kathara.get_instance().manager.exec(machine_name, command, wait=False, stream=False, lab=lab)
    return result, stderr, return_code

def analyze_bgp_path(router, lab, hacker_node, victim_node, prefix, red_nodes, red_edge, green_nodes, green_edge, paths):
    """
    Analyzes the BGP path for a given prefix in a specific container.

    :param router: Router object.
    :param lab: Kathara lab instance.
    :param hacker_node: AS number of the hacker.
    :param victim_node: AS number of the victim.
    :param prefix: BGP prefix to analyze.
    :param red_nodes: List to store nodes originating from the hacker.
    :param red_edge: List to store edges originating from the hacker.
    :param green_nodes: List to store nodes originating from the victim.
    :param green_edge: List to store edges originating from the victim.
    :param paths: Dictionary to store paths observed in the BGP analysis.
    """
    try:
        # Extract the router name (AS number) from the container name
        router_name = router.name.split("router")[1]
        print(f"Analyzing router {router_name}")

        # Identify if the router is the hacker or victim
        if router_name == hacker_node:
            red_nodes.append(router_name)
        elif router_name == victim_node:
            green_nodes.append(router_name)

        # Execute the BGP command inside the container
        command = f'vtysh -c "sh ip bgp {prefix} bestpath json"'
        exec_result, stderr, return_code = execute_command_in_container(router.name, lab, command)
        output = exec_result.decode("utf-8").strip()

        if not output or output == "{}":
            print(f"No valid JSON output for container {router_name} with prefix {prefix}.")
            return

        # Parse the JSON result
        bgp_data = json.loads(output)

        # Analyze the BGP paths
        aspath_segments = bgp_data.get("paths", [{}])[0].get("aspath", {}).get("segments", [])
        origin_as = None
        if aspath_segments and "list" in aspath_segments[0]:
            as_path = aspath_segments[0]["list"]
            origin_as = str(as_path[-1])  # The last element is the origin AS

            # Add the router to the appropriate list based on the origin
            if origin_as == hacker_node:
                red_nodes.append(router_name)
            elif origin_as == victim_node:
                green_nodes.append(router_name)

            # Add edges to the paths dictionary
            paths[router_name] = []
            if as_path:
                # Add the first edge router_name -> as_path[0]
                first_edge = f"{router_name}->{as_path[0]}"
                paths[router_name].append(first_edge)

                # Add internal edges as_path[i] -> as_path[i+1]
                for i in range(len(as_path) - 1):
                    edge = f"{as_path[i]}->{as_path[i + 1]}"
                    paths[router_name].append(edge)

        # Handle edges in the advertisedTo section
        advertised_to = bgp_data.get("advertisedTo", {})
        for to_router, details in advertised_to.items():
            to_router_short = details["hostname"].replace("router", "")
            edge = f"{router_name}->{to_router_short}"
            reverse_edge = f"{to_router_short}->{router_name}"

            if router_name == hacker_node or origin_as == hacker_node:
                if edge not in red_edge and reverse_edge not in red_edge:
                    red_edge.append(edge)
            elif router_name == victim_node or origin_as == victim_node:
                if edge not in green_edge and reverse_edge not in green_edge:
                    green_edge.append(edge)

    except Exception as e:
        print(f"Error while analyzing container {router_name}: {e}")

def bgp_check(routers, lab, hacker_node, victim_node, prefix_to_check):
    """
    Performs a BGP analysis to identify paths, nodes, and edges related to a hacker and a victim.

    :param routers: Dictionary of router objects.
    :param lab: Kathara lab instance.   
    :param hacker_node: AS number of the hacker.
    :param victim_node: AS number of the victim.
    :param prefix_to_check: BGP prefix to analyze.
    """
    # Global lists for storing analysis results
    red_nodes = []
    red_edge = []
    green_nodes = []
    green_edge = []
    paths = {}

    try:
        print("\nStarting BGP route analysis on routers...")
        for router in routers.values():
            analyze_bgp_path(router, lab, hacker_node, victim_node, prefix_to_check, red_nodes, red_edge, green_nodes, green_edge, paths)

        # Save the results to a JSON file
        output_data = {
            "hacker_node": hacker_node,
            "victim_node": victim_node,
            "red_nodes": red_nodes,
            "red_edges": red_edge,
            "green_nodes": green_nodes,
            "green_edges": green_edge,
            "paths": paths
        }

        output_file = "output/bgp_analysis_results.json"
        with open(output_file, "w") as json_file:
            json.dump(output_data, json_file, indent=4)

        print(f"\nBGP route analysis results saved in {output_file}")

        # Load additional input files for visualization
        input_file = "output/customer_cone.json"
        with open(input_file, "r") as f:
            topology = json.load(f)

        with open("output/bgp_analysis_results.json", 'r') as file:
            results = json.load(file)

        with open("output/saved_nodes.json", 'r') as file:
            saved_nodes = json.load(file)

        # Run the Dash app to visualize the results
        app_result.run_dash_app(topology, results, saved_nodes)

    except Exception as e:
        print(f"Error: {e}")
