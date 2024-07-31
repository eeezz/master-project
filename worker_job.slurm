#!/bin/bash
#SBATCH --job-name=worker_job
#SBATCH --output=output_%j.txt
#SBATCH --error=error_%j.txt
#SBATCH --partition=partition_name
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --time=3:00:00
#SBATCH --mail-type=END
#SBATCH --mail-user= # mail where notifications should go

# Load the required modules or activate the environment, example for loading venv:
source /home/user/project/bin/activate

# The argument passed to the script
DATA_FILE=$1

# Run the worker.py script with the data file
python worker2.py --data-file "$1" --output-file "$2"
# Alternatively use the whole path /home/username/project/worker2.py
