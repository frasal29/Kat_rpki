import time
import subprocess

def get_running_containers(client):
    """
    Returns all running containers, excluding those with '_krill_' in their name.

    :param client: Docker client instance.
    :return: A list of running container objects.
    """
    containers = client.containers.list()
    # Use a copy of the list to avoid issues while iterating
    for container in containers[:]:
        if "_krill_" in container.name:  # Exclude containers with '_krill_' in their name
            containers.remove(container)
    return containers

def execute_command_in_container(container, command):
    """
    Executes a command inside a container.

    :param container: Docker container object.
    :param command: Command to execute inside the container.
    :return: Output of the command as a string.
    """
    exec_result = container.exec_run(command, stdout=True, stderr=True)
    return exec_result.output.decode("utf-8")

def check_routes(container, expected_routes):
    """
    Checks if a container has at least the expected number of BGP routes.

    :param container: Docker container object.
    :param expected_routes: Expected number of BGP routes.
    :return: True if the number of routes is at least expected_routes, False otherwise.
    """
    result = execute_command_in_container(container, "vtysh -c 'show ip bgp'")
    routes = result.strip().split("\n")
    if len(routes) < expected_routes:
        print("Convergence not reached in:", container.name)
        print("Number of routes:", len(routes))
    return len(routes) >= expected_routes

def wait_for_convergence(client, container_count, check_interval=5, max_wait_time=600):
    """
    Waits until all containers have at least the expected number of BGP routes,
    and the route tables remain stable for 5 consecutive iterations.

    :param client: Docker client instance.
    :param container_count: Total number of containers (and expected routes per container).
    :param check_interval: Time interval in seconds between checks.
    :param max_wait_time: Maximum time in seconds to wait for convergence.
    :return: True if convergence is reached, False otherwise.
    """
    print("\nWaiting for route convergence...")
    elapsed = 0
    stable_iterations = 0  # Counter for stable iterations
    previous_routes = {}  # Route count for each container in the previous iteration
    previous_outputs = {}  # "show ip bgp" output for each container in the previous iteration

    while elapsed < max_wait_time:
        containers = get_running_containers(client)
        all_converged = True  # Indicates if all containers have converged
        current_routes = {}  # Current route count for each container
        current_outputs = {}  # Current "show ip bgp" output for each container

        for container in containers:
            # Count the number of routes in the current container
            result = execute_command_in_container(container, "vtysh -c 'show ip bgp'")
            routes = result.strip().split("\n")
            current_routes[container.name] = len(routes)
            current_outputs[container.name] = result.strip()

            # Check if the container has fewer routes than expected
            if len(routes) < container_count:
                all_converged = False
                print(f"Convergence not reached: {container.name} has {len(routes)} routes (expected: {container_count}).")

        # Check if routes and outputs are unchanged compared to the previous iteration
        for container_name, current_output in current_outputs.items():
            if container_name in previous_outputs and current_output != previous_outputs[container_name]:
                # Extract router name from the container name
                parts = container_name.split("router")
                router_name = parts[1].split("_")[0]  # Extract the router name before '_'
                print(f"BGP table content has changed for router {router_name}.")

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

def copy_and_execute_attack(container_name, path_input_attack):
    """
    Copies and executes the attack.sh script in a specific container.

    :param container_name: Name of the target container.
    :param path_input_attack: Path to the attack.sh script.
    """
    # Get the container ID
    container_id = subprocess.check_output(
        f"docker ps -qf \"name={container_name}\"",
        shell=True
    ).decode("utf-8").strip()

    if not container_id:
        raise ValueError(f"Container with name '{container_name}' not found.")

    # Copy the attack.sh script into the container
    print(f"\nCopying attack.sh into the container of router {container_name}...")
    subprocess.run(
        f"docker cp {path_input_attack} {container_id}:/shared/",
        shell=True,
        check=True
    )
    print("attack.sh successfully copied into the hacker container.")

    # Execute the copied script
    print(f"\nExecuting attack.sh in router {container_name}...")
    command = f"docker exec {container_id} bash /shared/attack.sh"
    subprocess.run(command, shell=True, check=True)
    print("Attack executed successfully!")

def ensure_bgp_convergence_and_execute_attack(client, container_count, target_container_name, path_input_attack):
    """
    Manages the wait for BGP convergence and executes the attack script.

    :param client: Docker client instance.
    :param container_count: Total number of containers.
    :param target_container_name: Name of the target container for the attack.
    :param path_input_attack: Path to the attack.sh script.
    """
    print("\nStarting the route convergence phase to execute the attack.")
    print("Waiting for all containers to start...")
    while len(get_running_containers(client)) < container_count:
        print("Not all containers are running, retrying in 10 seconds...")
        time.sleep(10)

    print("All containers are running.")

    # Wait for BGP convergence
    if wait_for_convergence(client, container_count):
        # Copy and execute the script in the specified container
        copy_and_execute_attack(target_container_name, path_input_attack)
    else:
        print("Error: Convergence was not reached.")