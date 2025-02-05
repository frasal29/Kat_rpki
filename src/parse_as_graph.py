import re
import json

def parse_file(file_path):
    """
    Parses the BGP relations file between ASes and builds metadata with relationships and additional information.

    :param file_path: Path to the BGP relations file.
    :return: Dictionary containing parsed metadata.
    """
    # Data structures to store parsed information
    metadata = {
        'clique': [],  # List of clique ASes
        'ixp_ases': [],  # List of IXP ASes
        'bgp_sessions': [],  # List of BGP sessions (not used in this function)
        'as_relations': []  # List of AS relationships, including p2c and p2p
    }
    
    with open(file_path, 'r') as file:
        lines = file.readlines()
        print("Processing the BGP relations file...")
        
        # Iterate over each line in the file to extract relevant information
        for i, line in enumerate(lines):
            line = line.strip()  # Remove leading/trailing whitespace
            
            # Skip lines that start with "# source" (these lines provide metadata but aren't processed here)
            if line.startswith("# source"):
                continue
            
            # Parse the input clique line, which lists AS numbers forming a clique
            elif line.startswith("# input clique:"):
                clique_ases = map(int, line[len("# input clique:"):].strip().split())
                metadata['clique'] = list(clique_ases)  # Convert AS numbers to a list and store them
            
            # Parse the IXP ASes line, which lists AS numbers associated with internet exchange points
            elif line.startswith("# IXP ASes:"):
                ixp_ases = map(int, line[len("# IXP ASes:"):].strip().split())
                metadata['ixp_ases'] = list(ixp_ases)  # Convert AS numbers to a list and store them

            # Parse lines indicating provider-to-customer relationships
            # These lines have the format "provider|customer|-1"
            elif re.match(r"\d+\|\d+\|-1", line):
                parts = line.split('|')  # Split the line into provider, customer, and relation type
                provider_as = int(parts[0])  # The provider AS number
                customer_as = int(parts[1])  # The customer AS number
                metadata['as_relations'].append((provider_as, customer_as, -1))  # -1 indicates a p2c (provider-to-customer) relation
                
            # Parse lines indicating peer-to-peer relationships
            # These lines have the format "peer1|peer2|0"
            elif re.match(r"\d+\|\d+\|0", line):
                parts = line.split('|')  # Split the line into peers and relation type
                peer_as1 = int(parts[0])  # First peer AS number
                peer_as2 = int(parts[1])  # Second peer AS number
                # Optional source field (e.g., "RIPE" or "other source") if present in the line
                source = parts[3] if len(parts) > 3 else ''
                metadata['as_relations'].append((peer_as1, peer_as2, 0, source))  # 0 indicates a p2p (peer-to-peer) relation

    return metadata

def generate_as_graph(metadata):
    """
    Generates a graph structure from AS metadata.

    :param metadata: Metadata dictionary containing AS relationships.
    :return: Dictionary representing the AS graph.
    """
    as_graph = {}
    
    # Add AS nodes based on relationships
    for provider_as, customer_as, relation_type, *source in metadata['as_relations']:
        # Convert AS numbers to strings
        provider_as = str(provider_as)
        customer_as = str(customer_as)

        if provider_as not in as_graph:
            as_graph[provider_as] = {'p2p': [], 'p2c': [], 'c2p': []}
        if customer_as not in as_graph:
            as_graph[customer_as] = {'p2p': [], 'p2c': [], 'c2p': []}

        # Add the relationship to the graph
        if relation_type == -1:  # Provider to Customer (unidirectional)
            as_graph[provider_as]['p2c'].append(customer_as)
            as_graph[customer_as]['c2p'].append(provider_as)
        elif relation_type == 0:  # Peer-to-Peer (bidirectional)
            # Check before adding to avoid duplicates
            if customer_as not in as_graph[provider_as]['p2p']:
                as_graph[provider_as]['p2p'].append(customer_as)
            if provider_as not in as_graph[customer_as]['p2p']:
                as_graph[customer_as]['p2p'].append(provider_as)
    
    return as_graph

def save_as_graph_to_json(as_graph, output_file):
    """
    Saves the AS graph to a JSON file.

    :param as_graph: Dictionary representing the AS graph.
    :param output_file: Path to the output JSON file.
    """
    with open(output_file, 'w') as file:
        json.dump(as_graph, file, indent=4)
    print(f"AS graph saved to {output_file}")

def parse(input_file, output_file):
    """
    Parses a BGP relations file and generates an AS graph in JSON format.

    :param input_file: Path to the input BGP relations file.
    :param output_file: Path to the output JSON file.
    """
    # Step 1: Parse the file
    metadata = parse_file(input_file)
    
    # Step 2: Generate the AS graph
    as_graph = generate_as_graph(metadata)
    
    # Step 3: Save the AS graph to a JSON file
    save_as_graph_to_json(as_graph, output_file)