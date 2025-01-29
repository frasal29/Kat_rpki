import os

def startup_routers(lab, neighbor_dict, input_file, dict_collision_domain, address_krill, address_router_to_krill, roa_list):
    """
    Configures startup files for routers based on the topology.

    :param lab: Kathara Lab object.
    :param neighbor_dict: Dictionary containing neighbor details.
    :param dict_collision_domain: Dictionary mapping routers to associated links.
    :param input_file: Name of the input file.
    :param address_krill: LAN address used for the Krill server.
    :param address_router_to_krill: Address of the router connected to the Krill server.
    :param roa_list: List of ROAs (Route Origin Authorizations) to be applied.
    :return: None
    """

    # Generate startup files using neighbor_dict
    print("\nStarting router configuration...")
    for as_number, details in neighbor_dict.items():
        print(f"Configuring startup file for AS {as_number}...")

        # ROUTER CONFIGURATIONS

        lista_stringhe_net = []  # Complete list of networks for an AS
        router_name = f"router{as_number}"

        if router_name in dict_collision_domain:
            links = dict_collision_domain[router_name]
            internal_index = None  # Variable to track the internal LAN index
            krill_index = None  # Variable to track the Krill LAN index
            for idx, link in enumerate(links):
                if "to" in link:  # Link between routers
                    peer_as = link.split("to")[1] if link.split("to")[0] == str(as_number) else link.split("to")[0]
                    
                    if peer_as in neighbor_dict[as_number]["asLan"]:
                        net = neighbor_dict[as_number]["asLan"][peer_as]
                        stringa_net = f"ip addr add {net}/30 dev eth{idx}"
                        lista_stringhe_net.append(stringa_net)
                elif as_number in link:
                    # Identify the index of the internal LAN
                    internal_index = idx

                elif "krill" in link:
                    # Identify the index of the LAN for Krill
                    krill_index = idx
            
            # Configure the internal LAN using the identified index
            if internal_index is not None:
                internal_lan = neighbor_dict[as_number]["internalLan"]
                stringa_internal_lan = f"ip addr add {internal_lan}/24 dev eth{internal_index}"
                lista_stringhe_net.append(stringa_internal_lan)

            # Configure the LAN for Krill using the identified index
            if krill_index is not None:
                stringa_krill_lan = f"ip addr add {address_router_to_krill}/24 dev eth{krill_index}"
                lista_stringhe_net.append(stringa_krill_lan)
        
        # If the router is a collector, create the folder if it does not exist
        if details.get("coll") == "yes":
            lista_stringhe_net.extend([
                "mkdir -p /shared/dumps",
                "chmod 777 /shared",
                "chmod 777 /shared/dumps"
            ])

        # Check the value of "rpki"
        if details.get("rpki") == "no":
            # Add basic commands to the list
            lista_stringhe_net.append("systemctl start frr")

        elif details.get("rpki") == "yes":
            # Configuration for "rpki": "yes"
            lista_stringhe_net.extend([
                "update-ca-certificates --fresh",
                f"echo \"{address_krill} rpki-server.org\" >> /etc/hosts",
                "mkdir -p /root/.rpki-cache/tals/",
                "mkdir -p /root/.rpki-cache/repository",
                "systemctl start frr",
                f"wget --bind-address={internal_lan} https://rpki-server.org:3000/ta/ta.tal -P /root/.rpki-cache/tals/",
                "while true; do",
                f"    wget --bind-address={internal_lan} https://rpki-server.org:3000/ta/ta.tal -P /root/.rpki-cache/tals/ 2>&1 | grep \"HTTP\" | grep -q \"200\"",
                "    if [ $? -eq 0 ]; then",
                "        echo \"Correct response received\"",
                "        break",
                "    else",
                "        echo \"Request not successful, trying again...\"",
                "    fi",
                "    sleep 1",
                "done",
                f"routinator --rrdp-local-addr {internal_lan} --rrdp-root-cert=/usr/local/share/ca-certificates/root.crt -c root/.routinator.conf -v server &",
                "vtysh -c \"rpki start\""
            ])

            # BGP table updates
            lista_stringhe_net.extend([
                f"MAX_ROUTES={len(neighbor_dict)+1}",
                "INTERVAL=40",
                "PREVIOUS_BGP_OUTPUT=\"\"",
                "VALID_ROUTES_DETECTED=False",
                "MAX_ITERATIONS=15",
                "while true; do",
                "    # Check the number of routes with flag N, V o I",
                "    ROUTE_COUNT=$(vtysh -c \"show ip bgp\" | grep -c \"^\\s*\\(N\\|V\\|I\\)\\*\")",
                "    CURRENT_BGP_OUTPUT=$(vtysh -c \"show ip bgp\")",
                "    if [ \"$ROUTE_COUNT\" -gt 0 ]; then",
                "        VALID_ROUTES_DETECTED=true",
                "    fi",
                "    if [ \"$VALID_ROUTES_DETECTED\" = true ]; then",
                "        echo \"Current route count: $ROUTE_COUNT\"",
                "        # Verify if the route count has reached the expected limit",
                "        if [ \"$ROUTE_COUNT\" -ge \"$MAX_ROUTES\" ]; then",
                "            echo \"Route count ($ROUTE_COUNT) has reached or exceeded the limit ($MAX_ROUTES). Checking for changes in the content.\"",
                "            # Check if the content of the BGP table has changed",
                "            if [ \"$CURRENT_BGP_OUTPUT\" != \"$PREVIOUS_BGP_OUTPUT\" ]; then",
                "                echo \"BGP table content has changed. Clearing BGP sessions.\"",
                "                for ((i=1; i<=MAX_ITERATIONS; i++)); do",
                "                    echo \"Attempt #$i: clear ip bgp * soft\"",
                "                    vtysh -c \"clear ip bgp * soft\"",
                "                    sleep \"$INTERVAL\"",
                "                    CURRENT_BGP_OUTPUT=$(vtysh -c \"show ip bgp\")",
                "                    if [ \"$CURRENT_BGP_OUTPUT\" == \"$PREVIOUS_BGP_OUTPUT\" ]; then",
                "                        echo \"BGP table no longer changing after $i attempts. Done.\"",
                "                        break",
                "                    fi",
                "                done",
                "            else",
                "                echo \"BGP table content has not changed. No action needed.\"",
                "            fi",
                "            PREVIOUS_BGP_OUTPUT=\"$CURRENT_BGP_OUTPUT\"",
                "        else",
                "            echo \"Route count ($ROUTE_COUNT) is below the expected limit ($MAX_ROUTES).\"",
                "            vtysh -c \"clear ip bgp * soft\"",
                "        fi",
                "    else",
                "        echo \"Waiting for valid routes to appear (N, V, I).\"",
                "    fi",
                "    sleep \"$INTERVAL\"",
                "done"
            ])

        # Write the configuration file to the lab directory
        lab.create_file_from_list(
            lista_stringhe_net,
            f"router{as_number}.startup"
        )

        # Ensure the '/lab_.../startup' directory exists
        startup_directory = f"lab_{os.path.splitext(input_file)[0]}"
        os.makedirs(startup_directory, exist_ok=True)

        # Also write the file in the 'startup' folder
        startup_file_path = os.path.join(startup_directory, f"router{as_number}.startup")
        with open(startup_file_path, "w") as startup_file:
            startup_file.write("\n".join(lista_stringhe_net))

    # Configuration for Krill
    lista_stringhe_krill = [
        f"ip addr add {address_krill}/24 dev eth0",
        f"ip route add default via {address_router_to_krill}",
        "update-ca-certificates --fresh",
        f"echo \"{address_krill} rpki-server.org\" >> /etc/hosts",
        "",
        "sed -i 's/\\r$//' /etc/init.d/krill-start",
        "sed -i 's/\\r$//' /etc/init.d/krill-stop",
        "",
        "# Start HAProxy",
        "service haproxy start",
        "",
        "# Start Krill",
        "/etc/init.d/krill-start",
        "krillc health > /dev/null 2>&1",
        "while [ $? -ne 0 ]",
        "do",
        "    sleep 1",
        "    krillc health > /dev/null 2>&1",
        "done",
        "",
        "# Configure CA",
        "CA=\"kathara-ca\"",
        "krillc add --ca $CA",
        "krillc repo request --ca $CA > /tmp/publisher_request.xml",
        "krillc pubserver publishers add --publisher $CA --request /tmp/publisher_request.xml > /tmp/repository_response.xml",
        "krillc repo configure --ca $CA --format text --response /tmp/repository_response.xml",
        "krillc parents request --ca $CA > /tmp/myid.xml",
        "krillc children add --ca ta --child $CA --asn \"AS0-65535\" --ipv4 \"0.0.0.0/0\" --request /tmp/myid.xml > /tmp/parent_response.xml",
        "krillc parents add --ca $CA --parent ta --response /tmp/parent_response.xml",
        "",
        "# Add ROAs dynamically",
        f'krillc roas update --ca $CA --add "0.0.0.0/0 => 0" > /dev/null 2>&1',
        "while [ $? -ne 0 ]",
        "do",
        "    sleep 1",
        f'    krillc roas update --ca $CA --add "0.0.0.0/0 => 0" > /dev/null 2>&1',
        "done",
        f'krillc roas update --ca $CA --remove "0.0.0.0/0 => 0"'
    ]
    for roa in roa_list:
        lista_stringhe_krill.append(f'krillc roas update --ca $CA --add "{roa}"')
    
    # Write the Krill configuration file to the lab directory
    lab.create_file_from_list(
        lista_stringhe_krill,
        "krill.startup"
    )

    # Also write the file in the 'startup' folder
    startup_file_krill_path = os.path.join(startup_directory, "krill.startup")
    with open(startup_file_krill_path, "w") as startup_krill:
        startup_krill.write("\n".join(lista_stringhe_krill))

    return
