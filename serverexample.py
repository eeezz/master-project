import json
import socket
import pathlib
import shutil
import time
import traceback
import base64
import os
import threading

from amaze.simu.types import InputType, OutputType, StartLocation

from stable_baselines3.common.callbacks import (EvalCallback,
                                                StopTrainingOnRewardThreshold)
from stable_baselines3.common.logger import configure

from amaze import Maze, Robot, Simulation, Sign, amaze_main
from amaze.extensions.sb3 import (make_vec_maze_env, env_method,
                                  load_sb3_controller, PPO,
                                  TensorboardCallback, sb3_controller, CV2QTGuard)

SEED = 0
BUDGET = 5000 #was 100000
VERBOSE = False

BUFFER_SIZE = 4096
HOST = '123.45'  # Replace with server's IP address
PORT = 12345  # Choose any port number that is not already in use by another service on the server

def handle_client_connection(client_socket):
    try:
        data = client_socket.recv(BUFFER_SIZE).decode()
        received_data = json.loads(data)

        participant_id = received_data.get("participant_id")
        maze_strings = received_data.get("maze_data")
        print("Received participant ID:", participant_id)
        #print("Received maze strings:", maze_strings)

        if maze_strings is not None:
            simple_strs = make_string(maze_strings)
            image_paths = main_learning(simple_strs,participant_id, is_test=False)
            response_data = json.dumps(image_paths)
            client_socket.sendall(response_data.encode())

    except Exception as e:
        traceback.print_exc()  # This will print the traceback
        print("Error:", e)

    finally:
        client_socket.close()

def make_string(maze_strings):
    # Construct data from the received maze string...
    maze_list = []
    for maze in maze_strings:
        seed = maze['Seed']
        size = maze['Size']
        traps = maze['Traps']
        unicursive = maze['Without intersections']
        start = StartLocation[maze['Start']]

        # ...Then train with the resulting parameters
        train_maze_data = Maze.BuildData(
            width=size, height=size,
            unicursive=unicursive,
            start=start,
            seed=seed,
            p_lure=0.0, p_trap=traps
        )
        maze_list.append(train_maze_data.to_string())

    return maze_list

def train(simple_str, FOLDER): # All from amaze
    print(f"training with maze{simple_str}")
    train_mazes = Maze.BuildData.from_string(simple_str).all_rotations()
    #eval_mazes = [d.where(seed=TEST_SEED) for d in train_mazes]
    '''would just have mazes instead of above 2. train mazes and eval_env s would be same.. eval_mazes would not exist anymore.
    for n in user_mazes:
    train(m)
    train(m):
    mazes = m.all_rotations()
    train_env - make_vec(mazes,..)
    train_env - make_vec(mazes,.., log_trajecotry = True)
    so commented eval_mazes out and also changed some instance uses to train_mazes below'''
    robot = Robot.BuildData.from_string("DD")

    train_env = make_vec_maze_env(train_mazes, robot, SEED)
    eval_env = make_vec_maze_env(train_mazes, robot, SEED, log_trajectory=True)

    optimal_reward = (sum(env_method(eval_env, "optimal_reward"))
                      / len(train_mazes))
    tb_callback = TensorboardCallback(
        log_trajectory_every=5,  # Eval callback (below) # was 1, has only few images when budget is low
        max_timestep=BUDGET
    )
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=FOLDER, log_path=FOLDER,
        eval_freq=BUDGET//(10*len(train_mazes)), verbose=1,
        n_eval_episodes=len(train_mazes),
        callback_after_eval=tb_callback,
        callback_on_new_best=StopTrainingOnRewardThreshold(
            reward_threshold=optimal_reward, verbose=1)
    )

    model = sb3_controller(
        PPO, policy="MlpPolicy", env=train_env, seed=SEED, learning_rate=1e-3, device="cpu")

    print("== Starting", "="*68)
    model.set_logger(configure(FOLDER, ["csv", "tensorboard"]))
    model.learn(BUDGET, callback=eval_callback, progress_bar=True)

    tb_callback.log_step(True)
    print("="*80)
    time.sleep(2)

def main_learning(simple_strs, participant_id, is_test=False):
    image_paths = []
    for simple_str in simple_strs:
        t = time.localtime()
        current_time = time.strftime("%H;%M;%S", t)
        FOLDER = f"tmp/demos/sb3/{participant_id}/{simple_str}/{current_time}"
        BEST = f"{FOLDER}/best_model.zip"
        folder = pathlib.Path(FOLDER)
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=False)
        train(simple_str, FOLDER) #not lowercase
        #print("finished a maze")
        eval_image_path = folder / f"trajectories/eval_final.png"
        if os.path.exists(eval_image_path):
            with open(eval_image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                image_paths.append(encoded_string)

    #evaluate() # Is off

    with CV2QTGuard(platform=False):
        amaze_main(f"--controller {BEST} --extension sb3 --maze {simple_str}"
                   f" --auto-quit --robot-inputs DISCRETE"
                   f" --robot-outputs DISCRETE --no-restore-config")
    # Add a delay before the next round
    time.sleep(2)
    return image_paths

def main():  # Create socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Server address and port
    server_address = (HOST, PORT)
    server_socket.bind(server_address)


    # Listen for incoming connections, currently set to max 5 clients
    server_socket.listen(5)
    print("Server is listening for incoming connections...")

    try:
        while True:  # Must accept client connection and state so
            client_socket, client_address = server_socket.accept()
            print("Accepted connection from", client_address)

            # Handle the client connection in a separate thread, so client requests do not get mixed up
            #handle_client_connection(client_socket)

            # Make a new thread to handle the client connection
            client_thread = threading.Thread(target=handle_client_connection, args=(client_socket,))
            client_thread.start()

    except KeyboardInterrupt:
        print("Server stopped.")

    finally:
        server_socket.close()

if __name__ == "__main__":
    main()