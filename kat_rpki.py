import os
import json
import logging
from Kathara.manager.Kathara import Kathara
from Kathara.model.Lab import Lab
import neighbor_dictionary
import roa_entry
import configuration_files
import lab_collision_domain
import frr
import daemons
import startup
import subprocess
import shutil
import time
import app
import customer_cone
import parse_as_graph
import attack
import bgp_convergence
import bgp_aspath_check
import docker
import statistics_customer_cone
import random

def generate_nodes(customer_cone, adoption_rpki_percent, adoption_collector_percent):
    """
    Generates a dictionary with RPKI nodes, Collector nodes, Hacker node, and Victim node.

    :param customer_cone: Dictionary representing the graph of customer cone nodes.
    :param adoption_rpki_percent: Percentage of nodes to include in rpki_nodes.
    :param adoption_collector_percent: Percentage of nodes to include in collector_nodes.
    :return: Dictionary with keys 'rpki_nodes', 'collector_nodes', 'hacker_node', 'victim_node'.
    """
    # Get all nodes from the graph
    all_nodes = list(customer_cone.keys())

    # Determine the number of nodes to include for RPKI and COLLECTOR
    num_rpki_nodes = int(len(all_nodes) * adoption_rpki_percent / 100)
    num_collector_nodes = int(len(all_nodes) * adoption_collector_percent / 100)

    # Randomly select RPKI and COLLECTOR nodes
    rpki_nodes = random.sample(all_nodes, num_rpki_nodes)
    collector_nodes = random.sample(all_nodes, num_collector_nodes)

    # Randomly select Hacker and Victim nodes (distinct)
    hacker_node = random.choice(all_nodes)
    victim_node = random.choice([node for node in all_nodes if node != hacker_node])

    # Build the result dictionary
    result = {
        "rpki_nodes": rpki_nodes,
        "collector_nodes": collector_nodes,
        "hacker_node": [hacker_node],
        "victim_node": [victim_node]
    }

    return result

def load_config(config_file):
    """
    Loads the configuration from a JSON file.
    """
    with open(config_file, "r") as file:
        config = json.load(file)
    return config

def get_valid_node_from_config_or_prompt(graph, specified_as):
    """
    Retrieves a valid node from the configuration file or prompts the user if not present.
    """
    def is_leaf_node(as_node):
        """Checks if the node is a leaf (without 'p2c' nodes)."""
        return not graph[as_node]["p2c"]  # Returns True if 'p2c' is empty

    if specified_as:
        if specified_as in graph:
            if not is_leaf_node(specified_as):
                return specified_as
            else:
                print(f"Error: the specified node '{specified_as}' is a leaf (no 'p2c' nodes).")
                exit(1)  # Exit if the specified node is a leaf
        else:
            print(f"Error: the specified node '{specified_as}' is not present in the graph.")
            exit(1)  # Exit if the specified node is invalid
    else:
        while True:
            specified_as = str(input("Choose the Customer Cone, enter its root AS: "))
            if specified_as in graph:
                if not is_leaf_node(specified_as):
                    return specified_as
                else:
                    print(f"Error: the chosen node '{specified_as}' is a leaf (no 'p2c' nodes). Try again.")
            else:
                print("Error: the chosen node is not present in the graph. Try again.")

def modify_topology_rpki(topology, rpki_nodes, collector_nodes):
    """
    Modifies the topology by adding 'collector' and 'rpki' attributes 
    based on the specified lists of rpki_nodes and collector_nodes.

    :param topology: Dictionary representing the topology.
    :param rpki_nodes: List of nodes to mark with "rpki": "yes".
    :param collector_nodes: List of nodes to mark with "collector": "yes".
    :return: Updated topology dictionary.
    """
    # Update the topology with new attributes
    for as_number in topology:
        # Assign "yes" or "no" to "collector" based on node presence in collector_nodes
        topology[as_number]["collector"] = "yes" if as_number in collector_nodes else "no"
        # Assign "yes" or "no" to "rpki" based on node presence in rpki_nodes
        topology[as_number]["rpki"] = "yes" if as_number in rpki_nodes else "no"
    
    return topology

