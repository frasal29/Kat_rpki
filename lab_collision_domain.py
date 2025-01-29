import os

def create_routers_and_links(lab, image_frr, image_routinator, image_krill, topology, input_file):
    """
    Creates routers and links based on the topology defined in the JSON file.

    :param lab: Kathara Lab object.
    :param image_frr: Docker image for routers without RPKI.
    :param image_routinator: Docker image for routers with RPKI.
    :param image_krill: Docker image for the Krill server.
    :param topology: Dictionary containing the topology.
    :param input_file: Name of the input file.
    :return: A tuple containing the routers dictionary, the Krill server instance, and the router-links map.
    """
    routers = {}
    krill = None  # Instance of the Krill server
    links = set()  # Tracks created links to avoid duplicates
    router_links_map = {}  # Dictionary mapping router names to their links

    # Creating routers
    for as_number, details in topology.items():
        # Check the value of the "rpki" attribute
        if details.get("rpki") == "yes":
            # If the router uses RPKI, create it with the Routinator image
            routers[as_number] = lab.new_machine(
                name=f"router{as_number}",
                image=image_routinator
                #bridged=True
            )
        else:
            # If the router does not use RPKI, create it with the FRRouting image
            routers[as_number] = lab.new_machine(
                name=f"router{as_number}",
                image=image_frr
                #bridged=True
            )
        
        # Initialize the router's link map with an empty list
        router_links_map[routers[as_number].name] = []

    # Creating the Krill server
    name_krill = "krill"
    port_krill = "3500:3000/tcp"  # Optional port mapping
    content_envs = [
        "KRILL_CLI_TOKEN=kathara-secret-token",  # Token for Krill CLI
        "KRILL_TEST=true",  # Enable Krill test mode
        "KRILL_CLI_MY_CA=kathara-ca"  # Specify the CA for Krill CLI
    ]
    
    # Create the Krill server instance
    krill = lab.new_machine(
        name=name_krill,
        image=image_krill,
        #port=port_krill,
        #bridged=True,
        envs=content_envs
    )
    
    # Creating links
    first_router = None  # Variable to track the first router
    is_first_router = True  # Flag to identify the first router

    for as_number, connections in topology.items():
        # Save the first router for the Krill link
        if is_first_router:
            first_router = routers[as_number]
            is_first_router = False  # Disable the flag after processing the first router

        # Iterate over all relationship types ('p2p', 'p2c', 'c2p')
        for rel_type in ['p2p', 'p2c', 'c2p']:
            if rel_type in connections:  # Check if the relationship type exists
                peers = connections[rel_type]
                for peer in peers:
                    # Define direct and reverse link names
                    link_name = f"{as_number}to{peer}"
                    reverse_link_name = f"{peer}to{as_number}"

                    # Check if the reverse link already exists
                    if reverse_link_name in links:
                        # Use the reverse link if it already exists
                        link_name = reverse_link_name
                    else:
                        # Create a new link if it does not exist
                        links.add(link_name)

                    # Connect the router to the link
                    lab.connect_machine_to_link(routers[as_number].name, link_name)
                    router_links_map[routers[as_number].name].append(link_name)  # Add the link to the router's map

        # Create and connect the internal LAN link for the router
        link_internal = f"{as_number}"
        lab.connect_machine_to_link(routers[as_number].name, link_internal)
        router_links_map[routers[as_number].name].append(link_internal)  # Add the internal link to the router's map

    # Create the Krill link for the first router
    link_krill_name = "krill"
    lab.connect_machine_to_link(first_router.name, link_krill_name)
    router_links_map[first_router.name].append(link_krill_name)

    # Connect the Krill server to the Krill link
    lab.connect_machine_to_link(krill.name, link_krill_name)

    # Saving the lab configuration to lab.conf
    lab_lines = []
    for as_number, details in topology.items():
        # Determine the correct image for the router
        if details.get("rpki") == "yes":
            image = image_routinator
        else:
            image = image_frr
        name_router = f"router{as_number}"
        router_collision_list = router_links_map[name_router]
        for i, value in enumerate(router_collision_list):
            lab_lines.append(f"{name_router}[{i}]=\"{value}\"")  # Add each link to the router configuration
        lab_lines.append(f"{name_router}[image]=\"{image}\"")
        lab_lines.append("")  # Add a blank line for separation

    # Add the Krill server configuration
    lab_lines.extend([
        f"krill[image]=\"{image_krill}\"",
        f"krill[0]=\"{link_krill_name}\""
        #f"krill[port]=\"{port_krill}\"",
        #"krill[bridged]=true"
    ])
    for line in content_envs:
        lab_lines.append(f"krill[env]=\"{line}\"")  # Add environment variables for Krill

    # Ensure the lab directory exists
    lab_directory = f"lab_{os.path.splitext(input_file)[0]}"
    os.makedirs(lab_directory, exist_ok=True)

    # Write the configuration file to the lab directory
    lab_conf_path = os.path.join(lab_directory, "lab.conf")
    with open(lab_conf_path, "w") as lab_conf_file:
        lab_conf_file.write("\n".join(lab_lines))

    return routers, krill, router_links_map
