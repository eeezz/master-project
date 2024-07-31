import json
import argparse
import time
import shutil
import pathlib
import os
import base64

from amaze.simu.types import InputType, OutputType, StartLocation
from stable_baselines3.common.callbacks import (EvalCallback, StopTrainingOnRewardThreshold)
from stable_baselines3.common.logger import configure
from amaze import Maze, Robot, Simulation, Sign, amaze_main
from amaze.extensions.sb3 import (make_vec_maze_env, env_method, load_sb3_controller, PPO, TensorboardCallback, sb3_controller, CV2QTGuard)

SEED = 0
BUDGET = 5000
VERBOSE = False

def parse_args(): # Accept command-line arguments
    parser = argparse.ArgumentParser(description="Training script")
    parser.add_argument('--data-file', type=str, required=True, help='Path to the JSON data file')
    return parser.parse_args()

def load_data(data_file): # Load the data file
    with open(data_file, 'r') as f:
        data = json.load(f)
    participant_id = data['participant_id']
    maze_strings = data['maze_data']
    return participant_id, maze_strings

def make_string(maze_strings):
    maze_list = []
    for maze in maze_strings:
        seed = maze['Seed']
        size = maze['Size']
        traps = maze['Traps']
        unicursive = maze['Without intersections']
        start = StartLocation[maze['Start']]

        train_maze_data = Maze.BuildData(
            width=size, height=size,
            unicursive=unicursive,
            start=start,
            seed=seed,
            p_lure=0.0, p_trap=traps
        )
        maze_list.append(train_maze_data.to_string())
    return maze_list

def train(simple_str, FOLDER):
    print(f"training with maze{simple_str}")
    train_mazes = Maze.BuildData.from_string(simple_str).all_rotations()
    robot = Robot.BuildData.from_string("DD")

    train_env = make_vec_maze_env(train_mazes, robot, SEED)
    eval_env = make_vec_maze_env(train_mazes, robot, SEED, log_trajectory=True)

    optimal_reward = (sum(env_method(eval_env, "optimal_reward")) / len(train_mazes))
    tb_callback = TensorboardCallback(
        log_trajectory_every=5,
        max_timestep=BUDGET
    )
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=FOLDER, log_path=FOLDER,
        eval_freq=BUDGET // (10 * len(train_mazes)), verbose=1,
        n_eval_episodes=len(train_mazes),
        callback_after_eval=tb_callback,
        callback_on_new_best=StopTrainingOnRewardThreshold(
            reward_threshold=optimal_reward, verbose=1)
    )

    model = sb3_controller(
        PPO, policy="MlpPolicy", env=train_env, seed=SEED, learning_rate=1e-3, device="cpu")

    print("== Starting", "=" * 68)
    model.set_logger(configure(FOLDER, ["csv", "tensorboard"]))
    model.learn(BUDGET, callback=eval_callback, progress_bar=False)

    tb_callback.log_step(True)
    print("=" * 80)
    time.sleep(2)

def create_round_image(participant_id, round_images):
    # Image is saved in folder of the participant
    results_folder = pathlib.Path(f"results/{participant_id}")
    round_image_path = results_folder / "round_image.png"

    # Since all images are the same size, create a new vertical image for the round
    image_width, image_height = round_images[0].size
    
    round_image = Image.new('RGB', (image_width, image_height * 4), (255, 255, 255))

    for i, img in enumerate(round_images):
        y_position = i * image_height
        round_image.paste(img, (0, y_position))

    round_image.save(round_image_path)
    print(f"Saved round image to {round_image_path}")
    return round_image_path

def append_to_timeline(participant_id, round_image_path): 
    results_folder = pathlib.Path(f"results/{participant_id}")
    timeline_image_path = results_folder / "timeline.png"

    # Load the new round image
    round_image = Image.open(round_image_path)
    round_image_width, round_image_height = round_image.size

    # If timeline image doesn't exist, create a new one
    if not timeline_image_path.exists():
        big_image = Image.new('RGB', (round_image_width, round_image_height), (255, 255, 255))
        big_image.paste(round_image, (0, 0))
        print("Created new big image with the first round.")
    else:
        big_image = Image.open(timeline_image_path)
        big_image = big_image.convert('RGB')  # So it is in the correct mode

        # Create a new big image with space for the new round
        big_image_width, big_image_height = big_image.size
        new_big_image = Image.new('RGB', (big_image_width + round_image_width, round_image_height), (255, 255, 255))
        # Add new image horizontally
        new_big_image.paste(big_image, (0, 0))
        new_big_image.paste(round_image, (big_image_width, 0))

        big_image = new_big_image
        print("Appended new round to the existing big image.")

    big_image.save(timeline_image_path)
    print(f"Saved big image to {timeline_image_path}")

def main_learning(simple_strs, participant_id, is_test=False):
    image_paths = []
    round_images = []
    for simple_str in simple_strs:
        t = time.localtime()
        current_time = time.strftime("%H;%M;%S", t)
        FOLDER = f"results/{participant_id}/{simple_str}/{current_time}"
        BEST = f"{FOLDER}/best_model.zip"
        folder = pathlib.Path(FOLDER)
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=False)
        train(simple_str, FOLDER)
        eval_image_path = folder / f"trajectories/eval_final.png"
        if os.path.exists(eval_image_path):
            with open(eval_image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                image_paths.append(encoded_string)
	    # Create timeline directly after maze result has been saved
            round_images.append(Image.open(eval_image_path))

    round_image_path = create_round_image(participant_id, round_images)
    append_to_timeline(participant_id, round_image_path)

    return image_paths

if __name__ == "__main__":
    args = parse_args()
    participant_id, maze_strings = load_data(args.data_file)
    simple_strs = make_string(maze_strings)
    image_paths = main_learning(simple_strs, participant_id, is_test=False)

    # Save images to a JSON file (specify as output file in worker_job.slurm)
    output_file = f"image_paths_{participant_id}.json"
    with open(output_file, 'w') as f:
        json.dump(image_paths, f)