def gen_certificates(input_file):
    """
    Generates certificates directly in the specified directory.
    """
    print("\nGenerating certificates...")
    # Create the certificates directory if it does not exist
    certificates_dir = f"lab_{input_file}/certificates"
    os.makedirs(certificates_dir, exist_ok=True)

    # Generate certificates in the certificates directory
    subprocess.run([
        "openssl", "req", "-new",
        "-x509",
        "-newkey", "rsa:4096",
        "-sha256",
        "-nodes",
        "-keyout", os.path.join(certificates_dir, "root.key"),
        "-out", os.path.join(certificates_dir, "root.crt"),
        "-days", "365",
        "-subj", "/C=IT/L=Roma/O=Roma Tre"
    ])

    with open(os.path.join(certificates_dir, "krill.ext"), "w") as ext_file:
        ext_file.write("""[krill]
subjectAltName=DNS:rpki-server.org, DNS:rpki-server.org:3000, DNS:rpki-server.org:80, DNS:localhost, IP:172.17.0.2, IP:127.0.0.1
basicConstraints=CA:FALSE
""")

    subprocess.run([
        "openssl", "req", "-new",
        "-newkey", "rsa:4096",
        "-keyout", os.path.join(certificates_dir, "krill.key"),
        "-out", os.path.join(certificates_dir, "krill.csr"),
        "-sha256",
        "-nodes",
        "-days", "365",
        "-subj", "/C=IT/L=Roma/O=Roma Tre/CN=rpki-server.org"
    ])

    subprocess.run([
        "openssl", "x509",
        "-in", os.path.join(certificates_dir, "krill.csr"),
        "-req",
        "-out", os.path.join(certificates_dir, "krill.crt"),
        "-CA", os.path.join(certificates_dir, "root.crt"),
        "-CAkey", os.path.join(certificates_dir, "root.key"),
        "-CAcreateserial",
        "-extensions", "krill",
        "-extfile", os.path.join(certificates_dir, "krill.ext"),
        "-days", "365"
    ])

    with open(os.path.join(certificates_dir, "krill.includesprivatekey.pem"), "w") as combined_file:
        with open(os.path.join(certificates_dir, "krill.crt"), "r") as crt_file:
            combined_file.write(crt_file.read())
        with open(os.path.join(certificates_dir, "krill.key"), "r") as key_file:
            combined_file.write(key_file.read())

# Function to write a list of strings into a file in a specified directory
def write_file_in_path(content_list_file, file_name, path):
    """
    Writes a list of strings to a file in the specified directory.

    :param content_list_file: List of strings to write.
    :param file_name: Name of the output file.
    :param path: Path to the output directory.
    """
    file_path = os.path.join(path, file_name)
    with open(file_path, "w", encoding="utf-8", newline="\n") as file:
        for line in content_list_file:
            file.write(line + "\n")

# Function to copy a file from one path to another, ensuring the output directory is created
def copy_file(source_path, output_directory, output_file_name):
    """
    Copies a file from a source path to an output directory.

    :param source_path: Path of the source file.
    :param output_directory: Path of the destination directory.
    :param output_file_name: Name of the output file.
    """
    # Full path of the destination file
    destination_path = os.path.join(output_directory, output_file_name)
    # Copy the file
    shutil.copy(source_path, destination_path)

