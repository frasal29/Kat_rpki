def create_neighbor_dictionary(topology):
    """
    Creates a dictionary that represents the relationships and LANs for each AS in the topology.

    :param topology: Dictionary representing the network topology.
    :return: A dictionary containing details about neighbors, LANs, and AS relationships.
    """

    def compute_internal_lan(as_number):
        """
        Computes the internal LAN of an AS given its number.

        :param as_number: The Autonomous System (AS) number.
        :return: A formatted string representing the internal LAN.
        """
        as_number_str = str(as_number)
        length = len(as_number_str)

        # Map AS number into first, second, and third blocks based on its length
        if length == 1:
            first_block = as_number_str[0]
            second_block = None
            third_block = None
        elif length == 2:
            first_block = as_number_str[:2]
            second_block = None
            third_block = None
        elif length == 3:
            first_block = as_number_str[:2]
            second_block = as_number_str[2]
            third_block = None
        elif length == 4:
            first_block = as_number_str[:2]
            second_block = as_number_str[2:]
            third_block = None
        elif length == 5:
            first_block = as_number_str[:2]
            second_block = as_number_str[2:4]
            third_block = as_number_str[4]
        elif length == 6:
            first_block = as_number_str[:2]
            second_block = as_number_str[2:4]
            third_block = as_number_str[4:]
        else:
            raise ValueError(f"AS number {as_number} out of range")
        
        # Adjust special cases for each block
        def fix_block(block):
            """
            Fixes the value of a block to handle special cases.

            :param block: The block to adjust.
            :return: The adjusted block value.
            """
            if block is None:
                return '0'
            if block == '0':
                return '110'  # Convert block '0' to '110'
            if len(block) == 1:
                return block  # Return the block as is
            if len(block) == 2 and block[0] == '0':
                return str(100 + int(block[1]))  # Convert '01' → 101, '00' → 100
            return block  # Return the original block for other cases
        
        # Fix blocks and construct the LAN
        first_block = fix_block(first_block)
        second_block = fix_block(second_block)
        third_block = fix_block(third_block)
        
        return f"{first_block}.{second_block}.{third_block}.1"

    # Tracks the current state of assigned LANs
    lan_state = {
        "first_block": 120,
        "second_block": 0,
        "third_block": 0,
        "fourth_block": 0
    }

    def get_next_lan():
        """
        Generates the next available LAN and updates the state.

        :return: A tuple representing the next LAN's IP blocks.
        """
        first = lan_state["first_block"]
        second = lan_state["second_block"]
        third = lan_state["third_block"]
        fourth = lan_state["fourth_block"]

        # Assign the current LAN before updating
        result = first, second, third, fourth
        
        # Update the state of the blocks
        lan_state["fourth_block"] += 4
        if lan_state["fourth_block"] > 252:
            lan_state["fourth_block"] = 0
            lan_state["third_block"] += 1
            if lan_state["third_block"] > 255:
                lan_state["third_block"] = 120
                lan_state["second_block"] += 1
                if lan_state["second_block"] > 255:
                    lan_state["second_block"] = 120
                    lan_state["first_block"] += 1
                    if lan_state["first_block"] > 255:
                        raise ValueError("Exhausted all available LANs!")
        return result

    # Initialize the neighbor dictionary
    neighbor_dictionary = {}

    for as_number, connections in topology.items():
        # Initialize the current AS in the dictionary
        if as_number not in neighbor_dictionary:
            coll = topology[as_number]["collector"]  # Indicates if the AS is a collector
            rpki = topology[as_number]["rpki"]  # Indicates if the AS uses RPKI
            neighbor_dictionary[as_number] = {
                "p2p": [],  # Peer-to-peer relationships
                "p2c": [],  # Provider-to-customer relationships
                "c2p": [],  # Customer-to-provider relationships
                "asLan": {},  # Dictionary of LANs shared with other ASes
                "internalLan": compute_internal_lan(as_number),  # Internal LAN of the AS
                "rpki": rpki,  # RPKI status
                "coll": coll  # Collector status
            }

        for rel_type in ['p2p', 'p2c', 'c2p']:
            if rel_type in connections:
                peers = connections[rel_type]
                for peer in peers:
                    # Initialize the peer AS if it does not exist
                    if peer not in neighbor_dictionary:
                        coll = topology[peer]["collector"]
                        rpki = topology[peer]["rpki"]
                        neighbor_dictionary[peer] = {
                            "p2p": [],
                            "p2c": [],
                            "c2p": [],
                            "asLan": {},
                            "internalLan": compute_internal_lan(peer),
                            "rpki": rpki,
                            "coll": coll
                        }

                    # Skip if a LAN has already been assigned
                    if as_number in neighbor_dictionary[peer]["asLan"]:
                        continue

                    # Configure the dictionary based on the type of relationship
                    if rel_type == "p2p":
                        # Peer-to-peer relationship
                        first, second, third, fourth = get_next_lan()

                        lan_as = f"{first}.{second}.{third}.{fourth+1}"
                        lan_peer = f"{first}.{second}.{third}.{fourth+2}"

                        neighbor_dictionary[as_number]["p2p"].append({peer: lan_peer})
                        neighbor_dictionary[peer]["p2p"].append({as_number: lan_as})
                        # Populate asLan for both ASes
                        neighbor_dictionary[as_number]["asLan"][peer] = lan_as
                        neighbor_dictionary[peer]["asLan"][as_number] = lan_peer

                    elif rel_type == "p2c":
                        # Provider-to-customer relationship
                        first, second, third, fourth = get_next_lan()

                        lan_as = f"{first}.{second}.{third}.{fourth+2}"
                        lan_peer = f"{first}.{second}.{third}.{fourth+1}"
                    
                        neighbor_dictionary[as_number]["p2c"].append({peer: lan_peer})
                        neighbor_dictionary[peer]["c2p"].append({as_number: lan_as})
                        # Populate asLan for both ASes
                        neighbor_dictionary[as_number]["asLan"][peer] = lan_as
                        neighbor_dictionary[peer]["asLan"][as_number] = lan_peer
                        
                    elif rel_type == "c2p":
                        # Customer-to-provider relationship
                        first, second, third, fourth = get_next_lan()

                        lan_as = f"{first}.{second}.{third}.{fourth+1}"
                        lan_peer = f"{first}.{second}.{third}.{fourth+2}"
                    
                        neighbor_dictionary[as_number]["c2p"].append({peer: lan_peer})
                        neighbor_dictionary[peer]["p2c"].append({as_number: lan_as})
                        # Populate asLan for both ASes
                        neighbor_dictionary[as_number]["asLan"][peer] = lan_as
                        neighbor_dictionary[peer]["asLan"][as_number] = lan_peer

    return neighbor_dictionary
