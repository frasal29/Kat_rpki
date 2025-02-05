import json

def build_customer_cone(graph, start_as):
    """
    Builds the Customer Cone for a specific Autonomous System (AS), including level management.

    :param graph: Dictionary representing the AS graph with relationships (p2c, c2p, p2p).
    :param start_as: The AS number to start building the Customer Cone from.
    :return: A dictionary representing the Customer Cone of the specified AS.
    """
    visited = set()  # Set to track visited nodes
    customer_cone = {}  # Dictionary to store the Customer Cone

    def dfs(as_node, level_min, level_max):
        """
        Performs a Depth-First Search (DFS) to traverse and build the Customer Cone.

        :param as_node: The current AS node being visited.
        :param level_min: The minimum level of the current AS node relative to the start AS.
        :param level_max: The maximum level of the current AS node relative to the start AS.
        """
        # If the node is already visited, update levels if needed
        if as_node in customer_cone:
            # Update the levelMin only if the new level is lower
            if level_min < int(customer_cone[as_node]["levelMin"]):
                customer_cone[as_node]["levelMin"] = str(level_min)  # Save as string

            # Update the levelMax only if the new level is higher
            if level_max > int(customer_cone[as_node]["levelMax"]):
                customer_cone[as_node]["levelMax"] = str(level_max)
            else:
                return  # No need to update further if levels are unchanged
        else:
            # Create a structure for the node in the Customer Cone with its level
            customer_cone[as_node] = {
                "levelMin": str(level_min),  # Save as string
                "levelMax": str(level_max),  # Save as string
                "p2p": [],  # Peer-to-peer relationships
                "p2c": graph[as_node]["p2c"],  # Provider-to-customer relationships
                "c2p": []  # Customer-to-provider relationships
            }

        visited.add(as_node)  # Mark the node as visited

        # Visit the customers of the current node (recursively) and increment the levels
        for customer in graph[as_node]["p2c"]:
            dfs(customer, level_min + 1, level_max + 1)

    # Start the DFS traversal from the specified node with level 0
    dfs(start_as, 0, 0)

    # Populate the p2p and c2p relationships within the Customer Cone
    for as_node in visited:
        # Add internal peers to the Customer Cone while maintaining the same level
        for peer in graph[as_node]["p2p"]:
            if peer in visited:
                customer_cone[as_node]["p2p"].append(peer)
        # Add internal providers to the Customer Cone
        for provider in graph[as_node]["c2p"]:
            if provider in visited:
                customer_cone[as_node]["c2p"].append(provider)

    return customer_cone

def create_specified_customer_cone(graph, specified_AS):
    """
    Creates the Customer Cone for a specific AS and saves it to a JSON file.

    :param graph: Dictionary representing the AS graph with relationships (p2c, c2p, p2p).
    :param specified_AS: The AS number for which to create the Customer Cone.
    :return: The path to the JSON file containing the Customer Cone.
    """
    # Build the Customer Cone
    customer_cone = build_customer_cone(graph, specified_AS)
    path_file = "output/customer_cone.json"  # Path to save the JSON file

    # Save the result to a JSON file
    with open(path_file, "w") as outfile:
        json.dump(customer_cone, outfile, indent=4)

    return path_file, customer_cone