# Configures BGP in routers using frr.conf and daemons files
def move_configurations_file(routers, krill, address_krill, image_frr, image_routinator, image_krill, input_file):
    """
    Moves and configures necessary files for routers, RPKI servers, and other components.

    :param routers: Dictionary of routers in the topology.
    :param krill: Krill server instance.
    :param address_krill: IP address of the Krill server.
    :param image_frr: Docker image for FRRouting routers.
    :param image_routinator: Docker image for Routinator.
    :param image_krill: Docker image for Krill.
    :param input_file: Name of the input configuration file.
    """
    # Generate configuration files
    routinator_conf = configuration_files.gen_routinator_conf()
    krill_conf = configuration_files.gen_krill_conf(address_krill)
    haproxy_cfg = configuration_files.gen_haproxy_cfg(address_krill)
    rpki_exceptions = configuration_files.gen_rpki_exception()
    resolv_conf = [
        "nameserver 8.8.8.8"
    ]
    
    # Define all krill directories
    krill_krill_directory = f"lab_{input_file}/krill/etc/krill"
    haproxy_krill_directory = f"lab_{input_file}/krill/etc/haproxy"
    root_krill_directory = f"lab_{input_file}/krill/root"
    ca_certificates_krill_directory = f"lab_{input_file}/krill/usr/local/share/ca-certificates"
    certs_krill_directory = f"lab_{input_file}/krill/etc/ssl/certs"
    ssl_krill_directory = f"lab_{input_file}/krill/var/krill/data/ssl"
    
    for as_number in routers:
        # Define all router directories
        certificates_dir = f"lab_{input_file}/certificates"
        frr_directory = f"lab_{input_file}/router{as_number}/etc/frr"
        root_directory = f"lab_{input_file}/router{as_number}/root"
        ca_certificates_directory = f"lab_{input_file}/router{as_number}/usr/local/share/ca-certificates"
        certs_directory = f"lab_{input_file}/router{as_number}/etc/ssl/certs"
        etc_directory = f"lab_{input_file}/router{as_number}/etc"

        vtysh_conf = [
            "service integrated-vtysh-config",
            f"hostname router{as_number}-frr"
        ]

        # Check if the router uses FRRouting
        if routers[as_number].get_image() == image_frr:
            directories = [frr_directory, etc_directory]
            for directory in directories:
                if not os.path.exists(directory):
                    os.makedirs(directory)  # Create the directory (and any intermediate directories)

            # Add frr.conf and daemons files to the container
            routers[as_number].create_file_from_path(os.path.join(frr_directory, "frr.conf"), "/etc/frr/frr.conf")
            routers[as_number].create_file_from_path(os.path.join(frr_directory, "daemons"), "/etc/frr/daemons")
            routers[as_number].create_file_from_list(lines=vtysh_conf, dst_path="/etc/frr/vtysh.conf")
            write_file_in_path(vtysh_conf, "vtysh.conf", frr_directory)
            # Add resolv.conf file for nameserver resolution
            routers[as_number].create_file_from_list(lines=resolv_conf, dst_path="/etc/resolv.conf")
            write_file_in_path(resolv_conf, "resolv.conf", etc_directory)

        # Check if the router uses Routinator
        if routers[as_number].get_image() == image_routinator:
            directories = [frr_directory, etc_directory, root_directory, ca_certificates_directory, certs_directory]
            for directory in directories:
                if not os.path.exists(directory):
                    os.makedirs(directory)  # Create the directory (and any intermediate directories)

            # Add frr.conf and daemons files to the container
            routers[as_number].create_file_from_path(os.path.join(frr_directory, "frr.conf"), "/etc/frr/frr.conf")
            routers[as_number].create_file_from_path(os.path.join(frr_directory, "daemons"), "/etc/frr/daemons")
            routers[as_number].create_file_from_list(lines=vtysh_conf, dst_path="/etc/frr/vtysh.conf")
            write_file_in_path(vtysh_conf, "vtysh.conf", frr_directory)
            # Add .routinator.conf file to the container
            routers[as_number].create_file_from_list(lines=routinator_conf, dst_path="/root/.routinator.conf")
            write_file_in_path(routinator_conf, ".routinator.conf", root_directory)
            # Add rpki_exceptions.json file to the container
            routers[as_number].create_file_from_list(lines=rpki_exceptions, dst_path="/root/rpki_exceptions.json")
            write_file_in_path(rpki_exceptions, "rpki_exceptions.json", root_directory)
            # Add certificates
            routers[as_number].create_file_from_path(os.path.join(certificates_dir, "root.crt"), "/usr/local/share/ca-certificates/root.crt")
            copy_file(os.path.join(certificates_dir, "root.crt"), ca_certificates_directory, "root.crt")
            routers[as_number].create_file_from_path(os.path.join(certificates_dir, "krill.includesprivatekey.pem"), "/etc/ssl/certs/cert.includesprivatekey.pem")
            copy_file(os.path.join(certificates_dir, "krill.includesprivatekey.pem"), certs_directory, "cert.includesprivatekey.pem")
            # Add resolv.conf file for nameserver resolution
            routers[as_number].create_file_from_list(lines=resolv_conf, dst_path="/etc/resolv.conf")
            write_file_in_path(resolv_conf, "resolv.conf", etc_directory)

    # Build all krill directories
    krill_directories = [
        krill_krill_directory,
        haproxy_krill_directory,
        root_krill_directory,
        ca_certificates_krill_directory,
        certs_krill_directory,
        ssl_krill_directory
        ]
    
    for directory in krill_directories:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Add configuration files for the Krill server
    krill.create_file_from_list(lines=krill_conf, dst_path="/etc/krill/krill.conf")
    write_file_in_path(krill_conf,"krill.conf",krill_krill_directory)
    krill.create_file_from_list(lines=haproxy_cfg, dst_path="/etc/haproxy/haproxy.cfg")
    write_file_in_path(haproxy_cfg,"haproxy.cfg",haproxy_krill_directory)
    krill.create_file_from_list(lines=rpki_exceptions, dst_path="/root/rpki_exceptions.json")
    write_file_in_path(rpki_exceptions,"rpki_exceptions.json",root_krill_directory)

    # Add certificates for Krill
    krill.create_file_from_path(os.path.join(certificates_dir, "root.crt"), "/usr/local/share/ca-certificates/root.crt")
    copy_file(os.path.join(certificates_dir, "root.crt"),ca_certificates_krill_directory,"root.crt")
    krill.create_file_from_path(os.path.join(certificates_dir, "krill.includesprivatekey.pem"), "/etc/ssl/certs/cert.includesprivatekey.pem")
    copy_file(os.path.join(certificates_dir, "krill.includesprivatekey.pem"),certs_krill_directory,"cert.includesprivatekey.pem")
    krill.create_file_from_path(os.path.join(certificates_dir, "krill.crt"), "/var/krill/data/ssl/cert.pem")
    copy_file(os.path.join(certificates_dir, "krill.crt"),ssl_krill_directory,"cert.pem")
    krill.create_file_from_path(os.path.join(certificates_dir, "krill.key"), "/var/krill/data/ssl/key.pem")
    copy_file(os.path.join(certificates_dir, "krill.key"),ssl_krill_directory,"key.pem")

    return

