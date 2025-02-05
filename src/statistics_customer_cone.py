import json

# Function to count the number of AS in the customer cone
def count_as_in_customer_cone(customer_cone):
    return len(customer_cone)

# Function to count the number of sub-customer cones in a customer cone
def count_sub_customer_cones(customer_cone):
    # Get the root AS (the first node in the customer cone)
    root_as = next(iter(customer_cone))
    # Count nodes with at least one child ("p2c" relationships), excluding the root AS
    sub_customer_cones = sum(
        1 for as_node, data in customer_cone.items() 
        if data["p2c"] and as_node != root_as
    )
    return sub_customer_cones

# Function to find the maximum degree and count edges for p2c, c2p, and p2p relationships
def find_degree_p2c_c2p_p2p(customer_cone):
    # Initialize variables to track nodes with the highest degree
    max_node_p2c = None
    max_node_c2p = None
    max_node_p2p = None
    max_degree_p2c = 0
    max_degree_c2p = 0
    max_degree_p2p = 0

    # Initialize total degree counters
    total_degree_p2c = 0
    total_degree_c2p = 0
    total_degree_p2p = 0

    for as_node, data in customer_cone.items():
        # Calculate degrees for p2c, c2p, and p2p relationships
        degree_p2c = len(data["p2c"])
        degree_c2p = len(data["c2p"])
        degree_p2p = len(data["p2p"])

        total_degree_p2c += degree_p2c
        total_degree_c2p += degree_c2p
        total_degree_p2p += degree_p2p

        # Update max degree and corresponding node for p2c
        if degree_p2c > max_degree_p2c:
            max_node_p2c = as_node
            max_degree_p2c = degree_p2c

        # Update max degree and corresponding node for c2p
        if degree_c2p > max_degree_c2p:
            max_node_c2p = as_node
            max_degree_c2p = degree_c2p

        # Update max degree and corresponding node for p2p
        if degree_p2p > max_degree_p2p:
            max_node_p2p = as_node
            max_degree_p2p = degree_p2p

    # Since p2p relationships are bidirectional, divide the total by 2
    total_degree_p2p = int(total_degree_p2p / 2)

    return {
        "max_node_p2c": max_node_p2c,
        "max_degree_p2c": max_degree_p2c,
        "max_node_c2p": max_node_c2p,
        "max_degree_c2p": max_degree_c2p,
        "max_node_p2p": max_node_p2p,
        "max_degree_p2p": max_degree_p2p,
        "total_degree_p2c": total_degree_p2c,
        "total_degree_c2p": total_degree_c2p,
        "total_degree_p2p": total_degree_p2p
    }

# Function to find the maximum and minimum levels of a customer cone
def get_max_levels(customer_cone):
    # Initialize max level variables
    max_level_min = float('-inf')
    max_level_max = float('-inf')

    for node_data in customer_cone.values():
        # Extract levelMin and levelMax for each node
        level_min = int(node_data["levelMin"])
        level_max = int(node_data["levelMax"])
        # Update max and min levels
        max_level_min = max(max_level_min, level_min)
        max_level_max = max(max_level_max, level_max)

    return max_level_max, max_level_min

# Function to find the minimum and maximum depth of a specific node in the customer cone
def find_node_depth(customer_cone, target_node):
    if target_node is None:
        return None, None
    # Get the node data for the target node
    node_data = customer_cone[target_node]
    min_depth = int(node_data["levelMin"])
    max_depth = int(node_data["levelMax"])

    return min_depth, max_depth

# Function to generate statistics for the customer cone
def generate_statistics(customer_cone, specified_as):
    # Calculate basic statistics
    num_as = count_as_in_customer_cone(customer_cone)
    degree_stats = find_degree_p2c_c2p_p2p(customer_cone)
    sub_customer_cones = count_sub_customer_cones(customer_cone)
    max_level_max, max_level_min = get_max_levels(customer_cone)

    # Get depth information for the nodes with the highest degree
    min_depth_node_p2c, max_depth_node_p2c = find_node_depth(customer_cone, degree_stats["max_node_p2c"])
    min_depth_node_c2p, max_depth_node_c2p = find_node_depth(customer_cone, degree_stats["max_node_c2p"])
    min_depth_node_p2p, max_depth_node_p2p = find_node_depth(customer_cone, degree_stats["max_node_p2p"])

    # Construct the statistics dictionary
    stats = {
        specified_as: {
            "Size customer cone": num_as,  # Total number of AS in the cone
            "# p2c edges": degree_stats["total_degree_p2c"],  # Total provider-to-customer edges
            "# c2p edges": degree_stats["total_degree_c2p"],  # Total customer-to-provider edges
            "# p2p edges": degree_stats["total_degree_p2p"],  # Total peer-to-peer edges
            "Sub Customer Cones": sub_customer_cones,  # Number of sub-customer cones
            "Shortest Maximum path length": max_level_min,  # Minimum depth in the cone
            "Maximum depth": max_level_max,  # Maximum depth in the cone
            "AS with most p2c": degree_stats["max_node_p2c"],  # AS with the most p2c relationships
            "Degree AS with most p2c": degree_stats["max_degree_p2c"],  # Degree of the AS with most p2c
            "Min depth AS with most p2c": min_depth_node_p2c,  # Minimum depth of the AS with most p2c
            "Max depth AS with most p2c": max_depth_node_p2c,  # Maximum depth of the AS with most p2c
            "AS with most c2p": degree_stats["max_node_c2p"],  # AS with the most c2p relationships
            "Degree AS with most c2p": degree_stats["max_degree_c2p"],  # Degree of the AS with most c2p
            "Min depth AS with most c2p": min_depth_node_c2p,  # Minimum depth of the AS with most c2p
            "Max depth AS with most c2p": max_depth_node_c2p,  # Maximum depth of the AS with most c2p
            "AS with most p2p": degree_stats["max_node_p2p"],  # AS with the most p2p relationships
            "Degree AS with most p2p": degree_stats["max_degree_p2p"],  # Degree of the AS with most p2p
            "Min depth AS with most p2p": min_depth_node_p2p,  # Minimum depth of the AS with most p2p
            "Max depth AS with most p2p": max_depth_node_p2p   # Maximum depth of the AS with most p2p
        }
    }
    return stats

# Function to save statistics to a JSON file
def save_statistics_to_json(customer_cone, specified_as, output_file):
    # Generate the statistics dictionary
    statistics = generate_statistics(customer_cone, specified_as)
    # Write the statistics to a JSON file
    with open(output_file, "w") as outfile:
        json.dump(statistics, outfile, indent=4)
    print(f"Statistics saved to {output_file}")
