import json
import socket
import math
import pathlib
import random
import shutil
import time

from amaze.simu.controllers.control import controller_factory, save, check_types
from amaze.simu.controllers.tabular import TabularController
from amaze.simu.maze import Maze
from amaze.simu.robot import Robot
from amaze.simu.simulation import Simulation
from amaze.simu.types import InputType, OutputType, StartLocation

def handle_client_connection(client_socket):
    try:
        # Check if the client is requesting the agent image
        data = client_socket.recv(1024).decode()
        if data == "request_image":
            # Placeholder: Send "place holder 1" as response
            response = "place holder 1"
            client_socket.sendall(response.encode())

        # Receive maze strings from the client
        maze_data = client_socket.recv(1024).decode()
        maze_strings = json.loads(maze_data)
        print("Received maze strings:", maze_strings)

        # Extract the first maze string
        first_maze_string = maze_strings[0]
        print("First maze string:", first_maze_string)

        # Use the first maze string for training. Only the first one is used as a start.
        # Training is what the user will need to wait on before submitting new mazes.
        train_with_maze_string(first_maze_string)

        # Receive survey answers from the client
        survey_data = client_socket.recv(1024).decode()
        survey_answers = json.loads(survey_data)
        print("Received survey answers:", survey_answers)

        # Send response back to the client
        client_socket.sendall("Data received".encode())

    except Exception as e:
        print("Error:", e)

    finally:
        # Close the client socket
        client_socket.close()

ALPHA = 0.1
GAMMA = 0.5

FOLDER = pathlib.Path("tmp/demos/q_learning/")

def robot_build_data():
    return Robot.BuildData(
        inputs=InputType.DISCRETE,
        outputs=OutputType.DISCRETE,
        control="tabular",
        control_data=dict(
            actions=Simulation.discrete_actions(),
            epsilon=0.1, seed=0
        )
    )

def train_with_maze_string(maze_string):
    # Has been made redundant, the maze data from client side becomes strings.
    # Here, those strings get transformed into data again. Choose one or the other.
    # Also, constructing maze data as done below is incorrect. Check documentation for string specifications.
    start_time = time.time()

    # Construct maze data from the received maze string
    parts = maze_string.split('_')
    seed = int(parts[0][1:])
    size = int(parts[1].split('x')[0])
    unicursive = 'U' in parts[2]
    start = StartLocation(int(parts[3][1]))

    # Train with the extracted parameters
    train_maze_data = Maze.BuildData(
        width=size, height=size,
        unicursive=unicursive,
        start=start,
        seed=seed,  # Include the extracted seed
        p_lure=0.0, p_trap=0.0
    )

    print("Training with maze:", train_maze_data.to_string())
    train_mazes = [
        Maze.generate(train_maze_data.where(start=start))
        for start in StartLocation
    ]

    maze_data = train_maze_data.where(seed=14)
    print("Evaluating with maze:", maze_data.to_string())
    eval_mazes = [
        Maze.generate(maze_data.where(start=start))
        for start in StartLocation
    ]

    robot = robot_build_data()
    policy: TabularController = controller_factory(robot.control,
                                                   robot.control_data)
    assert check_types(policy, robot)

    simulation = Simulation(train_mazes[0], robot)

    steps = [0, 0]

    n = 20 # Changed from 150 to 20 for ease of testing
    _w = math.ceil(math.log10(n))
    _log_format = (f"\r[{{:6.2f}}%] Episode {{:{_w}d}}; train: {{:.2f}};"
                   f" eval: {{:.2f}}; optimal: {{:.2f}}")

    print()
    print("=" * 80)
    print("Training for a maximum of", n, "episodes")

    i = None
    for i in range(n):
        simulation.reset(train_mazes[i % len(train_mazes)])
        t_reward = q_train(simulation, policy)
        steps[0] += simulation.timestep

        policy.epsilon = .1 * (1 - i / n)

        e_rewards, en_rewards = [], []
        for em in eval_mazes:
            simulation.reset(em)
            e_rewards.append(q_eval(simulation, policy))
            en_rewards.append(simulation.infos()["pretty_reward"])
            steps[1] += simulation.timestep
        e_rewards = sum(e_rewards) / len(e_rewards)
        en_rewards = sum(en_rewards) / len(en_rewards)

        print(_log_format.format(100 * (i + 1) / n, i,
                                 t_reward, e_rewards, en_rewards),
              end='', flush=True)

        if math.isclose(en_rewards, 1):
            print()
            print("[!!!!!!!] Optimal policy found [!!!!!!!]")
            break
        elif i == n - 1:
            print()

    print(f"Training took {time.time() - start_time:.2g} seconds for:\n"
          f" > {i} episodes\n"
          f" > {steps[0]} training steps\n"
          f" > {steps[1]} evaluating steps")

    return policy


def q_train(simulation, policy):
    state = simulation.generate_inputs().copy()
    action = policy(state)

    while not simulation.done():
        reward = simulation.step(action)
        state_ = simulation.observations.copy()
        action_ = policy(state)
        policy.q_learning(state, action, reward, state_, action_,
                          alpha=ALPHA, gamma=GAMMA)
        state, action = state_, action_

    return simulation.robot.reward


def q_eval(simulation, policy):
    action = policy.greedy_action(simulation.observations)
    while not simulation.done():
        simulation.step(action)
        action = policy.greedy_action(simulation.observations)

    return simulation.robot.reward


def evaluate_generalization(policy):
    policy.epsilon = 0
    rng = random.Random(0)
    robot = robot_build_data()

    n = 25 # Changed from 1000 to 25
    rewards = []

    print()
    print("=" * 80)
    print("Testing for generalization")
    _log_format = f"\r[{{:6.2f}}%] normalized reward: {{:.1g}} for {{}}"

    for i in range(n):
        maze_data = Maze.BuildData(
            width=rng.randint(10, 30),
            height=rng.randint(10, 20),
            seed=rng.randint(0, 10000),
            unicursive=True,
            p_lure=0, p_trap=0
        )
        maze = Maze.generate(maze_data)
        simulation = Simulation(maze, robot)
        simulation.run(policy)
        reward = simulation.normalized_reward()
        rewards.append(reward)
        print(_log_format.format(100 * (i + 1) / n, reward,
                                 maze_data.to_string()),
              end='', flush=True)
    print()

    avg_reward = sum(rewards) / n
    optimal = " (optimal)" if math.isclose(avg_reward, 1) else ""
    print(f"Average score of {avg_reward}{optimal} on {n} random mazes")
    print("=" * 80)


def main_learning(is_test=False): # Gets used where???
    if FOLDER.exists():
        shutil.rmtree(FOLDER)
    FOLDER.mkdir(parents=True, exist_ok=False)

    policy = train_with_maze_string()

    policy_file = save(policy, FOLDER.joinpath("policy"),
                       dict(comment="Can solve unicursive mazes"))
    print("Saved optimized policy to", policy_file)

    evaluate_generalization(policy)


def main():  # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Define server address and port
    server_address = ('127.0.0.1', 12345)

    # Bind the socket
    server_socket.bind(server_address)

    # Listen for incoming connections, currently set to max 5 clients
    server_socket.listen(5)
    print("Server is listening for incoming connections...")

    try:
        while True:  # Must accept client connection and state so
            client_socket, client_address = server_socket.accept()
            print("Accepted connection from", client_address)

            # Handle the client connection in a separate thread, so cleint requests do not get mixed up
            handle_client_connection(client_socket)

    except KeyboardInterrupt:
        print("Server stopped.")

    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