'''MAIN'''

# Check if the state file exists
state_file = "state.json"
# Load configuration file
config_file = "config.json"  # Name of the configuration file
config = load_config(config_file)

# Read values from the configuration file
relations_file = config.get("relations_file", None)
specified_as = config.get("specified_as", None)
show_statistics = config.get("show_statistics_ccone", False)
random_configuration = config.get("random_configuration", False)
adoption_rpki = config.get("adoption_rpki", 0)
adoption_collector = config.get("adoption_collector_peer", 0)
prefer_customer = config.get("prefer_customer", False)
invalid_prefixes_in_bgp_table = config.get("invalid_prefixes_in_bgp_table", False)

if not os.path.exists(state_file):

    if not os.path.exists(config_file):
        print(f"Error: configuration file '{config_file}' does not exist.")
        exit(1)

    # Validate configuration values
    if not os.path.exists(relations_file):
        print(f"Error: relations file '{relations_file}' does not exist.")
        exit(1)

    if not (0 <= adoption_rpki <= 100):
        print("Error: 'adoption_rpki' must be a percentage value between 0 and 100.")
        exit(1)

    if not (0 <= adoption_collector <= 100):
        print("Error: 'adoption_collector_peer' must be a percentage value between 0 and 100.")
        exit(1)

    # Load or generate the graph
    graph_file = "as_graph.json"
    if not os.path.exists(graph_file):
        parse_as_graph.parse(relations_file, graph_file)

    with open(graph_file, "r") as infile:
        graph = json.load(infile)

    # Get a valid node
    specified_as = get_valid_node_from_config_or_prompt(graph, specified_as)

    # Create the customer cone
    input_file, customer_cone_dict = customer_cone.create_specified_customer_cone(graph, specified_as)
    print("Customer Cone successfully created and saved in 'customer_cone.json'")

    if show_statistics:
        file_statistics_output = "statistics_customer_cone.json"
        statistics_customer_cone.save_statistics_to_json(customer_cone_dict, specified_as, file_statistics_output)

    # Save the current state to a file
    with open(state_file, "w") as f:
        json.dump({"input_file": input_file}, f)

else:
    # If the state file exists, load it
    with open(state_file, "r") as f:
        state = json.load(f)
        input_file = state["input_file"]

# Load the topology
with open(input_file, "r") as f:
    topology = json.load(f)

start_configuration = {
    "rpki_nodes": [],
    "collector_nodes": [],
    "hacker_node": [],
    "victim_node": []
}

if random_configuration:
    start_configuration = generate_nodes(topology, adoption_rpki, adoption_collector)

# Run the Dash app to select RPKI and COLLECTOR nodes
app.run_dash_app(topology, start_configuration)

# After running the Dash App, delete the state file to restart
if os.path.exists(state_file):
    os.remove(state_file)

# Wait for the flag file to be created
while not os.path.exists("terminate.flag"):
    time.sleep(1)

