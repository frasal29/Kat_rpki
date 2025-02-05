import time
from Kathara.manager.Kathara import Kathara


def execute_command_in_container(machine_name, lab, command):
    """
    Executes a command inside a container.

    :param machine_name: Machine object kathara
    :param lab: Kathara lab instance.
    :param command: Command to execute inside the container.
    :return: Output of the command as a string.
    """
    result, stderr, return_code = Kathara.get_instance().manager.exec(machine_name, command, wait=False, stream=False, lab=lab)
    return result, stderr, return_code


def wait_for_convergence(routers, routers_count, lab, check_interval=5, max_wait_time=600):
    """
    Waits until all routers have at least the expected number of BGP routes,
    and the route tables remain stable for 5 consecutive iterations.

    :param routers: Dictionary of router instances.
    :param routers_count: Expected number of routes per router.
    :param lab: Kathara lab instance.
    :param check_interval: Time interval in seconds between checks.
    :param max_wait_time: Maximum time in seconds to wait for convergence.
    :return: True if convergence is reached, False otherwise.
    """
    print("\nWaiting for route convergence...")
    elapsed = 0
    stable_iterations = 0  # Counter for stable iterations
    previous_routes = {}  # Route count for each router in the previous iteration
    previous_outputs = {}  # "show ip bgp" output for each router in the previous iteration

    while elapsed < max_wait_time:
        all_converged = True  # Indicates if all routers have converged
        current_routes = {}  # Current route count for each router
        current_outputs = {}  # Current "show ip bgp" output for each router

        for machine in routers.values():
            command = ["vtysh", "-c", "show ip bgp"]
            try:
                result, stderr, return_code = execute_command_in_container(machine.name, lab, command)
                if result is not None:
                    result = result.decode('utf-8')
                else:
                    print(f"Errore su {machine.name}: nessun output ricevuto.")
                    all_converged = False  # if there's no output, consider the convergence not reached
                    continue  # Pass to the next router

            except Exception as e:
                print(f"Errore su {machine.name}: {str(e)}")
                all_converged = False  # If there's an exception, consider the convergence not reached
                continue  # Pass to the next router

            routes = result.strip().split("\n")
            current_routes[machine.name] = len(routes)
            current_outputs[machine.name] = result.strip()

            # Check if the router has fewer routes than expected
            if len(routes) < routers_count:
                all_converged = False
                print(f"Convergence not reached: {machine.name} has {len(routes)} routes (expected: {routers_count}).")

        # Check if routes and outputs are unchanged compared to the previous iteration
        for machine_name, current_output in current_outputs.items():
            if machine_name in previous_outputs and current_output != previous_outputs[machine_name]:
                print(f"BGP table content has changed for {machine_name}")

        if previous_routes == current_routes and previous_outputs == current_outputs and all_converged:
            stable_iterations += 1
            print(f"Stable iteration {stable_iterations}/5")
        else:
            stable_iterations = 0  # Reset the counter if there's a variation

        # If the routes and outputs are stable for 5 consecutive iterations
        if stable_iterations >= 5:
            print("Convergence reached!")
            return True

        # Update previous routes and outputs
        previous_routes = current_routes.copy()
        previous_outputs = current_outputs.copy()

        print(f"\nConvergence not yet reached, retrying in {check_interval} seconds...")
        time.sleep(check_interval)
        elapsed += check_interval

    print("Timeout reached: Convergence not achieved.")
    return False


def execute_attack(routers, hacker_router, lab):
    """
    Copies and executes the attack.sh script in a specific container.
    
    :param routers: Dictionary of router instances.
    :param hacker_router: Name of the hacker router.
    :param lab: Kathara lab instance.
    """

    print(f"\nExecuting attack.sh in router {hacker_router}...")
    command = "bash /shared/attack.sh" # Execute the attack script
    machine = routers[hacker_router] 
    execute_command_in_container(machine.name, lab, command) 
    print("Attack executed successfully!")

def ensure_bgp_convergence_and_execute_attack(routers, routers_count, lab, target_container_name):
    """
    Manages the wait for BGP convergence and executes the attack script.

    :param routers: Dictionary of router instances.
    :param routers_count: Number of routers in the lab.
    :param lab: Kathara lab instance.
    :param target_container_name: Name of the target container for the attack.
    """
    print("\nStarting the route convergence phase to execute the attack.")
    print("All containers are running.")

    # Wait for BGP convergence
    if wait_for_convergence(routers, routers_count, lab):
        # Copy and execute the script in the specified container
        execute_attack(routers, target_container_name, lab)
    else:
        print("Error: Convergence was not reached.")