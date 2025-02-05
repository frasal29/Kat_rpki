import os

# Function to create FRR configuration files
def create_frr(neighbor_dict, input_file, prefix_lan_krill, prefer_customer, invalid_prefixes_in_bgp_table):
    """
    Creates FRR configuration files for each router.

    :param neighbor_dict: Dictionary containing neighbor configurations.
    :param input_file: Name of the input file.
    :param prefix_lan_krill: LAN prefix for the Krill server.
    :param prefer_customer: Boolean flag to prefer customer routes.
    :param invalid_prefixes_in_bgp_table: Boolean flag to allow invalid prefixes in the BGP table.
    """
    isFirstRouter = True  # Flag to identify the first router, which is directly connected to Krill
    for as_number, details in neighbor_dict.items():
        # Ensure the '/output/lab_.../startup' directory exists
        frr_conf_directory = f"output/lab_{os.path.splitext(input_file)[0]}/router{as_number}/etc/frr"
        os.makedirs(frr_conf_directory, exist_ok=True)

        # Name of the configuration file for the current router
        filename = f"{frr_conf_directory}/frr.conf"
        isRPKI = details.get("rpki") == "yes"  # Check if the router uses RPKI
        isCollector = details.get("coll") == "yes"  # Check if the router is a collector

        # Create the content for the configuration file
        config_lines = [
            "!",
            "! FRRouting configuration file",
            "!",
            "password zebra",
            "enable password zebra",
            "!",
            "log file /var/log/frr/frr.log",
            "!",
            "! BGP CONFIGURATION",
            "!",
            "debug bgp keepalives",  # Debugging for BGP keepalives
            "debug bgp updates in",  # Debugging for incoming BGP updates
            "debug bgp updates out"  # Debugging for outgoing BGP updates
        ]

        # Add RPKI debug if the router uses RPKI
        if isRPKI:
            config_lines.append("debug rpki")

        # Add dump configuration if the router is a collector
        if isCollector:
            config_lines.append("!")
            config_lines.append(f"dump bgp all-et /shared/dumps/dump-router{as_number}")
            config_lines.append("!")

        # Add RPKI configuration if the router uses RPKI
        if isRPKI:
            config_lines.extend([
                "!",
                "! RPKI CONFIGURATION",
                "!",
                "rpki",
                "rpki polling_period 10",  # Polling interval in seconds
                "rpki retry_interval 10",  # Retry interval in seconds
                "rpki revalidate_interval 5",  # Revalidation interval in seconds
                "rpki cache 127.0.0.1 3323 preference 1",  # RPKI cache server address and port
                "exit",
                "!"
            ])

        internal_lan = details["internalLan"]  # Get the internal LAN of the router

        config_lines.extend([
            "!",
            f"router bgp {as_number}",
            "no bgp ebgp-requires-policy",  # Disable the requirement for export policy
            "no bgp network import-check",  # Disable import check for the network command
            "!",
            f"bgp router-id {internal_lan}"  # Set the router ID to the internal LAN address
        ])

        # Add the internal LAN to the BGP configuration
        internal_lan_base = ".".join(internal_lan.split(".")[:3]) + ".0"  # Replace the last block with "0"
        prefix_internal_lan = f"{internal_lan_base}/24"
        config_lines.append(f"network {prefix_internal_lan}")

        # If this is the first router, announce the Krill LAN
        if isFirstRouter:
            config_lines.append(f"network {prefix_lan_krill}")
            isFirstRouter = False
        
        config_lines.append("!")

        prefix_lists = {"p2p": [], "p2c": [], "c2p": []}  # To store prefixes for each relationship type

        # Add neighbor configurations
        for rel_type in ["p2p", "p2c", "c2p"]:
            for peer in details[rel_type]:
                for as_peer, prefix_peer in peer.items():
                    config_lines.append(f"neighbor {prefix_peer} remote-as {as_peer}")
                    config_lines.append(f"neighbor {prefix_peer} description Router {rel_type}")

                    # Add the peer AS to the corresponding prefix list
                    if rel_type == "p2p":
                        prefix_lists["p2p"].append(prefix_peer)
                        config_lines.append(f"neighbor {prefix_peer} local-role peer")
                    elif rel_type == "p2c":
                        prefix_lists["c2p"].append(prefix_peer)
                        config_lines.append(f"neighbor {prefix_peer} local-role provider")
                    elif rel_type == "c2p":
                        prefix_lists["p2c"].append(prefix_peer)
                        config_lines.append(f"neighbor {prefix_peer} local-role customer")
                    
                    # Add route-map configurations based on RPKI and customer preference
                    if isRPKI and prefer_customer:
                        config_lines.append(f"neighbor {prefix_peer} route-map rpkiPreferCust in")
                    elif prefer_customer and not isRPKI:
                        config_lines.append(f"neighbor {prefix_peer} route-map preferCustomer in")
                    elif isRPKI and not prefer_customer:
                        config_lines.append(f"neighbor {prefix_peer} route-map onlyRpki in")

                    config_lines.append("!")

        # Create prefix-lists for each relationship type
        if prefer_customer:
            seq = 10  # Initialize sequence number
            for rel_type, prefixes in prefix_lists.items():
                for prefix in prefixes:
                    config_lines.append(f"ip prefix-list {rel_type.upper()} seq {seq} permit {prefix}/32")
                    seq += 10  # Increment sequence number
                config_lines.append("!")

        config_lines.extend([
            "ip prefix-list ANY permit 0.0.0.0/0 le 32",
            "route-map correct_src permit 1",
            "match ip address prefix-list ANY",
            f"set src {internal_lan}",
            "ip protocol bgp route-map correct_src",
            "!"
        ])

        # Add route-maps for local preference based on RPKI and prefer customer
        if isRPKI and prefer_customer:
            config_lines.extend([
                "!",
                "! Route-maps for Local Preference based on next-hop and on RPKI",
                "route-map rpkiPreferCust permit 10",
                "  match rpki valid",
                "  match ip next-hop prefix-list C2P",
                "  set local-preference 500",
                "!",
                "route-map rpkiPreferCust permit 20",
                "  match rpki valid",
                "  match ip next-hop prefix-list P2P",
                "  set local-preference 450",
                "!",
                "route-map rpkiPreferCust permit 30",
                "  match rpki valid",
                "  match ip next-hop prefix-list P2C",
                "  set local-preference 400",
                "!",
                "route-map rpkiPreferCust permit 40",
                "  match rpki notfound",
                "  match ip next-hop prefix-list C2P",
                "  set local-preference 350",
                "!",
                "route-map rpkiPreferCust permit 50",
                "  match rpki notfound",
                "  match ip next-hop prefix-list P2P",
                "  set local-preference 300",
                "!",
                "route-map rpkiPreferCust permit 60",
                "  match rpki notfound",
                "  match ip next-hop prefix-list P2C",
                "  set local-preference 250",
                "!"
                ])
                
            if invalid_prefixes_in_bgp_table:
                config_lines.extend([
                    "route-map rpkiPreferCust permit 70",
                    "  match rpki invalid",
                    "  match ip next-hop prefix-list C2P",
                    "  set local-preference 30",
                    "!",
                    "route-map rpkiPreferCust permit 80",
                    "  match rpki invalid",
                    "  match ip next-hop prefix-list P2P",
                    "  set local-preference 20",
                    "!",
                    "route-map rpkiPreferCust permit 90",
                    "  match rpki invalid",
                    "  match ip next-hop prefix-list P2C",
                    "  set local-preference 10",
                    "!",
                    "route-map rpkiPreferCust permit 100",
                    "!"
                    ])
            else:
                config_lines.extend([
                    "route-map rpkiPreferCust deny 70",
                    "  match rpki invalid",
                    "!",
                    "route-map rpkiPreferCust permit 80",
                    "!"
                    ])

        # Add route-maps for local preference based only on prefer customer
        elif prefer_customer and not isRPKI:
            config_lines.extend([
                "route-map preferCustomer permit 10",
                "   match ip next-hop prefix-list C2P",
                "   set local-preference 350",
                "!",
                "route-map preferCustomer permit 20",
                "   match ip next-hop prefix-list P2P",
                "   set local-preference 300",
                "!",
                "route-map preferCustomer permit 30",
                "   match ip next-hop prefix-list P2C",
                "   set local-preference 250",
                "!",
                "route-map preferCustomer permit 40",
                "!"
                ])

        # Add route-maps for local preference based only on RPKI
        elif isRPKI and not prefer_customer:
            config_lines.extend([
                "!",
                "! Route-maps for Local Preference based only on RPKI",
                "route-map onlyRpki permit 10",
                "  match rpki valid",
                "  set local-preference 500",
                "!",
                "route-map onlyRpki permit 20",
                "  match rpki notfound",
                "  set local-preference 200",
                "!"
                ])
            
            if invalid_prefixes_in_bgp_table:
                config_lines.extend([
                    "route-map onlyRpki permit 30",
                    "  match rpki invalid",
                    "  set local-preference 10",
                    "!",
                    "route-map onlyRpki permit 40",
                    "!"
                    ])
            else:
                config_lines.extend([
                    "route-map onlyRpki deny 30",
                    "  match rpki invalid",
                    "!",
                    "route-map onlyRpki permit 40",
                    "!"
                    ])

        # Write the configuration file
        with open(filename, "w") as f:
            f.write("\n".join(config_lines))
    return