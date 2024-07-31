# master-project
This project consists of two parts: an interface and a server, which is responisble for training. It is possible to split this server and insert a slurm script for use of resource allocation on a ripper. Make use of tunnelforwarding if a ripper is used, by adding this before the socket function. 

interface.py: the entire interface which allows for the creation of 4 mazes with interactable variables (seed, size, unicursive, traps, direction). When submitting mazes, a pop up is shown. The main window is not interactible while the pop up is there, clicking it too often can potentially lead to the interface crashing and closing especially on windows. This pop up errors out if no connection to a server can be made. The pop up changes its message and closes automatically when training has succeeded. Success will lead to a screen with results being shown. Entering an ID after the first instruction screen is mandatory as of now, it takes any values.

pretrained agent image.png: Image used in the interface.

serverexample.py: Uses socket library for connection. The entire server as one file. Training and maze conversions is included, as is creating timeline imgages. The function make_string takes the trap probabilities, but does not define that sign and no clues are included. Resulting maze strings lack any signs. Agents do not encounter signs on any such intersections. Result evalution images are encoded and returned to the interface. The HOST constant can be used to define a non-public ip adress, if both interface and server are hosted on the same device/network.

socket2.py: split of serverexample, handles connections.

worker2.py: split of serverexample, handles training.

worker_job.slurm: slurm file to be used on a ripper in conjunction with socket2 and worker2. Use tunnelforwarding in socket2 in that case.