# Read saved node data from JSON
with open("saved_nodes.json", "r") as f:
    saved_data = json.load(f)
    rpki_nodes = saved_data.get("rpki_nodes", [])
    collector_nodes = saved_data.get("collector_nodes", [])
    hacker_node = saved_data.get("hacker_node", [])[0]
    victim_node = saved_data.get("victim_node", [])[0]

# Remove the flag and JSON files
os.remove("terminate.flag")

print(f"Red nodes (RPKI): {rpki_nodes}")
print(f"BlackCircle nodes (Collector): {collector_nodes}")
print(f"Red node (Hacker): {hacker_node}")
print(f"Green node (Victim): {victim_node}")

# Start the Kathara lab
# Create Lab and Logger
logger = logging.getLogger("Kathara")
logger.setLevel(logging.INFO)
logger.info("Creating Lab BGP Announcement...")
lab = Lab("BGP Announcement")

address_router_to_krill = "115.115.115.1"  # IP address of the router connected to Krill
address_krill = "115.115.115.2"  # IP address of Krill
prefix_lan_krill = "115.115.115.0/24"  # LAN prefix for connection to Krill

# Docker images
image_frr = "kathara/frr3"
image_routinator = "kathara/routinator3"
image_krill = "kathara/krill3"

# Extract file name without path and extension
input_file_name = os.path.splitext(os.path.basename(input_file))[0]

# Ensure the '/lab_...' directory exists
dir_lab = f"lab_{os.path.splitext(input_file_name)[0]}"
os.makedirs(dir_lab, exist_ok=True)

# Function to modify the topology file by adding 'collector' and 'rpki' attributes
topology_rpki_coll = modify_topology_rpki(topology, rpki_nodes, collector_nodes)
# Save the updated topology to a new file
output_topology = f"{dir_lab}/topology_rpki_coll.json"
with open(output_topology, "w") as f:
    json.dump(topology_rpki_coll, f, indent=4)

# Dynamically create routers and links
routers, krill, dict_collision_domain = lab_collision_domain.create_routers_and_links(
    lab, image_frr, image_routinator, image_krill, topology_rpki_coll, input_file_name
)
output_collision = f"{dir_lab}/Collision_domains.json"
with open(output_collision, "w") as f:
    json.dump(dict_collision_domain, f, indent=4)

# Create a dictionary for each AS with all its links and internal LANs
neighbor_dict = neighbor_dictionary.create_neighbor_dictionary(topology_rpki_coll)
output_neighbor_dict = f"{dir_lab}/neighbor_dict.json"
with open(output_neighbor_dict, "w") as f:
    json.dump(neighbor_dict, f, indent=4)

# Create the attack.sh file where a malicious actor announces the victim's internal LAN
dir_shared = f"{dir_lab}/shared"
os.makedirs(dir_shared, exist_ok=True)
path_input_attack = f"{dir_shared}/attack.sh"
attack_strings = attack.create_file_attack(hacker_node, victim_node, neighbor_dict)
write_file_in_path(attack_strings, "attack.sh", dir_shared)

# Dynamically generate router startup configurations
roa_list = roa_entry.generate_roa_entries(neighbor_dict, prefix_lan_krill)
startup.startup_routers(lab, neighbor_dict, input_file_name, dict_collision_domain, address_krill, address_router_to_krill, roa_list)

# Create frr.conf files for each router
frr.create_frr(neighbor_dict, input_file_name, prefix_lan_krill, prefer_customer, invalid_prefixes_in_bgp_table)

# Create daemons files in the daemons folder
daemons.create_daemons_file(neighbor_dict, input_file_name)

# Generate certificates for RPKI-enabled routers
gen_certificates(input_file_name)

# Move configuration files to their appropriate locations
move_configurations_file(routers, krill, address_krill, image_frr, image_routinator, image_krill, input_file_name)

# Deploy the lab with all machines
Kathara.get_instance().deploy_lab(lab)

# Initialize Docker client
client = docker.from_env(timeout=600)
container_count = len(neighbor_dict)

# Ensure BGP convergence and execute the attack
bgp_convergence.ensure_bgp_convergence_and_execute_attack(client, container_count, hacker_node, path_input_attack)

# Wait for BGP convergence
bgp_convergence.wait_for_convergence(client, container_count)

# Get victim's LAN and prefix
lan_victim = neighbor_dict.get(f"{victim_node}", {}).get("internalLan", None)
prefix_base_victim = ".".join(lan_victim.split(".")[:3]) + ".0"

# Perform BGP path checks
bgp_aspath_check.bgp_check(hacker_node, victim_node, prefix_base_victim)