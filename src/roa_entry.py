def generate_roa_entries(as_dict, prefix_lan_krill):
    """
    Generates a list of strings for ROAs based on the AS dictionary.

    :param as_dict: Dictionary containing AS details.
    :param prefix_lan_krill: The LAN prefix for the Krill server.
    :return: List of strings formatted for ROAs.
    """
    roa_entries = []

    first_router = True  # Flag to check if the first router is processed
    for as_number, details in as_dict.items():
        # Check if the "rpki" attribute is set to "yes"
        # In this implementation, all routers using RPKI have their own valid route (by convention)
        if details.get("rpki") == "yes":
            if first_router:  # If the first router is RPKI-enabled, add the LAN to Krill as a ROA
                roa_entry_krill = f"{prefix_lan_krill} => {as_number}"
                roa_entries.append(roa_entry_krill)
                first_router = False
            
            internal_lan = details.get("internalLan")
            if internal_lan:
                # Modify the last byte of the IP to "0"
                lan_parts = internal_lan.split('.')
                lan_parts[-1] = "0"
                formatted_lan = '.'.join(lan_parts) + "/24"

                # Construct the ROA string and add it to the list
                roa_entry = f"{formatted_lan} => {as_number}"
                roa_entries.append(roa_entry)
    
    return roa_entries
